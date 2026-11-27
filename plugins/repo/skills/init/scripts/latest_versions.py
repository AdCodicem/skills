"""Check, and optionally update, every version a repository pins.

Reports the current releases of .NET, Node.js and Python, then checks:

- every `uses: owner/repo@ref` in YAML files (workflows, composite actions and
  workflow fragments) against the action's latest release;
- the SDK in `global.json`, and the `netX.Y` target frameworks against the
  supported .NET channels;
- `.nvmrc`, `.node-version` and `node-version:` against the Node.js LTS;
- `.python-version` and `python-version:` against the latest CPython;
- npm packages and the `packageManager` field in `package.json`, NuGet
  packages in `Directory.Packages.props`, project files and `dotnet-tools.json`,
  PyPI packages pinned with `==` or `>=` in `pyproject.toml`;
- Azure Verified Modules (`br/public:avm/...:version`) in Bicep files;
- `rev:` of pre-commit hooks hosted on GitHub.

With --write, rewrites the pins in place: actions become `@<full SHA> # vX.Y.Z`,
runtimes, modules and hooks move to their latest version, and packages move to
their latest version within the same major (all majors with --allow-major, for
files the skill has just generated).

Standard library only. Needs network access to github.com, builds.dotnet.microsoft.com,
nodejs.org, raw.githubusercontent.com, peps.python.org, registry.npmjs.org, api.nuget.org,
pypi.org and mcr.microsoft.com. Action tags come from `git ls-remote` when git
is installed, otherwise from the GitHub REST API (set GITHUB_TOKEN to raise its
rate limit).

Usage:
    python3 scripts/latest_versions.py [--root DIR] [--write] [--allow-major] [--json]

--root is the repository to check (default: this skill's templates).

Exit codes: 0 everything is current, 1 something is outdated (before --write),
2 a lookup failed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

DOTNET_INDEX_URL = "https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json"
NODE_INDEX_URL = "https://nodejs.org/dist/index.json"
NODE_SCHEDULE_URL = "https://raw.githubusercontent.com/nodejs/Release/main/schedule.json"
PYTHON_CYCLE_URL = "https://peps.python.org/api/release-cycle.json"
NPM_URL = "https://registry.npmjs.org/{name}/latest"
NUGET_URL = "https://api.nuget.org/v3-flatcontainer/{name}/index.json"
PYPI_URL = "https://pypi.org/pypi/{name}/json"
MCR_URL = "https://mcr.microsoft.com/v2/bicep/{path}/tags/list"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "templates"
SKIPPED_DIRS = {"bin", "obj", "node_modules", ".git", ".venv", "venv", "dist", "build"}
TIMEOUT = 20

USES = re.compile(
    r"^(?P<prefix>\s*(?:-\s*)?uses:\s*)(?P<quote>['\"]?)"
    r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?P<path>/[^@\s'\"]*)?@(?P<ref>[^\s'\"#]+)"
    r"(?P=quote)(?P<comment>[ \t]*#.*)?$",
    re.MULTILINE,
)
VERSION_COMMENT = re.compile(r"#\s*(v?\d+(?:\.\d+){0,2})\b")
YAML_VERSION = re.compile(
    r"^(?P<prefix>\s*(?:-\s*)?(?P<key>node-version|python-version):\s*)(?P<quote>['\"]?)"
    r"(?P<value>[^\s'\"#]+)(?P=quote)",
    re.MULTILINE,
)
TARGET_FRAMEWORKS = re.compile(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>")
NET_TFM = re.compile(r"^net(\d+)\.(\d+)")
PACKAGE_VERSION = re.compile(
    r"<(?P<tag>PackageVersion|PackageReference)\s+(?:Include|Update)=\"(?P<name>[^\"]+)\"\s+"
    r"Version=\"(?P<version>[^\"$]+)\""
)
AVM = re.compile(r"br/public:(?P<path>avm/[a-z0-9/-]+):(?P<version>\d+\.\d+\.\d+)")
PRE_COMMIT_REPO = re.compile(
    r"^(?P<indent>\s*)-\s*repo:\s*https://github\.com/(?P<repo>[\w.-]+/[\w.-]+?)(?:\.git)?\s*\n"
    r"(?P<between>(?:(?P=indent)\s+.*\n)*?)(?P<revline>(?P=indent)\s+rev:\s*['\"]?(?P<rev>[^\s'\"#]+)['\"]?)",
    re.MULTILINE,
)
PYPI_PIN = re.compile(r"\"(?P<name>[A-Za-z0-9_.\-\[\]]+)(?P<op>==|>=)(?P<version>\d+(?:\.\d+)*)\"")
VERSION_TAG = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
SHA = re.compile(r"^[0-9a-f]{40}$")

JsonFetcher = Callable[[str], object]
TagLister = Callable[[str], dict[str, str]]


@dataclass
class Item:
    """One pinned version: where it is, what it is pinned to, what is latest."""

    kind: str
    file: str
    name: str
    pinned: str
    latest: str = ""
    status: str = "unknown"
    write: str | None = None  # replacement text for --write, when one applies


@dataclass
class Report:
    runtimes: dict = field(default_factory=dict)
    items: list[Item] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_version(text: str) -> tuple[int, int, int] | None:
    """`v6.1.0` -> (6, 1, 0); `6` -> (6, 0, 0); anything else -> None."""
    match = VERSION_TAG.match(text.strip())
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def stable_versions(versions: list[str]) -> list[str]:
    """Versions without a prerelease or build suffix, oldest first."""
    pattern = re.compile(r"^\d+(?:\.\d+)*$")
    return sorted(
        (v for v in versions if pattern.match(v)),
        key=lambda v: tuple(int(p) for p in v.split(".")),
    )


def _files(root: Path, *patterns: str) -> list[Path]:
    found: set[Path] = set()
    for pattern in patterns:
        found.update(
            p
            for p in root.rglob(pattern)
            if p.is_file() and not SKIPPED_DIRS.intersection(p.relative_to(root).parts)
        )
    return sorted(found)


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


# --- Lookups -------------------------------------------------------------------


def fetch_json(url: str) -> object:
    headers = {"Accept": "application/json", "User-Agent": "repo-init-skill"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


def git_tags(repo: str) -> dict[str, str]:
    """Tag -> commit SHA, peeled for annotated tags, from `git ls-remote`."""
    git = shutil.which("git")
    if not git:
        raise OSError("git is not installed")
    result = subprocess.run(
        [git, "ls-remote", "--tags", f"https://github.com/{repo}"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=True,
    )
    tags: dict[str, str] = {}
    for line in result.stdout.splitlines():
        sha, _, ref = line.partition("\trefs/tags/")
        if not ref:
            continue
        if ref.endswith("^{}"):
            tags[ref[:-3]] = sha  # the peeled commit wins over the tag object
        else:
            tags.setdefault(ref, sha)
    return tags


def api_tags(repo: str) -> dict[str, str]:
    data = fetch_json(f"https://api.github.com/repos/{repo}/tags?per_page=100")
    return {item["name"]: item["commit"]["sha"] for item in data}  # type: ignore[index]


def list_tags(repo: str) -> dict[str, str]:
    try:
        return git_tags(repo)
    except (OSError, subprocess.SubprocessError):
        return api_tags(repo)


def latest_tag(tags: dict[str, str]) -> tuple[str, str]:
    """(latest full version tag, its commit SHA)."""
    candidates = [(parse_version(t), t) for t in tags if t.count(".") == 2 and parse_version(t)]
    if not candidates:
        candidates = [(parse_version(t), t) for t in tags if parse_version(t)]
    if not candidates:
        raise ValueError("no version tags found")
    _, tag = max(candidates)
    return tag, tags[tag]


def dotnet_channels(index: dict) -> list[dict]:
    """Supported stable .NET channels, newest first."""
    channels = [
        {
            "channel": r["channel-version"],
            "type": r.get("release-type"),
            "sdk": r.get("latest-sdk"),
            "runtime": r.get("latest-runtime"),
            "eol": r.get("eol-date"),
        }
        for r in index.get("releases-index", [])
        if r.get("support-phase") in {"active", "maintenance"}
        and r.get("release-type") in {"lts", "sts"}
    ]
    if not channels:
        raise ValueError("no supported channel in the .NET releases index")
    return sorted(
        channels, key=lambda c: tuple(int(p) for p in c["channel"].split(".")), reverse=True
    )


def node_lines(index: list[dict], schedule: dict, today: dt.date) -> dict:
    """The active LTS line and every maintained LTS line, from the index and schedule."""
    lts = [r for r in index if r.get("lts")]
    if not lts:
        raise ValueError("no LTS release in the Node.js index")
    latest = max(lts, key=lambda r: parse_version(r["version"]) or (0, 0, 0))
    maintained = []
    for name, info in schedule.items():
        major = name.lstrip("v")
        if not major.isdigit() or "lts" not in info:
            continue
        lts_start = dt.date.fromisoformat(info["lts"])
        end = dt.date.fromisoformat(info["end"])
        if lts_start <= today <= end:
            maintained.append(int(major))
    return {
        "lts": parse_version(latest["version"])[0],  # type: ignore[index]
        "version": latest["version"].lstrip("v"),
        "maintained": sorted(maintained),
    }


def python_lines(cycle: dict) -> dict:
    """The newest bugfix branch and every supported branch of CPython."""
    supported = [b for b, info in cycle.items() if info.get("status") in {"bugfix", "security"}]
    bugfix = [b for b, info in cycle.items() if info.get("status") == "bugfix"]
    if not bugfix:
        raise ValueError("no bugfix branch in the CPython release cycle")

    def key(branch: str) -> tuple[int, ...]:
        return tuple(int(p) for p in branch.split("."))

    return {"latest": max(bugfix, key=key), "supported": sorted(supported, key=key)}


# --- Scanning ------------------------------------------------------------------


def scan_actions(root: Path, report: Report, tags_for: TagLister) -> None:
    cache: dict[str, tuple[str, str] | Exception] = {}
    for file in _files(root, "*.yml", "*.yaml"):
        text = file.read_text(encoding="utf-8")
        for match in USES.finditer(text):
            repo = match["repo"]
            if repo not in cache:
                try:
                    cache[repo] = latest_tag(tags_for(repo))
                except Exception as exc:  # noqa: BLE001 - report every lookup failure
                    cache[repo] = exc
                    report.errors.append(f"{repo}: {exc}")
            found = cache[repo]
            ref = match["ref"]
            item = Item("action", _rel(root, file), repo + (match["path"] or ""), ref)
            if isinstance(found, Exception):
                report.items.append(item)
                continue
            tag, sha = found
            item.latest = tag
            if SHA.match(ref):
                comment = VERSION_COMMENT.search(match["comment"] or "")
                item.pinned = f"{ref[:12]} ({comment[1] if comment else 'no version comment'})"
                current = ref == sha or (
                    comment and parse_version(comment[1]) == parse_version(tag)
                )
                item.status = "current" if current else "outdated"
            else:
                pinned_major = (parse_version(ref) or (None,))[0]
                latest_major = (parse_version(tag) or (None,))[0]
                behind = pinned_major is not None and pinned_major != latest_major
                item.status = "outdated" if behind else "unpinned"
            item.write = f"{sha} # {tag}"
            report.items.append(item)


def scan_dotnet(root: Path, report: Report, channels: list[dict] | None) -> None:
    if channels is None:
        return
    latest = channels[0]
    supported = {c["channel"] for c in channels}
    global_json = root / "global.json"
    for file in _files(root, "global.json"):
        try:
            sdk = json.loads(file.read_text(encoding="utf-8")).get("sdk", {}).get("version")
        except json.JSONDecodeError:
            continue
        if sdk:
            pinned, newest = parse_version(sdk), parse_version(latest["sdk"])
            status = "current" if pinned and newest and pinned >= newest else "outdated"
            report.items.append(
                Item(
                    ".NET SDK",
                    _rel(root, file),
                    "global.json",
                    sdk,
                    latest["sdk"],
                    status,
                    latest["sdk"] if status == "outdated" else None,
                )
            )
    del global_json
    for file in _files(root, "*.props", "*.csproj", "*.fsproj"):
        text = file.read_text(encoding="utf-8")
        for match in TARGET_FRAMEWORKS.finditer(text):
            for tfm in (t.strip() for t in match[1].split(";")):
                version = NET_TFM.match(tfm)
                if not version:
                    continue
                channel = f"{version[1]}.{version[2]}"
                status = "current" if channel in supported else "unsupported"
                report.items.append(
                    Item(
                        "target framework",
                        _rel(root, file),
                        tfm,
                        tfm,
                        f"net{latest['channel']}",
                        status,
                    )
                )


def _major(value: str) -> int | None:
    match = re.match(r"^\D*(\d+)", value)
    return int(match[1]) if match else None


def scan_node(root: Path, report: Report, node: dict | None) -> None:
    if node is None:
        return
    lts = node["lts"]
    for file in _files(root, ".nvmrc", ".node-version", "dot-nvmrc", "dot-node-version"):
        value = file.read_text(encoding="utf-8").strip()
        if value.startswith("{{"):
            continue  # a template placeholder
        major = _major(value)
        status = "current" if value.startswith("lts/") or (major or 0) >= lts else "outdated"
        report.items.append(
            Item(
                "Node.js",
                _rel(root, file),
                file.name,
                value,
                str(lts),
                status,
                str(lts) if status == "outdated" else None,
            )
        )


def scan_python(root: Path, report: Report, python: dict | None) -> None:
    if python is None:
        return
    latest = python["latest"]
    for file in _files(root, ".python-version", "dot-python-version"):
        value = file.read_text(encoding="utf-8").strip()
        if value.startswith("{{"):
            continue  # a template placeholder
        status = "current" if _minor_key(value) >= _minor_key(latest) else "outdated"
        report.items.append(
            Item(
                "Python",
                _rel(root, file),
                file.name,
                value,
                latest,
                status,
                latest if status == "outdated" else None,
            )
        )


def _minor_key(value: str) -> tuple[int, int]:
    parts = re.findall(r"\d+", value)
    return (int(parts[0]), int(parts[1])) if len(parts) >= 2 else (0, 0)


def scan_workflow_runtimes(
    root: Path, report: Report, node: dict | None, python: dict | None
) -> None:
    for file in _files(root, "*.yml", "*.yaml"):
        text = file.read_text(encoding="utf-8")
        for match in YAML_VERSION.finditer(text):
            value = match["value"]
            if value.startswith("${{") or value.startswith("lts/"):
                continue
            if match["key"] == "node-version" and node:
                major = _major(value)
                status = "current" if (major or 0) >= node["lts"] else "outdated"
                latest = str(node["lts"])
            elif match["key"] == "python-version" and python:
                if value in {"3.x", "3"}:
                    continue
                status = (
                    "current" if _minor_key(value) >= _minor_key(python["latest"]) else "outdated"
                )
                latest = python["latest"]
            else:
                continue
            report.items.append(
                Item(
                    match["key"],
                    _rel(root, file),
                    match["key"],
                    value,
                    latest,
                    status,
                    latest if status == "outdated" else None,
                )
            )


def _package_item(
    kind: str, file: str, name: str, pinned: str, versions: list[str], allow_major: bool
) -> Item:
    clean = re.sub(r"^[\^~>=<v ]+", "", pinned)
    stable = stable_versions(versions)
    if not stable:
        return Item(kind, file, name, pinned, "", "unknown")
    newest = stable[-1]
    current = tuple(int(p) for p in re.findall(r"\d+", clean)[:3]) or (0,)
    major = current[0]
    same_major = [v for v in stable if int(v.split(".")[0]) == major]
    target = newest if allow_major else (same_major[-1] if same_major else None)
    status = "current" if tuple(int(p) for p in newest.split(".")[:3]) <= current else "outdated"
    write = None
    if target and tuple(int(p) for p in target.split(".")[:3]) > current:
        prefix = re.match(r"^[\^~>=<]*", pinned)[0]  # type: ignore[index]
        write = prefix + target
    return Item(kind, file, name, pinned, newest, status, write)


def scan_packages(root: Path, report: Report, fetcher: JsonFetcher, allow_major: bool) -> None:
    def lookup(url: str, extract: Callable[[object], list[str]]) -> list[str] | None:
        try:
            return extract(fetcher(url))
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"{url}: {exc}")
            return None

    for file in _files(root, "package.json"):
        try:
            package = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        manager = str(package.get("packageManager") or "")
        if re.match(r"^(pnpm|npm|yarn)@\d", manager):
            tool, _, pinned = manager.partition("@")
            pinned = pinned.split("+", 1)[0]
            versions = lookup(NPM_URL.format(name=tool), lambda data: [data["version"]])  # type: ignore[index]
            if versions is not None:
                report.items.append(
                    _package_item("packageManager", _rel(root, file), tool, pinned, versions, True)
                )
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, pinned in (package.get(section) or {}).items():
                if not re.match(r"^[\^~]?\d", str(pinned)):
                    continue  # workspace:, file:, git URLs, tags
                versions = lookup(
                    NPM_URL.format(name=urllib.parse.quote(name, safe="@/")),
                    lambda data: [data["version"]],  # type: ignore[index]
                )
                if versions is not None:
                    report.items.append(
                        _package_item("npm", _rel(root, file), name, pinned, versions, allow_major)
                    )
    for file in _files(root, "Directory.Packages.props", "*.csproj", "*.fsproj", "*.props"):
        for match in PACKAGE_VERSION.finditer(file.read_text(encoding="utf-8")):
            versions = lookup(
                NUGET_URL.format(name=match["name"].lower()),
                lambda data: list(data["versions"]),  # type: ignore[index]
            )
            if versions is not None:
                report.items.append(
                    _package_item(
                        "NuGet",
                        _rel(root, file),
                        match["name"],
                        match["version"],
                        versions,
                        allow_major,
                    )
                )
    for file in _files(root, "dotnet-tools.json"):
        try:
            tools = json.loads(file.read_text(encoding="utf-8")).get("tools", {})
        except json.JSONDecodeError:
            continue
        for name, tool in tools.items():
            versions = lookup(NUGET_URL.format(name=name.lower()), lambda d: list(d["versions"]))  # type: ignore[index]
            if versions is not None and tool.get("version"):
                report.items.append(
                    _package_item(
                        "NuGet tool", _rel(root, file), name, tool["version"], versions, allow_major
                    )
                )
    for file in _files(root, "pyproject.toml"):
        for match in PYPI_PIN.finditer(file.read_text(encoding="utf-8")):
            name = match["name"].split("[", 1)[0]
            versions = lookup(PYPI_URL.format(name=name), lambda d: list(d["releases"]))  # type: ignore[index]
            if versions is not None:
                item = _package_item(
                    "PyPI",
                    _rel(root, file),
                    name,
                    match["op"] + match["version"],
                    versions,
                    allow_major,
                )
                report.items.append(item)


def scan_avm(root: Path, report: Report, fetcher: JsonFetcher) -> None:
    cache: dict[str, list[str] | None] = {}
    for file in _files(root, "*.bicep"):
        for match in AVM.finditer(file.read_text(encoding="utf-8")):
            path = match["path"]
            if path not in cache:
                try:
                    cache[path] = list(fetcher(MCR_URL.format(path=path))["tags"])  # type: ignore[index]
                except Exception as exc:  # noqa: BLE001
                    cache[path] = None
                    report.errors.append(f"{path}: {exc}")
            versions = cache[path]
            if versions is not None:
                report.items.append(
                    _package_item(
                        "Bicep module", _rel(root, file), path, match["version"], versions, True
                    )
                )


def scan_pre_commit(root: Path, report: Report, tags_for: TagLister) -> None:
    for file in _files(root, ".pre-commit-config.yaml", "dot-pre-commit-config.yaml"):
        for match in PRE_COMMIT_REPO.finditer(file.read_text(encoding="utf-8")):
            item = Item("pre-commit", _rel(root, file), match["repo"], match["rev"])
            try:
                tag, _ = latest_tag(tags_for(match["repo"]))
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"{match['repo']}: {exc}")
                report.items.append(item)
                continue
            item.latest = tag
            item.status = (
                "current" if parse_version(match["rev"]) == parse_version(tag) else "outdated"
            )
            item.write = tag if item.status == "outdated" else None
            report.items.append(item)


def build_report(
    root: Path,
    fetcher: JsonFetcher = fetch_json,
    tags_for: TagLister = list_tags,
    today: dt.date | None = None,
    allow_major: bool = False,
) -> Report:
    report = Report()
    today = today or dt.date.today()

    def runtime(name: str, compute: Callable[[], object]) -> object:
        try:
            value = compute()
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"{name}: {exc}")
            return None
        report.runtimes[name] = value
        return value

    channels = runtime("dotnet", lambda: dotnet_channels(fetcher(DOTNET_INDEX_URL)))  # type: ignore[arg-type]
    node = runtime(
        "node",
        lambda: node_lines(fetcher(NODE_INDEX_URL), fetcher(NODE_SCHEDULE_URL), today),  # type: ignore[arg-type]
    )
    python = runtime("python", lambda: python_lines(fetcher(PYTHON_CYCLE_URL)))  # type: ignore[arg-type]

    scan_actions(root, report, tags_for)
    scan_dotnet(root, report, channels)  # type: ignore[arg-type]
    scan_node(root, report, node)  # type: ignore[arg-type]
    scan_python(root, report, python)  # type: ignore[arg-type]
    scan_workflow_runtimes(root, report, node, python)  # type: ignore[arg-type]
    scan_packages(root, report, fetcher, allow_major)
    scan_avm(root, report, fetcher)
    scan_pre_commit(root, report, tags_for)
    return report


# --- Writing -------------------------------------------------------------------


def apply_writes(root: Path, report: Report) -> list[str]:
    """Rewrite every pin that has a replacement; return the files changed."""
    by_file: dict[str, list[Item]] = {}
    for item in report.items:
        if item.write:
            by_file.setdefault(item.file, []).append(item)
    changed = []
    for rel, items in sorted(by_file.items()):
        path = root / rel
        text = original = path.read_text(encoding="utf-8")
        for item in items:
            text = _rewrite(text, item, path.name)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(rel)
    return changed


def _rewrite(text: str, item: Item, filename: str) -> str:
    new = item.write or ""
    if item.kind == "action":
        sha, _, tag = new.partition(" # ")

        def replace(match: re.Match[str]) -> str:
            if match["repo"] + (match["path"] or "") != item.name:
                return match[0]
            quote = match["quote"]
            return f"{match['prefix']}{quote}{item.name}@{sha}{quote} # {tag}"

        return USES.sub(replace, text)
    if item.kind == ".NET SDK":
        return re.sub(r'("version"\s*:\s*")[^"]+(")', rf"\g<1>{new}\g<2>", text, count=1)
    if item.kind in {"Node.js", "Python"}:
        return new + "\n"
    if item.kind in {"node-version", "python-version"}:

        def runtime(match: re.Match[str]) -> str:
            if match["key"] != item.kind or match["value"] != item.pinned:
                return match[0]
            return f"{match['prefix']}{match['quote']}{new}{match['quote']}"

        return YAML_VERSION.sub(runtime, text)
    if item.kind == "npm":
        name = re.escape(json.dumps(item.name))
        return re.sub(rf"({name}\s*:\s*\")[^\"]+(\")", rf"\g<1>{new}\g<2>", text)
    if item.kind == "packageManager":
        return re.sub(
            rf'("packageManager"\s*:\s*"{re.escape(item.name)}@)[^"]+(")',
            rf"\g<1>{new}\g<2>",
            text,
        )
    if item.kind == "NuGet":
        name = re.escape(item.name)
        return re.sub(
            rf"((?:Include|Update)=\"{name}\"\s+Version=\"){re.escape(item.pinned)}(\")",
            rf"\g<1>{new}\g<2>",
            text,
        )
    if item.kind == "NuGet tool":
        name = re.escape(json.dumps(item.name))
        return re.sub(
            rf"({name}\s*:\s*\{{\s*\"version\"\s*:\s*\")[^\"]+(\")", rf"\g<1>{new}\g<2>", text
        )
    if item.kind == "PyPI":
        op = item.pinned[:2]
        pattern = rf"(\"{re.escape(item.name)}(?:\[[^\]]*\])?){re.escape(item.pinned)}\""
        return re.sub(pattern, lambda m: f'{m[1]}{op}{new.lstrip("=><")}"', text)
    if item.kind == "Bicep module":
        return text.replace(f"br/public:{item.name}:{item.pinned}", f"br/public:{item.name}:{new}")
    if item.kind == "pre-commit":

        def hook(match: re.Match[str]) -> str:
            if match["repo"] != item.name:
                return match[0]
            return match[0].replace(match["revline"], match["revline"].replace(match["rev"], new))

        return PRE_COMMIT_REPO.sub(hook, text)
    return text


# --- Output --------------------------------------------------------------------


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [max(len(str(c)) for c in column) for column in zip(headers, *rows, strict=False)]
    return [
        "  ".join(f"{cell:<{width}}" for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in [headers, *rows]
    ]


def format_report(report: Report) -> str:
    lines = []
    if channels := report.runtimes.get("dotnet"):
        for c in channels:
            lines.append(
                f".NET {c['channel']} ({c['type'].upper()}): SDK {c['sdk']}, "
                f"runtime {c['runtime']}, end of support {c['eol']}"
            )
    if node := report.runtimes.get("node"):
        maintained = ", ".join(map(str, node["maintained"]))
        lines.append(
            f"Node.js LTS: {node['lts']} ({node['version']}); maintained LTS lines: {maintained}"
        )
    if python := report.runtimes.get("python"):
        lines.append(f"Python: {python['latest']}; supported: {', '.join(python['supported'])}")
    if report.items:
        rows = [
            [i.kind, i.file, i.name, i.pinned, i.latest, i.status.upper()] for i in report.items
        ]
        lines += ["", *_table(["Kind", "File", "Name", "Pinned", "Latest", "Status"], rows)]
    for error in report.errors:
        lines.append(f"ERROR {error}")
    if report.errors:
        lines.append("Some lookups failed: web-search the missing versions instead.")
    return "\n".join(lines)


def to_json(report: Report) -> str:
    return json.dumps(
        {
            "runtimes": report.runtimes,
            "items": [item.__dict__ for item in report.items],
            "errors": report.errors,
        },
        indent=2,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check and update pinned versions.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="repository to check")
    parser.add_argument("--write", action="store_true", help="rewrite outdated pins in place")
    parser.add_argument(
        "--allow-major", action="store_true", help="let --write cross package majors"
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    report = build_report(root, allow_major=args.allow_major)
    print(to_json(report) if args.json else format_report(report))
    if args.write:
        changed = apply_writes(root, report)
        print(f"\nUpdated {len(changed)} file(s)" + "".join(f"\n  {c}" for c in changed))
    if report.errors:
        return 2
    outdated = {"outdated", "unsupported"}
    if root != DEFAULT_ROOT.resolve():
        outdated.add("unpinned")  # templates name actions by tag on purpose
    return 1 if not args.write and any(i.status in outdated for i in report.items) else 0


if __name__ == "__main__":
    sys.exit(main())
