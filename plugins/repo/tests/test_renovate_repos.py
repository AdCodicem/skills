"""Tests for skills/init/scripts/renovate_repos.py, with a fake gh and local clones."""

from __future__ import annotations

import base64
import importlib.util
import json
import re
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "init" / "scripts" / "renovate_repos.py"
spec = importlib.util.spec_from_file_location("renovate_repos", SCRIPT)
rr = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rr
spec.loader.exec_module(rr)

OWNER = "me"
BOT = "me-renovate"
BOT_ID = "4242"
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"


def template(path: str, **extra: str) -> str:
    values = {"owner": OWNER, "timezone": "Europe/Paris", "renovate-bot": BOT}
    values["renovate-bot-id"] = BOT_ID
    values.update(extra)
    text, missing = rr.fill((rr.TEMPLATES / path).read_text(encoding="utf-8"), values)
    assert not missing
    return text


def pinned(text: str) -> str:
    """The workflow as Renovate keeps it: actions by SHA, a newer annotated version."""
    text = text.replace("actions/checkout@v7", f"actions/checkout@{CHECKOUT_SHA} # v7.0.1")
    return re.sub(r"RENOVATE_VERSION: \S+", "RENOVATE_VERSION: 99.0.0", text)


def clone(root: Path, files: dict[str, str]) -> Path:
    for path, text in files.items():
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8", newline="\n")
    return root


def current_clones(tmp_path: Path) -> tuple[Path, Path]:
    preset = clone(
        tmp_path / "preset",
        {
            "default.json": template("preset/default.json"),
            "groups-ecosystem.json": template("preset/groups-ecosystem.json"),
            "groups-weekly.json": template("preset/groups-weekly.json"),
            "README.md": template("preset/README.md"),
        },
    )
    runner = clone(
        tmp_path / "runner",
        {
            ".github/workflows/renovate.yml": template("runner/dot-github/workflows/renovate.yml"),
            "config.js": template("runner/config.js"),
            "renovate.json": template("runner/renovate.json"),
            "README.md": template("runner/README.md"),
        },
    )
    return preset, runner


def run(*args: str, runner=None) -> int:
    argv = ["--owner", OWNER, *args]
    return rr.main(argv, runner) if runner else rr.main(argv)


def test_fill_reports_unfilled_placeholders():
    text, missing = rr.fill("{{owner}} {{timezone}} ${{ env.X }}", {"owner": "me"})
    assert text == "me {{timezone}} ${{ env.X }}"
    assert missing == ["timezone"]


def test_current_clones_match(tmp_path, capsys):
    preset, runner = current_clones(tmp_path)
    assert run("--preset-dir", str(preset), "--runner-dir", str(runner)) == 0
    assert "Everything matches" in capsys.readouterr().out


def test_identity_and_timezone_come_from_the_live_files(tmp_path):
    preset, runner = current_clones(tmp_path)
    args = rr.argparse.Namespace(timezone=None, bot_slug=None)
    sources = {"preset": rr.DirSource(preset), "runner": rr.DirSource(runner)}
    values = rr.resolve_values(OWNER, args, sources, runner=lambda a: (1, "", ""))
    assert values["timezone"] == "Europe/Paris"
    assert (values["renovate-bot"], values["renovate-bot-id"]) == (BOT, BOT_ID)


def test_unknown_identity_is_unresolved(tmp_path, capsys):
    preset, runner = current_clones(tmp_path)
    (runner / "config.js").write_text("module.exports = {};\n", encoding="utf-8")
    assert run("--preset-dir", str(preset), "--runner-dir", str(runner), "--json") == 1
    rows = {r["path"]: r for r in json.loads(capsys.readouterr().out)}
    assert rows["config.js"]["status"] == "unresolved"
    assert rows["config.js"]["notes"] == ["pass --bot-slug"]


def test_preset_keeps_account_rules_in_place_and_adds_missing_ones(tmp_path):
    data = json.loads(template("preset/default.json"))
    own = {"description": "Our own rule.", "matchPackageNames": ["x"], "enabled": False}
    dropped = data["packageRules"].pop(1)
    data["packageRules"].insert(1, own)
    data["timezone"] = "UTC"
    data["extraSetting"] = True
    merged, notes = rr.merge_preset(json.loads(template("preset/default.json")), data)
    keys = [r["description"] for r in merged["packageRules"]]
    assert keys.index("Our own rule.") == keys.index(data["packageRules"][0]["description"]) + 1
    assert dropped["description"] in keys
    assert merged["timezone"] == "UTC"
    assert merged["extraSetting"] is True
    assert f"missing package rule: {dropped['description']}" in notes
    assert "kept the account's own package rule: Our own rule." in notes


def test_preset_drift_is_written_to_the_clone(tmp_path, capsys):
    preset, runner = current_clones(tmp_path)
    data = json.loads((preset / "default.json").read_text(encoding="utf-8"))
    data["minimumReleaseAge"] = "1 day"
    (preset / "default.json").write_text(json.dumps(data), encoding="utf-8")
    assert run("--preset-dir", str(preset), "--runner-dir", str(runner), "--write") == 1
    assert "written" in capsys.readouterr().out
    written = json.loads((preset / "default.json").read_text(encoding="utf-8"))
    assert written["minimumReleaseAge"] == "3 days"
    assert run("--preset-dir", str(preset), "--runner-dir", str(runner)) == 0


def test_workflow_pins_are_not_drift_and_are_kept(tmp_path):
    raw = template("runner/dot-github/workflows/renovate.yml")
    live = pinned(raw)
    assert rr.compare("r", "w.yml", "workflow", raw, live).status == "ok"
    changed = raw.replace("timeout-minutes: 45", "timeout-minutes: 90")
    result = rr.compare("r", "w.yml", "workflow", changed, live)
    assert result.status == "drift"
    assert f"actions/checkout@{CHECKOUT_SHA} # v7.0.1" in result.proposed
    assert "RENOVATE_VERSION: 99.0.0" in result.proposed
    assert "timeout-minutes: 90" in result.proposed


def test_missing_files_are_written(tmp_path):
    preset, runner = current_clones(tmp_path)
    (runner / "README.md").unlink()
    assert run("--preset-dir", str(preset), "--runner-dir", str(runner), "--write") == 1
    assert (runner / "README.md").read_text(encoding="utf-8") == template("runner/README.md")


def test_write_needs_a_clone(capsys):
    try:
        run("--write")
    except SystemExit as exc:
        assert exc.code == 2
    assert "--write needs" in capsys.readouterr().err


class FakeGh:
    def __init__(self, files: dict[str, dict[str, str]]) -> None:
        self.files = files

    def __call__(self, args: list[str]) -> tuple[int, str, str]:
        endpoint = args[1]
        parts = endpoint.split("/")
        repo = "/".join(parts[1:3])
        if repo not in self.files:
            return 1, "", "gh: Not Found (HTTP 404)"
        if len(parts) == 3:
            return 0, json.dumps({"full_name": repo}), ""
        path = "/".join(parts[4:]).replace("%2F", "/")
        if path not in self.files[repo]:
            return 1, "", "gh: Not Found (HTTP 404)"
        content = base64.b64encode(self.files[repo][path].encode()).decode()
        return 0, json.dumps({"content": content, "encoding": "base64"}), ""


def test_reads_through_gh_and_reports_a_missing_runner(capsys):
    gh = FakeGh(
        {
            f"{OWNER}/renovate-config": {
                "default.json": template("preset/default.json"),
                "README.md": template("preset/README.md"),
            }
        }
    )
    assert run("--json", runner=gh) == 1
    rows = json.loads(capsys.readouterr().out)
    assert [(r["path"], r["status"]) for r in rows] == [
        ("default.json", "ok"),
        ("groups-ecosystem.json", "missing"),
        ("groups-weekly.json", "missing"),
        ("README.md", "ok"),
        ("", "missing"),
    ]


def test_gh_errors_other_than_404_stop_the_audit(capsys):
    assert run(runner=lambda args: (1, "", "gh: HTTP 401: Bad credentials")) == 2
    assert "Bad credentials" in capsys.readouterr().err
