"""Report what a .NET codebase targets, so generated code only uses what is available.

Usage: python3 detect_target.py [PATH] [--json] [--no-sdk-probe] [--evaluate]

PATH is a folder, a .csproj, a .slnx/.sln or a .cs file (default: current folder).
For every C# project found, prints the target frameworks, the effective C# language
version, preview opt-ins, nullable and AOT settings, the ASP.NET Core / EF Core /
test stack and its versions. Properties come from the project file, the nearest
Directory.Build.props/.targets and Directory.Packages.props. MSBuild conditions are
not evaluated: a value set under a condition is reported with a "conditional" flag.
--evaluate asks MSBuild for the real values (`dotnet msbuild -getProperty`, one call
per project and target framework): slower, but authoritative.

Python 3.11 standard library only. Never modifies anything.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

SKIP_DIRS = {"bin", "obj", "node_modules", ".git", ".vs", ".idea", "artifacts", "packages"}
MAX_PROJECTS = 200

# Default C# version per target framework (docs: "C# language versioning").
TFM_DEFAULT_LANG = {
    "net11.0": "15",
    "net10.0": "14",
    "net9.0": "13",
    "net8.0": "12",
    "net7.0": "11",
    "net6.0": "10",
    "net5.0": "9.0",
    "netcoreapp3.1": "8.0",
    "netcoreapp3.0": "8.0",
    "netstandard2.1": "8.0",
}
# Newest C# version each SDK band's compiler supports.
SDK_MAX_LANG = {11: "15", 10: "14", 9: "13", 8: "12", 7: "11", 6: "10"}
LATEST_KNOWN_LANG = "15"

TRACKED_PROPERTIES = (
    "TargetFramework",
    "TargetFrameworks",
    "LangVersion",
    "EnablePreviewFeatures",
    "Nullable",
    "ImplicitUsings",
    "AllowUnsafeBlocks",
    "PublishAot",
    "IsAotCompatible",
    "IsTrimmable",
    "InvariantGlobalization",
    "TreatWarningsAsErrors",
    "AnalysisLevel",
    "AnalysisMode",
    "ManagePackageVersionsCentrally",
    "OutputType",
    "IsTestProject",
    "UseMicrosoftTestingPlatformRunner",
    "TestingPlatformDotnetTestSupport",
    "NuGetAudit",
    "NuGetAuditMode",
    "Features",
    "InterceptorsNamespaces",
)

STACKS = {
    "aspnetcore": re.compile(r"^Microsoft\.AspNetCore\.", re.IGNORECASE),
    "efcore": re.compile(r"^Microsoft\.EntityFrameworkCore(\.|$)", re.IGNORECASE),
    "aspire": re.compile(r"^Aspire\.", re.IGNORECASE),
}
TEST_PACKAGES = {
    "xunit.v3": "xUnit v3",
    "xunit": "xUnit v2",
    "mstest": "MSTest",
    "mstest.testframework": "MSTest",
    "nunit": "NUnit",
    "tunit": "TUnit",
    "microsoft.testing.platform": "Microsoft.Testing.Platform",
}


@dataclass
class Prop:
    value: str
    source: str
    conditional: bool = False


@dataclass
class Package:
    name: str
    version: str | None
    source: str


@dataclass
class ProjectReport:
    path: str
    sdk: str | None
    target_frameworks: list[str]
    lang_version: dict[str, str]
    lang_version_source: str
    preview: bool
    properties: dict[str, dict[str, object]]
    stacks: dict[str, str | None]
    test_frameworks: list[str]
    packages: list[dict[str, str | None]]
    notes: list[str] = field(default_factory=list)


# -- XML helpers --------------------------------------------------------------


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_xml(path: Path) -> ET.Element | None:
    try:
        return ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None


def has_condition(element: ET.Element, parents: dict[ET.Element, ET.Element]) -> bool:
    node: ET.Element | None = element
    while node is not None:
        if node.get("Condition"):
            return True
        node = parents.get(node)
    return False


def read_properties(path: Path, into: dict[str, Prop]) -> None:
    root = parse_xml(path)
    if root is None:
        return
    parents = {child: parent for parent in root.iter() for child in parent}
    for group in root.iter():
        if local(group.tag) != "PropertyGroup":
            continue
        for prop in group:
            name = local(prop.tag)
            if prop.text is not None:  # all properties, so $(Name) references expand
                into[name] = Prop(prop.text.strip(), path.name, has_condition(prop, parents))


def read_items(path: Path, item: str) -> list[ET.Element]:
    root = parse_xml(path)
    if root is None:
        return []
    return [e for e in root.iter() if local(e.tag) == item]


def expand(value: str, props: dict[str, Prop]) -> str:
    def sub(match: re.Match[str]) -> str:
        found = props.get(match.group(1))
        return found.value if found else match.group(0)

    for _ in range(5):
        new = re.sub(r"\$\(([A-Za-z_][\w.]*)\)", sub, value)
        if new == value:
            break
        value = new
    return value


# -- File discovery -----------------------------------------------------------


def find_upward(start: Path, name: str, stop: Path | None = None) -> Path | None:
    for folder in [start, *start.parents]:
        candidate = folder / name
        if candidate.is_file():
            return candidate
        if stop is not None and folder == stop:
            break
    return None


def build_files(project_dir: Path, name: str) -> list[Path]:
    """Directory.Build.props/.targets chain, outermost first (follows explicit parent imports)."""
    chain: list[Path] = []
    current = find_upward(project_dir, name)
    while current is not None:
        chain.append(current)
        imports = " ".join(e.get("Project", "") for e in read_items(current, "Import"))
        if name not in imports and "GetPathOfFileAbove" not in imports:
            break
        current = find_upward(current.parent.parent, name)
    return list(reversed(chain))


def iter_projects(root: Path) -> list[Path]:
    found: list[Path] = []
    stack = [root]
    while stack and len(found) < MAX_PROJECTS:
        folder = stack.pop()
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.name.startswith("."):
                    stack.append(entry)
            elif entry.suffix.lower() == ".csproj":
                found.append(entry)
    return sorted(found)


def projects_from_solution(solution: Path) -> list[Path]:
    text = solution.read_text(encoding="utf-8", errors="replace")
    if solution.suffix.lower() == ".slnx":
        rels = re.findall(r'Path="([^"]+\.csproj)"', text)
    else:
        rels = re.findall(r'"([^"]+\.csproj)"', text)
    paths = [(solution.parent / rel.replace("\\", "/")).resolve() for rel in rels]
    return sorted(p for p in paths if p.is_file())


def file_based_directives(cs_file: Path) -> dict[str, list[str]]:
    directives: dict[str, list[str]] = {}
    try:
        lines = cs_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return directives
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#!") or not stripped:
            continue
        match = re.match(r"#:(\w+)\s+(.*)", stripped)
        if not match:
            break
        directives.setdefault(match.group(1), []).append(match.group(2).strip())
    return directives


# -- SDK ----------------------------------------------------------------------


def strip_json_comments(text: str) -> str:
    """Remove // and /* */ comments (allowed in global.json) outside of strings."""
    out: list[str] = []
    i, in_string = 0, False
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 1
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
            out.append(char)
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
            continue
        else:
            out.append(char)
        i += 1
    return "".join(out)


def read_global_json(start: Path) -> tuple[Path | None, dict[str, object]]:
    path = find_upward(start, "global.json")
    if path is None:
        return None, {}
    try:
        data = json.loads(strip_json_comments(path.read_text(encoding="utf-8-sig")))
    except (OSError, json.JSONDecodeError):
        return path, {"error": "unreadable global.json"}
    return path, data if isinstance(data, dict) else {}


def probe_sdk(cwd: Path) -> str | None:
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        return None
    try:
        result = subprocess.run(
            [dotnet, "--version"], cwd=cwd, capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        return None
    version = result.stdout.strip()
    return version if result.returncode == 0 and re.match(r"^\d+\.", version) else None


def sdk_major(version: str | None) -> int | None:
    match = re.match(r"^(\d+)\.", version or "")
    return int(match.group(1)) if match else None


# -- Language version ---------------------------------------------------------


def tfm_major(tfm: str) -> int | None:
    match = re.match(r"^net(\d+)\.\d+$", tfm.split("-", 1)[0].lower())
    return int(match.group(1)) if match and int(match.group(1)) >= 5 else None


def is_known_tfm(tfm: str) -> bool:
    base = tfm.split("-", 1)[0].lower()
    pattern = r"^(net\d+\.\d+|netcoreapp\d\.\d|netstandard\d\.\d|net\d{2,3})$"
    return bool(re.match(pattern, base))


def default_lang(tfm: str) -> str:
    """C# version used when LangVersion is not set: TFM major + 4 from net5.0 on."""
    base = tfm.split("-", 1)[0].lower()  # net10.0-windows -> net10.0
    if base in TFM_DEFAULT_LANG:
        return TFM_DEFAULT_LANG[base]
    major = tfm_major(base)
    if major is not None:
        return str(major + 4)
    return "7.3"  # .NET Framework, .NET Standard 2.0, older .NET Core


def version_key(value: str) -> float | None:
    try:
        return float(value.split(" ", 1)[0])
    except ValueError:
        return None


def effective_lang(tfm: str, lang: Prop | None, sdk: int | None) -> str:
    sdk_max = SDK_MAX_LANG.get(sdk) if sdk else None
    if lang is None:
        default = default_lang(tfm)
        default_key, max_key = version_key(default), version_key(sdk_max or "")
        if default_key and max_key and default_key > max_key:
            return f"{sdk_max} (capped by the SDK; the TFM default is {default})"
        return default
    value = lang.value.lower()
    if value in {"latest", "latestmajor", "default"}:
        # These follow the compiler, not the target framework.
        return f"{sdk_max or LATEST_KNOWN_LANG}{'' if sdk_max else ' (assumed: SDK unknown)'}"
    if value == "preview":
        return f"preview (beyond {sdk_max or LATEST_KNOWN_LANG})"
    return lang.value


def lang_notes(tfms: list[str], lang: Prop | None, pinned: int | None) -> list[str]:
    notes: list[str] = []
    if lang is not None:
        if lang.value.lower() in {"latest", "latestmajor", "default"}:
            notes.append(
                f"LangVersion={lang.value} follows the installed SDK, not the target framework: "
                "builds can differ between machines"
            )
        explicit = version_key(lang.value)
        for tfm in tfms:
            default = version_key(default_lang(tfm))
            if explicit and default and explicit > default:
                notes.append(
                    f"C# {lang.value} is newer than the {tfm} default ({default_lang(tfm)}): "
                    "unsupported by Microsoft; features that need runtime types fail"
                )
    for tfm in tfms:
        major = tfm_major(tfm)
        if major and pinned and pinned < major:
            notes.append(f"global.json pins SDK {pinned}.x, which cannot build {tfm}")
        if not is_known_tfm(tfm):
            notes.append(f"'{tfm}' looks like a custom TFM alias: run with --evaluate")
    return notes


def evaluate_project(project: Path, tfms: list[str]) -> dict[str, dict[str, str]]:
    """Ask MSBuild for the evaluated values, per target framework."""
    dotnet = shutil.which("dotnet")
    if dotnet is None:
        return {}
    names = ["LangVersion", "TargetFrameworkIdentifier", "TargetFrameworkVersion", "Nullable"]
    results: dict[str, dict[str, str]] = {}
    for tfm in tfms or [""]:
        command = [dotnet, "msbuild", str(project), *(f"-getProperty:{n}" for n in names)]
        if tfm and len(tfms) > 1:
            command.append(f"-p:TargetFramework={tfm}")
        try:
            run = subprocess.run(
                command, cwd=project.parent, capture_output=True, text=True, timeout=120
            )
            values = json.loads(run.stdout).get("Properties", {})
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, AttributeError):
            continue
        if isinstance(values, dict):
            results[tfm] = {k: str(v) for k, v in values.items()}
    return results


# -- Project analysis ---------------------------------------------------------


def package_versions(central: Path | None, props: dict[str, Prop]) -> dict[str, str]:
    versions: dict[str, str] = {}
    if central is None:
        return versions
    central_props: dict[str, Prop] = dict(props)
    read_properties(central, central_props)
    for item in read_items(central, "PackageVersion"):
        name = item.get("Include") or item.get("Update")
        if name and item.get("Version"):
            versions[name.lower()] = expand(item.get("Version", ""), central_props)
    return versions


def analyze_project(
    project: Path, sdk: int | None, pinned: int | None = None, evaluate: bool = False
) -> ProjectReport:
    props: dict[str, Prop] = {}
    notes: list[str] = []
    for file in build_files(project.parent, "Directory.Build.props"):
        read_properties(file, props)
    read_properties(project, props)
    for file in build_files(project.parent, "Directory.Build.targets"):
        read_properties(file, props)

    root = parse_xml(project)
    sdk_attr = root.get("Sdk") if root is not None else None
    if root is not None and not sdk_attr:
        sdk_names = [e.get("Name") for e in root.iter() if local(e.tag) == "Sdk" and e.get("Name")]
        sdk_attr = ";".join(n for n in sdk_names if n) or None
    if root is None:
        notes.append("project file could not be parsed")

    tfm_prop = props.get("TargetFrameworks") or props.get("TargetFramework")
    tfms = [t.strip() for t in expand(tfm_prop.value, props).split(";")] if tfm_prop else []
    tfms = [t for t in tfms if t]
    if tfm_prop and tfm_prop.conditional:
        notes.append(f"target framework set under a condition in {tfm_prop.source}")
    if not tfms:
        notes.append("no TargetFramework found (set elsewhere or legacy project format)")

    lang = props.get("LangVersion")
    preview_prop = props.get("EnablePreviewFeatures")
    if lang is not None:
        lang = Prop(expand(lang.value, props), lang.source, lang.conditional)
        if lang.conditional:
            notes.append(f"LangVersion set under a condition in {lang.source}")
    elif preview_prop and preview_prop.value.lower() == "true":
        lang = Prop("preview", f"{preview_prop.source} (EnablePreviewFeatures)")
    lang_by_tfm = {tfm: effective_lang(tfm, lang, sdk) for tfm in tfms}
    lang_source = f"LangVersion in {lang.source}" if lang else "default for the TFM"
    notes.extend(lang_notes(tfms, lang, pinned))
    preview = bool(lang and lang.value.lower() == "preview")

    if evaluate:
        evaluated = evaluate_project(project, tfms)
        for tfm, values in evaluated.items():
            if values.get("LangVersion"):
                lang_by_tfm[tfm or (tfms[0] if tfms else "?")] = values["LangVersion"]
                lang_source = "dotnet msbuild evaluation"
            preview = preview or values.get("LangVersion", "").lower() == "preview"
        if not evaluated:
            notes.append("MSBuild evaluation failed or dotnet is not installed")

    # Central Package Management may be enabled in Directory.Packages.props itself.
    central = find_upward(project.parent, "Directory.Packages.props")
    central_versions = package_versions(central, props)

    packages: list[Package] = []
    for item in read_items(project, "PackageReference"):
        name = item.get("Include") or item.get("Update")
        if not name:
            continue
        version = item.get("Version") or item.get("VersionOverride")
        source = project.name
        if not version:
            version = central_versions.get(name.lower())
            source = "Directory.Packages.props" if version else source
        packages.append(Package(name, expand(version, props) if version else None, source))
    for file in build_files(project.parent, "Directory.Build.props"):
        for item in read_items(file, "PackageReference"):
            name = item.get("Include")
            if name and all(p.name.lower() != name.lower() for p in packages):
                version = item.get("Version") or central_versions.get(name.lower())
                packages.append(Package(name, version, file.name))

    stacks: dict[str, str | None] = {}
    for stack, pattern in STACKS.items():
        hits = [p for p in packages if pattern.match(p.name)]
        if hits:
            stacks[stack] = next((p.version for p in hits if p.version), None)
    frameworks = [e.get("Include", "") for e in read_items(project, "FrameworkReference")]
    if (
        sdk_attr and "Microsoft.NET.Sdk.Web" in sdk_attr
    ) or "Microsoft.AspNetCore.App" in frameworks:
        stacks["aspnetcore"] = stacks.get("aspnetcore") or "shared framework (matches TFM)"
    if sdk_attr and "Aspire" in sdk_attr:
        stacks["aspire"] = stacks.get("aspire") or sdk_attr

    tests = sorted(
        {TEST_PACKAGES[p.name.lower()] for p in packages if p.name.lower() in TEST_PACKAGES}
    )
    if sdk_attr and "MSTest.Sdk" in sdk_attr:
        tests = sorted({*tests, "MSTest"})

    return ProjectReport(
        path=project.as_posix(),
        sdk=sdk_attr,
        target_frameworks=tfms,
        lang_version=lang_by_tfm,
        lang_version_source=lang_source,
        preview=preview,
        properties={
            k: {"value": expand(v.value, props), "source": v.source, "conditional": v.conditional}
            for k, v in sorted(props.items())
            if k in TRACKED_PROPERTIES
            and k not in {"TargetFramework", "TargetFrameworks", "LangVersion"}
        },
        stacks=stacks,
        test_frameworks=tests,
        packages=[asdict(p) for p in packages],
        notes=notes,
    )


def analyze_file_based_app(cs_file: Path, sdk: int | None) -> dict[str, object]:
    directives = file_based_directives(cs_file)
    props = dict(p.split("=", 1) if "=" in p else (p, "") for p in directives.get("property", []))
    tfm = props.get("TargetFramework") or (f"net{sdk}.0 (SDK default)" if sdk else "SDK default")
    lang = props.get("LangVersion")
    return {
        "path": cs_file.as_posix(),
        "kind": "file-based app",
        "directives": directives,
        "target_framework": tfm,
        "lang_version": lang or (SDK_MAX_LANG.get(sdk, "unknown") if sdk else "SDK default"),
    }


# -- Entry point --------------------------------------------------------------


def collect(target: Path, probe: bool, evaluate: bool = False) -> dict[str, object]:
    target = target.resolve()
    base = target if target.is_dir() else target.parent
    global_path, global_json = read_global_json(base)
    sdk_block = global_json.get("sdk") if isinstance(global_json.get("sdk"), dict) else {}
    pinned = sdk_block.get("version") if isinstance(sdk_block, dict) else None
    resolved = probe_sdk(base) if probe else None
    sdk = sdk_major(resolved) or sdk_major(str(pinned) if pinned else None)

    file_apps: list[dict[str, object]] = []
    if target.is_file() and target.suffix.lower() == ".csproj":
        projects = [target]
    elif target.is_file() and target.suffix.lower() in {".sln", ".slnx"}:
        projects = projects_from_solution(target)
    elif target.is_file() and target.suffix.lower() == ".cs":
        owner = next(
            (p for p in [target.parent, *target.parent.parents] if any(p.glob("*.csproj"))), None
        )
        if owner is None or file_based_directives(target):
            projects = []
            file_apps.append(analyze_file_based_app(target, sdk))
        else:
            projects = sorted(owner.glob("*.csproj"))
    else:
        projects = iter_projects(base)

    pinned_major = sdk_major(str(pinned) if pinned else None)
    reports = [analyze_project(p, sdk, pinned_major, evaluate) for p in projects]
    all_tfms = sorted({t for r in reports for t in r.target_frameworks})
    return {
        "root": base.as_posix(),
        "sdk": {
            "global_json": global_path.as_posix() if global_path else None,
            "pinned": pinned,
            "roll_forward": sdk_block.get("rollForward") if isinstance(sdk_block, dict) else None,
            "allow_prerelease": sdk_block.get("allowPrerelease")
            if isinstance(sdk_block, dict)
            else None,
            "test_runner": (global_json.get("test") or {}).get("runner")
            if isinstance(global_json.get("test"), dict)
            else None,
            "resolved": resolved,
            "max_lang_version": SDK_MAX_LANG.get(sdk) if sdk else None,
        },
        "target_frameworks": all_tfms,
        "projects": [asdict(r) for r in reports],
        "file_based_apps": file_apps,
        "truncated": len(projects) >= MAX_PROJECTS,
    }


def render(data: dict[str, object]) -> str:
    out: list[str] = []
    sdk = data["sdk"]
    assert isinstance(sdk, dict)
    pin = sdk.get("pinned") or "not pinned"
    out.append(
        f"SDK: resolved {sdk.get('resolved') or 'unknown'}, global.json {pin}"
        + (f", rollForward {sdk['roll_forward']}" if sdk.get("roll_forward") else "")
        + (f", test runner {sdk['test_runner']}" if sdk.get("test_runner") else "")
    )
    if sdk.get("max_lang_version"):
        out.append(f"Newest C# version this SDK compiles: {sdk['max_lang_version']}")
    tfms = data["target_frameworks"]
    if tfms:
        out.append(f"Target frameworks in use: {', '.join(tfms)}")
    for project in data["projects"]:  # type: ignore[union-attr]
        out.append("")
        out.append(f"{project['path']}  [{project['sdk'] or 'no Sdk attribute'}]")
        for tfm, lang in project["lang_version"].items():
            out.append(f"  {tfm}: C# {lang}")
        out.append(f"  C# version from: {project['lang_version_source']}")
        if project["preview"]:
            out.append("  PREVIEW features enabled (LangVersion preview or EnablePreviewFeatures)")
        props = project["properties"]
        shown = ", ".join(
            f"{k}={v['value']}{' (conditional)' if v['conditional'] else ''}"
            for k, v in props.items()
        )
        if shown:
            out.append(f"  Properties: {shown}")
        if project["stacks"]:
            out.append(
                "  Stacks: "
                + ", ".join(f"{k} {v or '(version unknown)'}" for k, v in project["stacks"].items())
            )
        if project["test_frameworks"]:
            out.append(f"  Tests: {', '.join(project['test_frameworks'])}")
        for note in project["notes"]:
            out.append(f"  Note: {note}")
    for app in data["file_based_apps"]:  # type: ignore[union-attr]
        out.append("")
        out.append(f"{app['path']}  [file-based app]")
        out.append(f"  Target: {app['target_framework']}, C# {app['lang_version']}")
        for kind, values in app["directives"].items():
            out.append(f"  #:{kind} {', '.join(values)}")
    if not data["projects"] and not data["file_based_apps"]:
        out.append("No C# project found.")
    if data.get("truncated"):
        out.append(f"Stopped after {MAX_PROJECTS} projects.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", nargs="?", default=".", type=Path)
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--no-sdk-probe", action="store_true", help="do not run 'dotnet --version'")
    parser.add_argument(
        "--evaluate", action="store_true", help="confirm values with 'dotnet msbuild -getProperty'"
    )
    args = parser.parse_args(argv)
    if not args.path.exists():
        print(f"Path not found: {args.path}", file=sys.stderr)
        return 1
    data = collect(args.path, probe=not args.no_sdk_probe, evaluate=args.evaluate)
    print(json.dumps(data, indent=2) if args.json else render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
