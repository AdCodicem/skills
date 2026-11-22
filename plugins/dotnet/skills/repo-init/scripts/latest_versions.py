"""Report the latest .NET LTS release and check GitHub Action pins.

Prints the current LTS .NET channel with its latest SDK and runtime, then
compares every `uses: owner/repo@ref` found in the workflow files with the
action's latest release.

Standard library only. Needs network access to builds.dotnet.microsoft.com
and github.com. Action tags come from `git ls-remote` when git is installed,
otherwise from the GitHub REST API (set GITHUB_TOKEN to raise its rate limit).

Usage:
    python3 scripts/latest_versions.py [--workflows DIR ...] [--json]

By default it checks this skill's templates (templates/dot-github/workflows).

Exit codes: 0 every pin is current, 1 some pins are outdated, 2 a lookup failed.
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
from pathlib import Path

DOTNET_INDEX_URL = "https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json"
DEFAULT_WORKFLOWS = Path(__file__).resolve().parents[1] / "templates" / "dot-github" / "workflows"
USES = re.compile(
    r"^\s*(?:-\s*)?uses:\s*['\"]?"
    r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:/[^@\s'\"]*)?@(?P<ref>[^\s'\"#]+)",
    re.MULTILINE,
)
VERSION_TAG = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")
SHA = re.compile(r"^[0-9a-f]{40}$")
TIMEOUT = 20

TagLister = Callable[[str], list[str]]
JsonFetcher = Callable[[str], dict]


def parse_version(tag: str) -> tuple[int, int, int] | None:
    """`v6.1.0` -> (6, 1, 0); `v6` -> (6, 0, 0); anything else -> None."""
    match = VERSION_TAG.match(tag)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def find_pins(paths: Iterable[Path]) -> dict[str, set[str]]:
    """Map each action repository (`owner/repo`) to the refs pinned in workflow files."""
    pins: dict[str, set[str]] = {}
    for path in paths:
        files = sorted(path.glob("*.y*ml")) if path.is_dir() else [path]
        for file in files:
            for match in USES.finditer(file.read_text(encoding="utf-8")):
                pins.setdefault(match["repo"], set()).add(match["ref"])
    return pins


def latest_lts(index: dict) -> dict:
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


def fetch_json(url: str) -> dict | list:
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
    pins: dict[str, set[str]],
    tag_lister: TagLister = list_tags,
    index_fetcher: JsonFetcher = fetch_json,
) -> dict:
    report: dict = {"dotnet": None, "actions": [], "errors": []}
    try:
        report["dotnet"] = latest_lts(index_fetcher(DOTNET_INDEX_URL))
    except Exception as exc:  # noqa: BLE001 - report every lookup failure, never crash
        report["errors"].append(f".NET releases index: {exc}")

    for repo in sorted(pins):
        try:
            latest_tag, pin = latest_release(tag_lister(repo))
        except Exception as exc:  # noqa: BLE001
            report["errors"].append(f"{repo}: {exc}")
            continue
        for ref in sorted(pins[repo]):
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


def format_report(report: dict) -> str:
    lines = []
    dotnet = report["dotnet"]
    if dotnet:
        lines.append(
            f".NET LTS: {dotnet['channel']} (SDK {dotnet['sdk']}, runtime {dotnet['runtime']}, "
            f"{dotnet['support_phase']}, end of support {dotnet['eol_date']})"
        )
    if report["actions"]:
        width = max(len(item["action"]) for item in report["actions"])
        lines.append("")
        lines.append(f"{'Action':<{width}}  {'Pinned':<10}  {'Latest':<10}  {'Use':<10}  Status")
        for item in report["actions"]:
            lines.append(
                f"{item['action']:<{width}}  {item['pinned']:<10}  {item['latest']:<10}  "
                f"{item['recommended']:<10}  {item['status'].upper()}"
            )
    for error in report["errors"]:
        lines.append(f"ERROR {error}")
    if report["errors"]:
        lines.append("Some lookups failed: web-search the missing versions instead.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report the latest .NET LTS and action versions.")
    parser.add_argument(
        "--workflows",
        type=Path,
        action="append",
        help="workflow folder or file to check (default: this skill's templates)",
    )
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    report = build_report(find_pins(args.workflows or [DEFAULT_WORKFLOWS]))
    print(json.dumps(report, indent=2) if args.json else format_report(report))
    if report["errors"]:
        return 2
    return 1 if any(item["status"] == "outdated" for item in report["actions"]) else 0


if __name__ == "__main__":
    sys.exit(main())
