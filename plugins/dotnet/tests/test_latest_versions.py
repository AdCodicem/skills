"""Tests for skills/repo-init/scripts/latest_versions.py (no network access)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "skills" / "repo-init"
SCRIPT = SKILL / "scripts" / "latest_versions.py"
spec = importlib.util.spec_from_file_location("latest_versions", SCRIPT)
lv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lv)

INDEX = {
    "releases-index": [
        {"channel-version": "11.0", "release-type": "sts", "support-phase": "active",
         "latest-sdk": "11.0.100", "latest-runtime": "11.0.0", "eol-date": "2028-11-14"},
        {"channel-version": "10.0", "release-type": "lts", "support-phase": "active",
         "latest-sdk": "10.0.404", "latest-runtime": "10.0.15", "eol-date": "2028-11-14"},
        {"channel-version": "8.0", "release-type": "lts", "support-phase": "eol",
         "latest-sdk": "8.0.428", "latest-runtime": "8.0.34", "eol-date": "2026-11-10"},
    ]
}  # fmt: skip


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("v6.1.0", (6, 1, 0)), ("v6", (6, 0, 0)), ("2.4", (2, 4, 0)), ("v6-beta", None)],
)
def test_parse_version(tag, expected):
    assert lv.parse_version(tag) == expected


def test_latest_lts_skips_sts_and_eol():
    assert lv.latest_lts(INDEX) == {
        "channel": "10.0",
        "sdk": "10.0.404",
        "runtime": "10.0.15",
        "support_phase": "active",
        "eol_date": "2028-11-14",
    }


def test_latest_lts_fails_without_lts():
    with pytest.raises(ValueError):
        lv.latest_lts({"releases-index": []})


def test_latest_release_prefers_major_tag_pin():
    assert lv.latest_release(["v5", "v5.0.1", "v6", "v6.1.0", "v6.0.0", "latest"]) == (
        "v6.1.0",
        "v6",
    )


def test_latest_release_falls_back_to_full_version():
    assert lv.latest_release(["v2.5.0", "v2.6.0", "v2.4.4"]) == ("v2.6.0", "v2.6.0")


@pytest.mark.parametrize(
    ("ref", "latest", "expected"),
    [
        ("v7", "v7.0.1", "current"),
        ("v4", "v7.0.1", "outdated"),
        ("v2.6.0", "v2.6.0", "current"),
        ("v2.5.0", "v2.6.0", "outdated"),
        ("main", "v7.0.1", "unknown"),
        ("a" * 40, "v7.0.1", "unknown"),
    ],
)
def test_pin_status(ref, latest, expected):
    assert lv.pin_status(ref, latest) == expected


def test_find_pins_reads_subpaths_and_quotes(tmp_path):
    (tmp_path / "ci.yml").write_text(
        "steps:\n"
        "  - uses: actions/checkout@v7\n"
        "  - name: CodeQL\n"
        "    uses: github/codeql-action/init@v4\n"
        "  - uses: 'actions/checkout@v6' # comment\n"
        "  - run: echo uses: fake/action@v1\n",
        encoding="utf-8",
    )
    assert lv.find_pins([tmp_path]) == {
        "actions/checkout": {"v7", "v6"},
        "github/codeql-action": {"v4"},
    }


def test_templates_pin_every_action_with_a_version():
    pins = lv.find_pins([lv.DEFAULT_WORKFLOWS])
    assert "actions/checkout" in pins
    for repo, refs in pins.items():
        for ref in refs:
            assert lv.parse_version(ref), f"{repo}@{ref} is not pinned to a version"


def test_build_report_and_exit_codes(capsys, monkeypatch):
    tags = {"actions/checkout": ["v6", "v6.0.0", "v7", "v7.0.1"], "broken/action": []}
    report = lv.build_report(
        {"actions/checkout": {"v4", "v7"}, "broken/action": {"v1"}},
        tag_lister=lambda repo: tags[repo],
        index_fetcher=lambda url: INDEX,
    )
    assert report["dotnet"]["channel"] == "10.0"
    assert [(a["pinned"], a["status"]) for a in report["actions"]] == [
        ("v4", "outdated"),
        ("v7", "current"),
    ]
    assert report["errors"] == ["broken/action: no version tags found"]
    text = lv.format_report(report)
    assert "OUTDATED" in text and "web-search" in text


def test_main_exit_codes(monkeypatch, tmp_path, capsys):
    (tmp_path / "ci.yml").write_text("- uses: actions/checkout@v4\n", encoding="utf-8")
    original = lv.build_report

    def fake(pins, tags):
        return original(pins, tag_lister=lambda repo: tags, index_fetcher=lambda url: INDEX)

    monkeypatch.setattr(lv, "build_report", lambda pins: fake(pins, ["v7", "v7.0.1"]))
    assert lv.main(["--workflows", str(tmp_path)]) == 1
    assert lv.main(["--workflows", str(tmp_path), "--json"]) == 1
    assert '"status": "outdated"' in capsys.readouterr().out

    monkeypatch.setattr(lv, "build_report", lambda pins: fake(pins, ["v4", "v4.2.0"]))
    assert lv.main(["--workflows", str(tmp_path)]) == 0

    monkeypatch.setattr(lv, "build_report", lambda pins: fake(pins, []))
    assert lv.main(["--workflows", str(tmp_path)]) == 2
