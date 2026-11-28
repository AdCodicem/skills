"""Audit, then update, the account's two Renovate repositories against this skill's templates.

The shared preset (`OWNER/renovate-config`) and the runner (`OWNER/renovate`)
are created once per account (references/renovate.md) and then drift as the
templates improve. This script compares each file they should hold with the
template, filled for the account:

- `default.json` of the preset is compared as JSON. The template's settings and
  package rules (matched by `description`) win; the account's own timezone,
  extra top-level settings and extra package rules are kept.
- the runner's workflow is compared with the action pins and the
  `# renovate:`-annotated versions masked, since Renovate updates those; an
  update keeps the live pins and versions.
- `config.js` takes the bot identity from the live `gitAuthor` (or
  `--bot-slug`); the other files are compared as text.

Without a local clone it reads through `gh api` and only reports. With
`--preset-dir` or `--runner-dir` (a clone of that repository) it reads the clone,
and `--write` rewrites the files that differ there, for review with `git diff`.

Standard library only; `gh` must be authenticated unless both clones are given.

Usage:
    python3 scripts/renovate_repos.py --owner OWNER [--timezone TZ]
        [--bot-slug SLUG] [--preset-repo NAME] [--runner-repo NAME]
        [--preset-dir PATH] [--runner-dir PATH] [--write] [--diff] [--json]

Exit codes: 0 every file matches, 1 something differs or is missing (or was
written), 2 a repository cannot be read.
"""

from __future__ import annotations

import argparse
import base64
import difflib
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import quote

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "renovate"
TIMEOUT = 60

# (path in the repository, template under templates/renovate/, comparison)
FILES = {
    "preset": [
        ("default.json", "preset/default.json", "preset-json"),
        ("README.md", "preset/README.md", "text"),
    ],
    "runner": [
        (".github/workflows/renovate.yml", "runner/dot-github/workflows/renovate.yml", "workflow"),
        ("config.js", "runner/config.js", "text"),
        ("renovate.json", "runner/renovate.json", "json"),
        ("README.md", "runner/README.md", "text"),
    ],
}

HINTS = {"timezone": "--timezone", "renovate-bot": "--bot-slug", "renovate-bot-id": "--bot-slug"}

Runner = Callable[[list[str]], tuple[int, str, str]]

PLACEHOLDER = re.compile(r"\{\{([a-z][a-z0-9-]*)\}\}")
GIT_AUTHOR = re.compile(r"([A-Za-z0-9-]+)\[bot\] <(\d+)\+")
USES = re.compile(r"^(\s*-?\s*uses:\s*)([^@\s]+)@(\S+)(.*)$")
ANNOTATION = re.compile(r"#\s*renovate:")
VERSION_VALUE = re.compile(r"^(\s*[A-Za-z_][A-Za-z0-9_]*:\s*)(\S+)(.*)$")


class ReadError(Exception):
    pass


def run_gh(args: list[str]) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout, completed.stderr


class GhSource:
    """Reads files of OWNER/REPO's default branch through `gh api`."""

    def __init__(self, repo: str, runner: Runner = run_gh) -> None:
        self.repo = repo
        self.runner = runner

    def _get(self, endpoint: str) -> dict | None:
        code, out, err = self.runner(["api", endpoint])
        if code == 0:
            return json.loads(out)
        if "404" in err or "Not Found" in err:
            return None
        raise ReadError(f"{self.repo}: {err.strip() or f'gh exited with {code}'}")

    def exists(self) -> bool:
        return self._get(f"repos/{self.repo}") is not None

    def read(self, path: str) -> str | None:
        data = self._get(f"repos/{self.repo}/contents/{quote(path)}")
        if data is None:
            return None
        if not isinstance(data, dict) or "content" not in data:
            raise ReadError(f"{self.repo}: {path} is not a file")
        return base64.b64decode(data["content"]).decode("utf-8")

    def write(self, path: str, text: str) -> None:
        raise ReadError("--write needs a local clone (--preset-dir or --runner-dir)")


class DirSource:
    """Reads and writes files of a local clone."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.repo = str(root)

    def exists(self) -> bool:
        return self.root.is_dir()

    def read(self, path: str) -> str | None:
        file = self.root / path
        return file.read_text(encoding="utf-8") if file.is_file() else None

    def write(self, path: str, text: str) -> None:
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8", newline="\n")


@dataclass
class Result:
    repo: str
    path: str
    status: str  # ok, drift, missing, unresolved, written
    notes: list[str] = field(default_factory=list)
    diff: str = ""
    proposed: str | None = None


def fill(text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Fills `{{name}}` placeholders; returns the text and the names left unfilled."""
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        name = match[1]
        if name in values:
            return values[name]
        missing.append(name)
        return match[0]

    return PLACEHOLDER.sub(replace, text), sorted(set(missing))


def normalize(text: str) -> str:
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    return "\n".join(lines).strip("\n") + "\n"


def unified(live: str | None, proposed: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            normalize(live or "").splitlines(keepends=True),
            normalize(proposed).splitlines(keepends=True),
            f"live/{path}",
            f"template/{path}",
        )
    )


def _rule_key(rule: dict) -> str:
    return rule.get("description") or json.dumps(rule, sort_keys=True)


def merge_preset(template: dict, live: dict) -> tuple[dict, list[str]]:
    """The template wins; the account's timezone, extra settings and extra rules stay."""
    notes: list[str] = []
    merged = dict(template)
    for key, value in live.items():
        if key == "packageRules":
            continue
        if key not in template:
            merged[key] = value
            notes.append(f"kept the account's own setting `{key}`")
        elif key == "timezone":
            merged[key] = value
        elif value != template[key]:
            notes.append(f"`{key}` differs from the template")
    template_rules = template.get("packageRules", [])
    live_rules = live.get("packageRules", [])
    live_by_key = {_rule_key(r): r for r in live_rules}
    template_keys = {_rule_key(r) for r in template_rules}
    for rule in template_rules:
        key = _rule_key(rule)
        if key not in live_by_key:
            notes.append(f"missing package rule: {key}")
        elif live_by_key[key] != rule:
            notes.append(f"changed package rule: {key}")
    # Later package rules win, so each extra rule stays right after the template
    # rule it followed in the live file (or first, if it came before them all).
    after: dict[str | None, list[dict]] = {}
    previous: str | None = None
    for rule in live_rules:
        key = _rule_key(rule)
        if key in template_keys:
            previous = key
        else:
            after.setdefault(previous, []).append(rule)
            notes.append(f"kept the account's own package rule: {key}")
    rules = list(after.get(None, []))
    for rule in template_rules:
        rules.append(rule)
        rules.extend(after.get(_rule_key(rule), []))
    merged["packageRules"] = rules
    return merged, notes


def _live_pins(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Maps each action to its live `@ref # comment`, each annotated variable to its value."""
    actions: dict[str, str] = {}
    versions: dict[str, str] = {}
    annotated = False
    for line in text.replace("\r\n", "\n").split("\n"):
        if match := USES.match(line):
            actions.setdefault(match[2], match[3] + match[4])
        elif annotated and (match := VERSION_VALUE.match(line)):
            versions[match[1].strip().rstrip(":").strip()] = match[2]
        annotated = bool(ANNOTATION.search(line))
    return actions, versions


def mask_workflow(text: str) -> str:
    out: list[str] = []
    annotated = False
    for line in text.replace("\r\n", "\n").split("\n"):
        if match := USES.match(line):
            line = f"{match[1]}{match[2]}@<pin>"
        elif annotated and (match := VERSION_VALUE.match(line)):
            line = f"{match[1]}<version>{match[3]}"
        annotated = bool(ANNOTATION.search(line))
        out.append(line)
    return normalize("\n".join(out))


def pin_workflow(template: str, live: str) -> str:
    """The template, with the live action pins and annotated versions."""
    actions, versions = _live_pins(live)
    out: list[str] = []
    annotated = False
    for line in template.replace("\r\n", "\n").split("\n"):
        if (match := USES.match(line)) and match[2] in actions:
            line = f"{match[1]}{match[2]}@{actions[match[2]]}"
        elif annotated and (match := VERSION_VALUE.match(line)):
            name = match[1].strip().rstrip(":").strip()
            if name in versions:
                line = f"{match[1]}{versions[name]}{match[3]}"
        annotated = bool(ANNOTATION.search(line))
        out.append(line)
    return "\n".join(out)


def _dump(data: dict) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _result(repo: str, path: str, same: bool, notes: list[str], live: str, proposed: str) -> Result:
    diff = "" if same else unified(live, proposed, path)
    return Result(repo, path, "ok" if same else "drift", notes, diff, proposed)


def compare(repo: str, path: str, kind: str, template: str, live: str | None) -> Result:
    if kind == "preset-json":
        template_data = json.loads(template)
        if live is None:
            return Result(repo, path, "missing", proposed=_dump(template_data))
        merged, notes = merge_preset(template_data, json.loads(live))
        proposed = _dump(merged)
        same = merged == json.loads(live)
        return _result(repo, path, same, notes, live, proposed)
    if kind == "json":
        template_data = json.loads(template)
        if live is None:
            return Result(repo, path, "missing", proposed=template)
        live_data = json.loads(live)
        merged = {**template_data, **{k: v for k, v in live_data.items() if k not in template_data}}
        proposed = _dump(merged)
        same = merged == live_data
        return _result(repo, path, same, [], live, proposed)
    if live is None:
        return Result(repo, path, "missing", proposed=template)
    if kind == "workflow":
        same = mask_workflow(template) == mask_workflow(live)
        proposed = pin_workflow(template, live)
        notes = [] if same else ["action pins and annotated versions are kept from the live file"]
        return _result(repo, path, same, notes, live, proposed)
    same = normalize(template) == normalize(live)
    return _result(repo, path, same, [], live, template)


def resolve_values(
    owner: str, args: argparse.Namespace, sources: dict, runner: Runner
) -> dict[str, str]:
    values = {"owner": owner}
    preset_live = sources["preset"].read("default.json") if sources["preset"].exists() else None
    if preset_live:
        timezone = json.loads(preset_live).get("timezone")
        if timezone:
            values["timezone"] = timezone
    if args.timezone:
        values["timezone"] = args.timezone
    runner_live = sources["runner"].read("config.js") if sources["runner"].exists() else None
    if runner_live and (match := GIT_AUTHOR.search(runner_live)):
        values["renovate-bot"], values["renovate-bot-id"] = match[1], match[2]
    if args.bot_slug and args.bot_slug != values.get("renovate-bot"):
        values["renovate-bot"] = args.bot_slug
        values.pop("renovate-bot-id", None)
        code, out, _ = runner(["api", f"users/{quote(args.bot_slug)}%5Bbot%5D", "-q", ".id"])
        if code == 0 and out.strip().isdigit():
            values["renovate-bot-id"] = out.strip()
    return values


def audit(args: argparse.Namespace, runner: Runner = run_gh) -> list[Result]:
    owner = args.owner

    def source(local: str | None, name: str) -> GhSource | DirSource:
        return DirSource(Path(local)) if local else GhSource(f"{owner}/{name}", runner)

    sources = {
        "preset": source(args.preset_dir, args.preset_repo),
        "runner": source(args.runner_dir, args.runner_repo),
    }
    values = resolve_values(owner, args, sources, runner)
    results: list[Result] = []
    for kind_name, files in FILES.items():
        repo = sources[kind_name]
        if not repo.exists():
            note = "the repository does not exist: create it (references/renovate.md)"
            results.append(Result(repo.repo, "", "missing", [note]))
            continue
        for path, template_path, kind in files:
            raw = (TEMPLATES / template_path).read_text(encoding="utf-8")
            template, unfilled = fill(raw, values)
            if unfilled:
                flags = sorted({HINTS.get(n, n) for n in unfilled})
                note = f"pass {', '.join(flags)}"
                results.append(Result(repo.repo, path, "unresolved", [note]))
                continue
            result = compare(repo.repo, path, kind, template, repo.read(path))
            writable = isinstance(repo, DirSource)
            pending = result.status in ("drift", "missing") and result.proposed
            if args.write and writable and pending:
                repo.write(path, result.proposed)
                result.status = "written"
            results.append(result)
    return results


def format_results(results: list[Result], show_diff: bool) -> str:
    lines = []
    for r in results:
        lines.append(f"  {r.status:<10} {r.repo}{'/' + r.path if r.path else ''}")
        lines.extend(f"             note: {note}" for note in r.notes)
        if show_diff and r.diff:
            lines.append("")
            lines.extend("             " + d for d in r.diff.rstrip("\n").split("\n"))
            lines.append("")
    pending = [r for r in results if r.status != "ok"]
    lines.append("")
    if pending:
        lines.append(f"{len(pending)} file(s) differ, are missing or were written.")
    else:
        lines.append("Everything matches the templates.")
    return "\n".join(lines)


def main(argv: list[str] | None = None, runner: Runner = run_gh) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--owner", required=True, help="the account that owns both repositories")
    parser.add_argument("--preset-repo", default="renovate-config")
    parser.add_argument("--runner-repo", default="renovate")
    parser.add_argument("--preset-dir", help="local clone of the preset repository")
    parser.add_argument("--runner-dir", help="local clone of the runner repository")
    parser.add_argument("--timezone", help="IANA timezone, when the preset does not set one yet")
    parser.add_argument("--bot-slug", help="the Renovate App's slug, if config.js has no gitAuthor")
    parser.add_argument("--write", action="store_true", help="rewrite differing files")
    parser.add_argument("--diff", action="store_true", help="show unified diffs")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)
    if args.write and not (args.preset_dir or args.runner_dir):
        parser.error("--write needs --preset-dir or --runner-dir")
    try:
        results = audit(args, runner)
    except ReadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        rows = [{k: v for k, v in asdict(r).items() if k != "proposed"} for r in results]
        print(json.dumps(rows, indent=2))
    else:
        print(format_results(results, args.diff))
    return 0 if all(r.status == "ok" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
