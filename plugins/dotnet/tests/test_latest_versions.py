"""Tests for skills/repo-init/scripts/latest_versions.py (no network access)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1] / "skills" / "repo-init"
SCRIPT = SKILL / "scripts" / "latest_versions.py"
spec = importlib.util.spec_from_file_location("latest_versions", SCRIPT)
lv = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lv  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(lv)

DOTNET_INDEX = {
    "releases-index": [
        {"channel-version": "11.0", "release-type": "sts", "support-phase": "active",
         "latest-sdk": "11.0.100", "latest-runtime": "11.0.0", "eol-date": "2028-11-14"},
        {"channel-version": "10.0", "release-type": "lts", "support-phase": "active",
         "latest-sdk": "10.0.404", "latest-runtime": "10.0.15", "eol-date": "2028-11-14"},
        {"channel-version": "8.0", "release-type": "lts", "support-phase": "eol",
         "latest-sdk": "8.0.428", "latest-runtime": "8.0.34", "eol-date": "2026-11-10"},
    ]
}  # fmt: skip
NODE_INDEX = [
    {"version": "v27.0.0", "lts": False},
    {"version": "v26.13.1", "lts": "Lithium"},
    {"version": "v24.22.3", "lts": "Krypton"},
    {"version": "v22.23.5", "lts": "Jod"},
]


def fetcher(url):
    return {lv.DOTNET_INDEX_URL: DOTNET_INDEX, lv.NODE_INDEX_URL: NODE_INDEX}[url]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    write(
        tmp_path / ".github/workflows/ci.yml",
        "steps:\n"
        "  - uses: actions/checkout@v4\n"
        "  - name: CodeQL\n"
        "    uses: github/codeql-action/init@v4\n"
        "  - uses: 'actions/setup-node@v7' # comment\n"
        "    with:\n"
        "      node-version: '22.x'\n"
        "  - run: echo uses: fake/action@v1\n",
    )
    write(tmp_path / "global.json", json.dumps({"sdk": {"version": "10.0.100"}}))
    write(
        tmp_path / "src/Lib/Lib.csproj",
        "<Project><PropertyGroup>"
        "<TargetFrameworks>netstandard2.0;net8.0;net9.0</TargetFrameworks>"
        "</PropertyGroup></Project>",
    )
    write(tmp_path / "src/Lib/obj/Ignored.csproj", "<TargetFramework>net6.0</TargetFramework>")
    return tmp_path


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("v6.1.0", (6, 1, 0)), ("v6", (6, 0, 0)), ("2.4", (2, 4, 0)), ("v6-beta", None)],
)
def test_parse_version(tag, expected):
    assert lv.parse_version(tag) == expected


def test_scan_collects_every_kind_of_pin(repo):
    pins = lv.scan(repo)
    assert pins.actions == {
        "actions/checkout": {"v4"},
        "github/codeql-action": {"v4"},
        "actions/setup-node": {"v7"},
    }
    assert pins.node == [(".github/workflows/ci.yml", "22.x")]
    assert pins.sdk == [("global.json", "10.0.100")]
    assert pins.frameworks == [("src/Lib/Lib.csproj", "net9.0")]


def test_latest_dotnet_lts_skips_sts_and_eol():
    assert lv.latest_dotnet_lts(DOTNET_INDEX) == {
        "channel": "10.0",
        "sdk": "10.0.404",
        "runtime": "10.0.15",
        "support_phase": "active",
        "eol_date": "2028-11-14",
    }


def test_latest_node_lts_is_newest_lts_line():
    assert lv.latest_node_lts(NODE_INDEX) == {
        "major": 26,
        "version": "v26.13.1",
        "codename": "Lithium",
    }


@pytest.mark.parametrize("parse", ["latest_dotnet_lts", "latest_node_lts"])
def test_lts_lookups_fail_without_lts(parse):
    empty = {"releases-index": []} if parse == "latest_dotnet_lts" else []
    with pytest.raises(ValueError):
        getattr(lv, parse)(empty)


def test_latest_release_prefers_major_tag_pin():
    tags = ["v5", "v5.0.1", "v6", "v6.1.0", "v6.0.0", "latest"]
    assert lv.latest_release(tags) == ("v6.1.0", "v6")


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [("26", "current"), ("26.x", "current"), ("27", "current"), ("22", "outdated"),
     (">=24", "outdated"), ("lts/*", "current"), ("node", "unknown")],
)  # fmt: skip
def test_node_status(value, expected):
    assert lv.node_status(value, 26) == expected


def test_sdk_and_framework_status():
    assert lv.sdk_status("10.0.404", "10.0.404") == "current"
    assert lv.sdk_status("10.0.100", "10.0.404") == "outdated"
    assert lv.framework_status("net10.0", "10.0") == "current"
    assert lv.framework_status("net11.0", "10.0") == "current"
    assert lv.framework_status("net8.0-windows", "10.0") == "outdated"


def test_templates_are_fully_pinned():
    pins = lv.scan(lv.DEFAULT_ROOT)
    assert "actions/checkout" in pins.actions
    for repo, refs in pins.actions.items():
        for ref in refs:
            assert lv.parse_version(ref), f"{repo}@{ref} is not pinned to a version"
    assert pins.sdk and pins.frameworks and pins.node


def test_build_report(repo):
    tags = {
        "actions/checkout": ["v6", "v6.0.0", "v7", "v7.0.1"],
        "github/codeql-action": ["v4", "v4.39.4"],
        "actions/setup-node": [],
    }
    report = lv.build_report(lv.scan(repo), tag_lister=lambda r: tags[r], fetcher=fetcher)
    assert report["dotnet"]["channel"] == "10.0"
    assert report["node"]["major"] == 26
    assert [(r["runtime"], r["pinned"], r["latest"], r["status"]) for r in report["runtimes"]] == [
        (".NET SDK", "10.0.100", "10.0.404", "outdated"),
        ("Target framework", "net9.0", "net10.0", "outdated"),
        ("Node.js", "22.x", "26", "outdated"),
    ]
    assert [(a["action"], a["status"]) for a in report["actions"]] == [
        ("actions/checkout", "outdated"),
        ("github/codeql-action", "current"),
    ]
    assert report["errors"] == ["actions/setup-node: no version tags found"]
    text = lv.format_report(report)
    assert "Node.js LTS: 26" in text and "OUTDATED" in text and "web-search" in text


def test_build_report_survives_index_failures(repo):
    def broken(url):
        raise OSError("offline")

    report = lv.build_report(lv.scan(repo), tag_lister=lambda r: ["v7"], fetcher=broken)
    assert report["dotnet"] is None and report["node"] is None
    assert report["runtimes"] == []
    assert len(report["errors"]) == 2


def test_main_exit_codes(monkeypatch, tmp_path, capsys):
    write(tmp_path / ".github/workflows/ci.yml", "- uses: actions/checkout@v4\n")
    original = lv.build_report

    def fake(tags):
        return lambda pins: original(pins, tag_lister=lambda r: tags, fetcher=fetcher)

    monkeypatch.setattr(lv, "build_report", fake(["v7", "v7.0.1"]))
    assert lv.main(["--root", str(tmp_path)]) == 1
    assert lv.main(["--root", str(tmp_path), "--json"]) == 1
    assert '"status": "outdated"' in capsys.readouterr().out

    monkeypatch.setattr(lv, "build_report", fake(["v4", "v4.2.0"]))
    assert lv.main(["--root", str(tmp_path)]) == 0

    monkeypatch.setattr(lv, "build_report", fake([]))
    assert lv.main(["--root", str(tmp_path)]) == 2
