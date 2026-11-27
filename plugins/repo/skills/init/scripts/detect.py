"""Describe a repository for the repo-init skill: what it holds, what it already has.

Prints JSON with:

- `ecosystems`: the modules whose marker files are present (dotnet, node, react,
  python, bicep, pulumi, cloudflare, terraform, container, docs-site), each with
  the files that revealed it and, where it can be told, the project kind
  (library, application, cli, tooling, infrastructure);
- `files`: every standard file of the fixed core, present or missing;
- `workflows`: the workflow files and what they trigger on, with the risky
  triggers flagged (`pull_request_target`);
- `release` and `dependencies`: the release tool and the dependency bots in place;
- `git`: the default branch, the GitHub remote, whether the history is empty;
- `github`: visibility, owner type, plan, merge settings, when `gh` is
  installed and authenticated (otherwise `available: false` and the reason).

Standard library only. Reads files under --root; calls `git` and `gh` when they
are installed. Never writes anything.

Usage:
    python3 scripts/detect.py [--root DIR] [--no-github]

Exit codes: 0 on success, 2 when --root is not a directory.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path

SKIPPED_DIRS = {".git", "node_modules", "bin", "obj", ".venv", "venv", "dist", "build", ".tox"}
MAX_FILES = 20_000
TIMEOUT = 20

# Standard files of the fixed core, by area. A tuple lists accepted alternatives.
STANDARD_FILES: dict[str, list[str | tuple[str, ...]]] = {
    "hygiene": [
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        (".pre-commit-config.yaml", ".pre-commit-config.yml"),
    ],
    "governance": [
        ("LICENSE", "LICENSE.md", "LICENSE.txt"),
        "README.md",
        ("CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"),
        ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"),
        ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"),
        ("CODE_OF_CONDUCT.md", ".github/CODE_OF_CONDUCT.md", "docs/CODE_OF_CONDUCT.md"),
        (".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md"),
        ".github/ISSUE_TEMPLATE",
        ".github/FUNDING.yml",
    ],
    "ci": [
        ".github/workflows/ci.yml",
        ".github/workflows/lint.yml",
        ".github/workflows/actions.lock",
    ],
    "release": [
        (".releaserc.json", ".releaserc", ".releaserc.yml", "release.config.js"),
        ".github/workflows/release.yml",
        ".github/workflows/preview.yml",
        "CHANGELOG.md",
    ],
    "dependencies": [
        (".github/dependabot.yml", ".github/dependabot.yaml"),
        ("renovate.json", "renovate.json5", ".github/renovate.json", ".renovaterc"),
    ],
    "security": [".github/workflows/codeql.yml", ".github/zizmor.yml"],
    "docs": ["docs/adr", "ARCHITECTURE.md", "docs/website"],
    "agents": ["CLAUDE.md", "AGENTS.md"],
}

ON_LINE = re.compile(r"^['\"]?on['\"]?\s*:(.*)$")
NON_PRODUCT_DIRS = {"tests", "test", "samples", "sample", "benchmarks", "tools", "examples"}

Runner = Callable[[list[str]], str | None]


def iter_files(root: Path) -> list[Path]:
    """Files under root, skipping build output and dependency folders, bounded."""
    found: list[Path] = []
    stack = [root]
    while stack and len(found) < MAX_FILES:
        folder = stack.pop()
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIPPED_DIRS:
                    stack.append(entry)
            elif entry.is_file():
                found.append(entry)
    return found


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _node_kind(package: dict) -> str:
    dependencies = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    if package.get("bin"):
        return "cli"
    if (
        package.get("private")
        and not package.get("dependencies")
        and ("semantic-release" in dependencies or not dependencies)
    ):
        return "tooling"
    if package.get("private") or any(
        name in dependencies for name in ("vite", "next", "react-scripts", "@remix-run/dev")
    ):
        return "application"
    if any(key in package for key in ("exports", "main", "module", "types")):
        return "library"
    return "unknown"


def _dotnet_kind(text: str) -> str:
    """The kind of one project file."""
    if re.search(r"<IsTestProject>\s*true", text, re.IGNORECASE):
        return "test"
    if re.search(r"<PackAsTool>\s*true", text, re.IGNORECASE):
        return "cli"
    if re.search(r'Sdk="Microsoft\.NET\.Sdk\.(Web|Worker|BlazorWebAssembly)"', text) or re.search(
        r"<OutputType>\s*(Win)?Exe\s*</OutputType>", text, re.IGNORECASE
    ):
        return "application"
    return "library"


def _python_kind(pyproject: dict) -> str:
    project = pyproject.get("project", {})
    if project.get("scripts"):
        return "cli"
    if "build-system" in pyproject:
        return "library"
    return "application" if project else "unknown"


def detect_ecosystems(root: Path, files: list[Path]) -> dict[str, dict]:
    ecosystems: dict[str, dict] = {}

    def add(name: str, path: Path, kind: str | None = None, **extra: object) -> None:
        entry = ecosystems.setdefault(name, {"markers": [], "kinds": []})
        rel = _rel(root, path)
        if rel not in entry["markers"]:
            entry["markers"].append(rel)
        if kind and kind not in entry["kinds"]:
            entry["kinds"].append(kind)
        for key, value in extra.items():
            entry.setdefault(key, value)

    projects = [f for f in files if f.suffix in {".csproj", ".fsproj"}]
    for file in files:
        name = file.name
        if file.suffix in {".sln", ".slnx"} or name == "global.json":
            add("dotnet", file)
        elif name == "package.json":
            try:
                package = json.loads(_read(file))
            except json.JSONDecodeError:
                package = {}
            if not isinstance(package, dict):
                package = {}
            dependencies = {
                **package.get("dependencies", {}),
                **package.get("devDependencies", {}),
                **package.get("peerDependencies", {}),
            }
            manager = str(package.get("packageManager", "")).split("@", 1)[0] or None
            if "@docusaurus/core" in dependencies:
                add("docs-site", file, "docusaurus")
            elif "react" in dependencies and _node_kind(package) == "application":
                add("react", file, "application", package_manager=manager)
            else:
                add("node", file, _node_kind(package), package_manager=manager)
        elif name in {"pyproject.toml", "setup.py", "setup.cfg"}:
            kind = None
            if name == "pyproject.toml":
                try:
                    kind = _python_kind(tomllib.loads(_read(file)))
                except tomllib.TOMLDecodeError:
                    kind = "unknown"
            add("python", file, kind)
        elif (
            file.suffix == ".bicep" or name in {"bicepconfig.json"} or file.suffix == ".bicepparam"
        ):
            add("bicep", file, "infrastructure")
        elif name in {"Pulumi.yaml", "Pulumi.yml"}:
            runtime = re.search(r"^runtime:\s*(?:\n\s+name:\s*)?([a-z]+)", _read(file), re.M)
            add("pulumi", file, "infrastructure", runtime=runtime[1] if runtime else None)
        elif name in {"wrangler.toml", "wrangler.json", "wrangler.jsonc"}:
            add("cloudflare", file, "application")
        elif file.suffix in {".tf", ".tofu"}:
            add("terraform", file, "infrastructure")
        elif name in {"Dockerfile", "Containerfile"} or name.endswith(".Dockerfile"):
            add("container", file)
    product = [p for p in projects if not NON_PRODUCT_DIRS.intersection(p.relative_to(root).parts)]
    for project in product or projects:
        kind = _dotnet_kind(_read(project))
        add("dotnet", project, None if kind == "test" else kind)
    for entry in ecosystems.values():
        entry["markers"] = entry["markers"][:10]
    return ecosystems


def detect_files(root: Path) -> dict[str, dict[str, str | None]]:
    """Each standard file: the path found, or None when missing."""
    result: dict[str, dict[str, str | None]] = {}
    for area, entries in STANDARD_FILES.items():
        area_result: dict[str, str | None] = {}
        for entry in entries:
            options = entry if isinstance(entry, tuple) else (entry,)
            found = next((option for option in options if (root / option).exists()), None)
            area_result[options[0]] = found
        result[area] = area_result
    return result


def workflow_triggers(text: str) -> list[str]:
    """The events under a workflow's top-level `on:` key, without a YAML parser."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = ON_LINE.match(line)
        if not match:
            continue
        inline = match[1].split("#", 1)[0].strip()
        if inline:
            return sorted(set(re.findall(r"[a-z_]+", inline)))
        triggers: list[str] = []
        indent = None
        for child in lines[index + 1 :]:
            stripped = child.split("#", 1)[0].rstrip()
            if not stripped.strip():
                continue
            depth = len(stripped) - len(stripped.lstrip())
            if depth == 0:
                break
            indent = depth if indent is None else indent
            if depth == indent:
                key = re.match(r"\s*-?\s*([a-z_]+)", stripped)
                if key:
                    triggers.append(key[1])
        return sorted(set(triggers))
    return []


def detect_workflows(root: Path) -> list[dict]:
    folder = root / ".github" / "workflows"
    workflows = []
    for file in sorted(folder.glob("*.y*ml")) if folder.is_dir() else []:
        text = _read(file)
        triggers = workflow_triggers(text)
        workflows.append(
            {
                "file": _rel(root, file),
                "triggers": triggers,
                "pull_request_target": "pull_request_target" in triggers,
                "unpinned_actions": len(
                    re.findall(r"uses:\s*['\"]?[\w.-]+/[\w./-]+@(?![0-9a-f]{40})", text)
                ),
            }
        )
    return workflows


def detect_release(root: Path) -> dict:
    tools = []
    if any(
        (root / name).exists() for name in (".releaserc.json", ".releaserc", "release.config.js")
    ):
        tools.append("semantic-release")
    if (root / "release-please-config.json").exists():
        tools.append("release-please")
    if (root / ".changeset").is_dir():
        tools.append("changesets")
    if any(p.name == "GitVersion.yml" for p in root.glob("*")):
        tools.append("gitversion")
    return {"tools": tools}


def detect_dependencies(root: Path) -> dict:
    bots = {}
    dependabot = next(
        (
            root / p
            for p in (".github/dependabot.yml", ".github/dependabot.yaml")
            if (root / p).exists()
        ),
        None,
    )
    if dependabot:
        bots["dependabot"] = sorted(
            set(re.findall(r"package-ecosystem:\s*['\"]?([\w-]+)", _read(dependabot)))
        )
    renovate = next(
        (
            root / p
            for p in ("renovate.json", "renovate.json5", ".github/renovate.json", ".renovaterc")
            if (root / p).exists()
        ),
        None,
    )
    if renovate:
        bots["renovate"] = _rel(root, renovate)
    return bots


def run_command(command: list[str]) -> str | None:
    """Run a command; return its stdout, or None when it is missing or fails."""
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def parse_remote(url: str) -> str | None:
    """`https://github.com/o/r.git` or `git@github.com:o/r.git` -> `o/r`."""
    match = re.search(r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url.strip())
    return f"{match[1]}/{match[2]}" if match else None


def detect_git(root: Path, runner: Runner = run_command) -> dict:
    inside = runner(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"])
    if not inside or inside.strip() != "true":
        return {"repository": False}
    remote = runner(["git", "-C", str(root), "remote", "get-url", "origin"])
    head = runner(["git", "-C", str(root), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if not head:
        branches = runner(["git", "-C", str(root), "branch", "--list", "--all", "main", "master"])
        head = next((b.strip(" *") for b in (branches or "").splitlines() if b.strip()), None)
    commits = runner(["git", "-C", str(root), "rev-list", "--count", "HEAD"])
    tags = runner(["git", "-C", str(root), "tag", "--list", "v*"])
    return {
        "repository": True,
        "github": parse_remote(remote) if remote else None,
        "default_branch": head.strip().split("/", 1)[-1] if head else None,
        "commits": int(commits.strip()) if commits and commits.strip().isdigit() else 0,
        "version_tags": sorted(tags.split())[-5:] if tags else [],
    }


def detect_github(repo: str | None, runner: Runner = run_command) -> dict:
    if not repo:
        return {"available": False, "reason": "no GitHub remote"}
    data = runner(["gh", "api", f"repos/{repo}"])
    if data is None:
        return {
            "available": False,
            "reason": "gh is not installed, not authenticated, or the repository is unreachable",
        }
    try:
        info = json.loads(data)
    except json.JSONDecodeError:
        return {"available": False, "reason": "unexpected answer from gh api"}
    owner = info.get("owner", {})
    result = {
        "available": True,
        "visibility": info.get("visibility"),
        "owner_type": owner.get("type"),
        "default_branch": info.get("default_branch"),
        "is_admin": info.get("permissions", {}).get("admin"),
        "merge": {
            key: info.get(key)
            for key in (
                "allow_squash_merge",
                "allow_merge_commit",
                "allow_rebase_merge",
                "allow_auto_merge",
                "delete_branch_on_merge",
                "squash_merge_commit_title",
            )
        },
        "plan": None,
    }
    endpoint = "user" if owner.get("type") == "User" else f"orgs/{owner.get('login')}"
    plan_data = runner(["gh", "api", endpoint])
    if plan_data:
        try:
            plan = json.loads(plan_data).get("plan") or {}
            if owner.get("type") != "User" or json.loads(plan_data).get("login") == owner.get(
                "login"
            ):
                result["plan"] = plan.get("name")
        except json.JSONDecodeError:
            pass
    return result


def suggest_profile(github: dict) -> str | None:
    if not github.get("available"):
        return None
    public = github.get("visibility") == "public"
    if github.get("owner_type") == "User":
        return "personal-oss" if public else "personal-private"
    return "company-oss" if public else "company-private"


def detect(root: Path, use_github: bool = True, runner: Runner = run_command) -> dict:
    files = iter_files(root)
    git = detect_git(root, runner)
    github = (
        detect_github(git.get("github"), runner)
        if use_github
        else {
            "available": False,
            "reason": "--no-github",
        }
    )
    return {
        "root": str(root),
        "empty": not any(f for f in files if ".git" not in f.relative_to(root).parts),
        "ecosystems": detect_ecosystems(root, files),
        "files": detect_files(root),
        "workflows": detect_workflows(root),
        "release": detect_release(root),
        "dependencies": detect_dependencies(root),
        "git": git,
        "github": github,
        "suggested_profile": suggest_profile(github),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Describe a repository for repo-init.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository to describe")
    parser.add_argument("--no-github", action="store_true", help="do not call gh")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    print(json.dumps(detect(root, use_github=not args.no_github), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
