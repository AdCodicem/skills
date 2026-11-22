"""Check a .NET repository's pinned versions against the latest releases.

Reports the current LTS releases of .NET and Node.js, then checks:

- every `uses: owner/repo@ref` in the workflow files against the action's
  latest release;
- the SDK pinned in `global.json` against the latest .NET LTS SDK;
- the highest `netX.Y` target framework in `*.props` and `*.csproj` files
  against the .NET LTS channel;
- every `node-version:` in the workflow files against the Node.js LTS.

Standard library only. Needs network access to builds.dotnet.microsoft.com,
nodejs.org and github.com. Action tags come from `git ls-remote` when git is
installed, otherwise from the GitHub REST API (set GITHUB_TOKEN to raise its
rate limit).

Usage:
    python3 scripts/latest_versions.py [--root DIR] [--json]

--root is the repository to check (default: this skill's templates). Workflows
are read from `.github/workflows/` or `dot-github/workflows/` under it.

Exit codes: 0 everything is current, 1 something is outdated, 2 a lookup failed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

DOTNET_INDEX_URL = "https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json"
NODE_INDEX_URL = "https://nodejs.org/dist/index.json"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "templates"
WORKFLOW_DIRS = (".github/workflows", "dot-github/workflows")
SKIPPED_DIRS = {"bin", "obj", "node_modules", ".git"}
USES = re.compile(
    r"^\s*(?:-\s*)?uses:\s*['\"]?"
    r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/[^@\s'\"]*)?@(?P<ref>[^\s'\"#]+)",
    re.MULTILINE,
)
NODE_VERSION = re.compile(r"^\s*node-version:\s*['\"]?(?P<value>[^\s'\"#]+)", re.MULTILINE)
TARGET_FRAMEWORKS = re.compile(r"<TargetFrameworks?>([^<]+)</TargetFrameworks?>")
NET_TFM = re.compile(r"^net(\d+)\.(\d+)")
VERSION_TAG = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
SHA = re.compile(r"^[0-9a-f]{40}$")
TIMEOUT = 20

TagLister = Callable[[str], list[str]]
JsonFetcher = Callable[[str], object]


@dataclass
class Pins:
    """Versions pinned in a repository, with the file each one comes from."""

    actions: dict[str, set[str]] = field(default_factory=dict)
    node: list[tuple[str, str]] = field(default_factory=list)
    sdk: list[tuple[str, str]] = field(default_factory=list)
    frameworks: list[tuple[str, str]] = field(default_factory=list)


def parse_version(tag: str) -> tuple[int, int, int] | None:
    """`v6.1.0` -> (6, 1, 0); `v6` -> (6, 0, 0); anything else -> None."""
    match = VERSION_TAG.match(tag)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def _files(root: Path, pattern: str) -> list[Path]:
    return sorted(
        p for p in root.rglob(pattern) if not SKIPPED_DIRS.intersection(p.relative_to(root).parts)
    )


def scan(root: Path) -> Pins:
    """Collect action, Node.js, SDK and target framework pins under `root`."""
    pins = Pins()
    for folder in WORKFLOW_DIRS:
        for file in sorted((root / folder).glob("*.y*ml")):
            text = file.read_text(encoding="utf-8")
            name = file.relative_to(root).as_posix()
            for match in USES.finditer(text):
                pins.actions.setdefault(match["repo"], set()).add(match["ref"])
            pins.node.extend((name, m["value"]) for m in NODE_VERSION.finditer(text))

    global_json = root / "global.json"
    if global_json.is_file():
        version = json.loads(global_json.read_text(encoding="utf-8")).get("sdk", {}).get("version")
        if version:
            pins.sdk.append(("global.json", version))

    for file in _files(root, "*.props") + _files(root, "*.csproj"):
        text = file.read_text(encoding="utf-8")
        tfms = [t.strip() for m in TARGET_FRAMEWORKS.finditer(text) for t in m[1].split(";")]
        versioned = [
            (tuple(map(int, NET_TFM.match(t).groups())), t) for t in tfms if NET_TFM.match(t)
        ]
        if versioned:
            pins.frameworks.append((file.relative_to(root).as_posix(), max(versioned)[1]))
    return pins


def latest_dotnet_lts(index: dict) -> dict:
    """Pick the newest supported LTS channel from the .NET releases index."""
    candidates = [
        release
        for release in index.get("releases-index", [])
        if release.get("release-type") == "lts"
        and release.get("support-phase") in {"active", "maintenance"}
    ]
    if not candidates:
        raise ValueError("no supported LTS release in the .NET releases index")
    best = max(candidates, key=lambda r: tuple(int(p) for p in r["channel-version"].split(".")))
    return {
        "channel": best["channel-version"],
        "sdk": best["latest-sdk"],
        "runtime": best["latest-runtime"],
        "support_phase": best["support-phase"],
        "eol_date": best.get("eol-date"),
    }


def latest_node_lts(index: list[dict]) -> dict:
    """The newest LTS line in the Node.js release index is the active LTS."""
    releases = [r for r in index if r.get("lts")]
    if not releases:
        raise ValueError("no LTS release in the Node.js index")
    best = max(releases, key=lambda r: parse_version(r["version"]) or (0, 0, 0))
    return {
        "major": parse_version(best["version"])[0],
        "version": best["version"],
        "codename": best["lts"],
    }


def latest_release(tags: Iterable[str]) -> tuple[str, str]:
    """Return (latest version tag, recommended pin) for an action.

    The recommended pin is the bare major tag (`v6`) when the action publishes
    one, otherwise the full latest version (`v2.6.0`).
    """
    versions = [(parse_version(tag), tag) for tag in tags]
    versions = [(version, tag) for version, tag in versions if version is not None]
    if not versions:
        raise ValueError("no version tags found")
    full = [(version, tag) for version, tag in versions if tag.count(".") == 2]
    latest_version, latest_tag = max(full or versions)
    major_tag = f"v{latest_version[0]}"
    pin = major_tag if major_tag in {tag for _, tag in versions} else latest_tag
    return latest_tag, pin


def pin_status(ref: str, latest_tag: str) -> str:
    """`current`, `outdated`, or `unknown` (SHA or branch pins)."""
    if SHA.match(ref):
        return "unknown"
    pinned, latest = parse_version(ref), parse_version(latest_tag)
    if pinned is None or latest is None:
        return "unknown"
    depth = ref.count(".") + 1  # v6 -> compare major only, v2.6.0 -> compare all
    return "current" if pinned[:depth] >= latest[:depth] else "outdated"


def node_status(value: str, lts_major: int) -> str:
    """Compare a `node-version` value (`26`, `26.x`, `lts/*`...) with the LTS major."""
    if value.startswith("lts/"):
        return "current"
    match = re.match(r"^\D*(\d+)", value)
    if not match:
        return "unknown"
    return "current" if int(match[1]) >= lts_major else "outdated"


def sdk_status(pinned: str, latest: str) -> str:
    pinned_version, latest_version = parse_version(pinned), parse_version(latest)
    if pinned_version is None or latest_version is None:
        return "unknown"
    return "current" if pinned_version >= latest_version else "outdated"


def framework_status(tfm: str, channel: str) -> str:
    match = NET_TFM.match(tfm)
    if not match:
        return "unknown"
    lts = tuple(int(part) for part in channel.split("."))
    return "current" if tuple(map(int, match.groups())) >= lts else "outdated"


def git_tags(repo: str) -> list[str]:
    git = shutil.which("git")
    if not git:
        raise OSError("git is not installed")
    result = subprocess.run(
        [git, "ls-remote", "--tags", "--refs", f"https://github.com/{repo}"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=True,
    )
    return [line.rsplit("refs/tags/", 1)[-1] for line in result.stdout.splitlines() if line]


def fetch_json(url: str) -> object:
    headers = {"Accept": "application/json", "User-Agent": "dotnet-repo-init-skill"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read())


def api_tags(repo: str) -> list[str]:
    data = fetch_json(f"https://api.github.com/repos/{repo}/tags?per_page=100")
    return [item["name"] for item in data]


def list_tags(repo: str) -> list[str]:
    try:
        return git_tags(repo)
    except (OSError, subprocess.SubprocessError):
        return api_tags(repo)


def build_report(
    pins: Pins,
    tag_lister: TagLister = list_tags,
    fetcher: JsonFetcher = fetch_json,
) -> dict:
    report: dict = {"dotnet": None, "node": None, "runtimes": [], "actions": [], "errors": []}
    for key, url, parse in (
        ("dotnet", DOTNET_INDEX_URL, latest_dotnet_lts),
        ("node", NODE_INDEX_URL, latest_node_lts),
    ):
        try:
            report[key] = parse(fetcher(url))
        except Exception as exc:  # noqa: BLE001 - report every lookup failure, never crash
            report["errors"].append(f"{url}: {exc}")

    def runtime(name: str, file: str, pinned: str, latest: str, status: str) -> None:
        report["runtimes"].append(
            {"runtime": name, "file": file, "pinned": pinned, "latest": latest, "status": status}
        )

    if dotnet := report["dotnet"]:
        for file, version in pins.sdk:
            runtime(".NET SDK", file, version, dotnet["sdk"], sdk_status(version, dotnet["sdk"]))
        latest_tfm = f"net{dotnet['channel']}"
        for file, tfm in pins.frameworks:
            status = framework_status(tfm, dotnet["channel"])
            runtime("Target framework", file, tfm, latest_tfm, status)
    if node := report["node"]:
        for file, value in pins.node:
            runtime("Node.js", file, value, str(node["major"]), node_status(value, node["major"]))

    for repo in sorted(pins.actions):
        try:
            latest_tag, pin = latest_release(tag_lister(repo))
        except Exception as exc:  # noqa: BLE001
            report["errors"].append(f"{repo}: {exc}")
            continue
        for ref in sorted(pins.actions[repo]):
            report["actions"].append(
                {
                    "action": repo,
                    "pinned": ref,
                    "latest": latest_tag,
                    "recommended": pin,
                    "status": pin_status(ref, latest_tag),
                }
            )
    return report


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [
        max(len(str(cell)) for cell in column) for column in zip(headers, *rows, strict=False)
    ]
    return [
        "  ".join(f"{cell:<{width}}" for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in [headers, *rows]
    ]


def format_report(report: dict) -> str:
    lines = []
    if dotnet := report["dotnet"]:
        lines.append(
            f".NET LTS: {dotnet['channel']} (SDK {dotnet['sdk']}, runtime {dotnet['runtime']}, "
            f"{dotnet['support_phase']}, end of support {dotnet['eol_date']})"
        )
    if node := report["node"]:
        lines.append(f"Node.js LTS: {node['major']} ({node['version']}, {node['codename']})")
    if report["runtimes"]:
        rows = [
            [r["runtime"], r["file"], r["pinned"], r["latest"], r["status"].upper()]
            for r in report["runtimes"]
        ]
        lines += ["", *_table(["Runtime", "File", "Pinned", "Latest", "Status"], rows)]
    if report["actions"]:
        rows = [
            [a["action"], a["pinned"], a["latest"], a["recommended"], a["status"].upper()]
            for a in report["actions"]
        ]
        lines += ["", *_table(["Action", "Pinned", "Latest", "Use", "Status"], rows)]
    for error in report["errors"]:
        lines.append(f"ERROR {error}")
    if report["errors"]:
        lines.append("Some lookups failed: web-search the missing versions instead.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check pinned versions against latest releases.")
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="repository to check (default: this skill's templates)",
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    report = build_report(scan(args.root.resolve()))
    print(json.dumps(report, indent=2) if args.json else format_report(report))
    if report["errors"]:
        return 2
    items = report["runtimes"] + report["actions"]
    return 1 if any(item["status"] == "outdated" for item in items) else 0


if __name__ == "__main__":
    sys.exit(main())
