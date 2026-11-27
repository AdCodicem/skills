"""Tests for skills/init/scripts/latest_versions.py (no network access)."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "init" / "scripts" / "latest_versions.py"
spec = importlib.util.spec_from_file_location("latest_versions", SCRIPT)
lv = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = lv  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(lv)

TODAY = dt.date(2026, 11, 25)
CHECKOUT_SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
DOTNET_INDEX = {
    "releases-index": [
        {"channel-version": "11.0", "release-type": "sts", "support-phase": "active",
         "latest-sdk": "11.0.100", "latest-runtime": "11.0.0", "eol-date": "2028-11-14"},
        {"channel-version": "10.0", "release-type": "lts", "support-phase": "active",
         "latest-sdk": "10.0.404", "latest-runtime": "10.0.15", "eol-date": "2028-11-14"},
        {"channel-version": "12.0", "release-type": "lts", "support-phase": "preview",
         "latest-sdk": "12.0.100-preview.1", "latest-runtime": "12.0.0-preview.1"},
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
NODE_SCHEDULE = {
    "v20": {"start": "2023-04-18", "lts": "2023-10-24", "end": "2026-04-30"},
    "v22": {"start": "2024-04-24", "lts": "2024-10-29", "end": "2027-04-30"},
    "v24": {"start": "2025-05-06", "lts": "2025-10-28", "end": "2028-04-30"},
    "v25": {"start": "2025-10-15", "end": "2026-06-01"},
    "v26": {"start": "2026-04-22", "lts": "2026-10-28", "end": "2029-04-30"},
}
PYTHON_CYCLE = {
    "3.16": {"status": "feature"},
    "3.15": {"status": "bugfix"},
    "3.14": {"status": "bugfix"},
    "3.13": {"status": "security"},
    "3.10": {"status": "end-of-life"},
}
REGISTRY = {
    "https://registry.npmjs.org/semantic-release/latest": {"version": "26.0.1"},
    "https://registry.npmjs.org/@semantic-release/git/latest": {"version": "11.0.3"},
    "https://registry.npmjs.org/pnpm/latest": {"version": "12.23.0"},
    "https://api.nuget.org/v3-flatcontainer/xunit.v3/index.json": {
        "versions": ["2.0.0", "3.1.0", "3.2.0", "4.0.0-pre.1"]
    },
    "https://api.nuget.org/v3-flatcontainer/docfx/index.json": {"versions": ["2.78.0", "2.81.0"]},
    "https://pypi.org/pypi/ruff/json": {"releases": {"0.16.0": [], "0.17.6": [], "1.0.0rc1": []}},
    "https://mcr.microsoft.com/v2/bicep/avm/res/storage/storage-account/tags/list": {
        "tags": ["0.9.0", "0.32.0", "0.33.2"]
    },
}
TAGS = {
    "actions/checkout": {"v6": "a" * 40, "v7": CHECKOUT_SHA, "v7.0.1": CHECKOUT_SHA},
    "actions/setup-node": {"v7.1.0": "b" * 40},
    "github/codeql-action": {"v4.31.0": "c" * 40},
    "pre-commit/pre-commit-hooks": {"v5.0.0": "d" * 40, "v6.0.0": "e" * 40},
}


def fetcher(url):
    fixed = {
        lv.DOTNET_INDEX_URL: DOTNET_INDEX,
        lv.NODE_INDEX_URL: NODE_INDEX,
        lv.NODE_SCHEDULE_URL: NODE_SCHEDULE,
        lv.PYTHON_CYCLE_URL: PYTHON_CYCLE,
        **REGISTRY,
    }
    return fixed[url]


def tags_for(repo):
    return TAGS[repo]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path):
    write(
        tmp_path / ".github/workflows/ci.yml",
        "steps:\n"
        "  - uses: actions/checkout@v6\n"
        "  - name: CodeQL\n"
        "    uses: github/codeql-action/init@v4\n"
        "  - uses: 'actions/setup-node@v7' # comment\n"
        "    with:\n"
        "      node-version: '22.x'\n"
        "  - uses: ./.github/actions/local\n"
        "  - run: echo uses: fake/action@v1\n"
        "  - with:\n"
        "      python-version: ${{ matrix.python }}\n",
    )
    write(
        tmp_path / ".github/workflows/lint.yml",
        f"steps:\n  - uses: actions/checkout@{CHECKOUT_SHA} # v7.0.1\n"
        "  - with:\n      python-version: '3.13'\n",
    )
    write(tmp_path / "global.json", json.dumps({"sdk": {"version": "10.0.100"}}))
    write(
        tmp_path / "Directory.Build.props",
        "<Project><PropertyGroup><TargetFrameworks>net8.0;net10.0</TargetFrameworks>"
        "</PropertyGroup></Project>",
    )
    write(
        tmp_path / "Directory.Packages.props",
        '<Project><ItemGroup><PackageVersion Include="xunit.v3" Version="3.1.0" />'
        "</ItemGroup></Project>",
    )
    write(
        tmp_path / ".config/dotnet-tools.json",
        json.dumps({"tools": {"docfx": {"version": "2.78.0", "commands": ["docfx"]}}}),
    )
    write(tmp_path / ".nvmrc", "24\n")
    write(tmp_path / ".python-version", "3.15\n")
    write(
        tmp_path / "package.json",
        json.dumps(
            {
                "private": True,
                "packageManager": "pnpm@10.28.0+sha512.abc",
                "devDependencies": {
                    "semantic-release": "^25.0.9",
                    "@semantic-release/git": "^11.0.1",
                    "local": "workspace:*",
                },
            },
            indent=2,
        ),
    )
    write(tmp_path / "pyproject.toml", '[dependency-groups]\ndev = ["ruff>=0.16.0"]\n')
    write(
        tmp_path / "infra/main.bicep",
        "module s 'br/public:avm/res/storage/storage-account:0.9.0' = {}\n",
    )
    write(
        tmp_path / ".pre-commit-config.yaml",
        "repos:\n  - repo: https://github.com/pre-commit/pre-commit-hooks\n    rev: v5.0.0\n"
        "    hooks:\n      - id: check-yaml\n",
    )
    write(tmp_path / "node_modules/x/package.json", json.dumps({"dependencies": {"left": "1.0.0"}}))
    return tmp_path


def by(report, kind, name=None):
    return [i for i in report.items if i.kind == kind and (name is None or i.name == name)]


def test_runtimes_come_from_the_official_indexes(repo):
    report = lv.build_report(repo, fetcher, tags_for, TODAY)
    assert report.errors == []
    assert [c["channel"] for c in report.runtimes["dotnet"]] == ["11.0", "10.0"]
    assert report.runtimes["node"] == {"lts": 26, "version": "26.13.1", "maintained": [22, 24, 26]}
    assert report.runtimes["python"] == {"latest": "3.15", "supported": ["3.13", "3.14", "3.15"]}


def test_actions_are_compared_with_their_latest_release_and_pinned_by_sha(repo):
    report = lv.build_report(repo, fetcher, tags_for, TODAY)
    checkout = by(report, "action", "actions/checkout")
    assert {(i.file, i.status) for i in checkout} == {
        (".github/workflows/ci.yml", "outdated"),  # v6 is a major behind
        (".github/workflows/lint.yml", "current"),
    }
    assert all(i.write == f"{CHECKOUT_SHA} # v7.0.1" for i in checkout)
    assert by(report, "action", "github/codeql-action/init")[0].latest == "v4.31.0"
    assert not by(report, "action", "fake/action")  # a run: line is not a uses: line


def test_runtime_pins_are_checked(repo):
    report = lv.build_report(repo, fetcher, tags_for, TODAY)
    assert by(report, ".NET SDK")[0].status == "outdated"
    frameworks = {i.name: i.status for i in by(report, "target framework")}
    assert frameworks == {"net8.0": "unsupported", "net10.0": "current"}
    assert by(report, "Node.js")[0].status == "outdated"
    assert by(report, "Python")[0].status == "current"
    node_versions = by(report, "node-version")
    assert [(i.pinned, i.status) for i in node_versions] == [("22.x", "outdated")]
    assert [(i.pinned, i.status) for i in by(report, "python-version")] == [("3.13", "outdated")]


def test_packages_modules_and_hooks_are_checked(repo):
    report = lv.build_report(repo, fetcher, tags_for, TODAY)
    npm = {i.name: (i.status, i.write) for i in by(report, "npm")}
    assert npm == {
        "semantic-release": ("outdated", None),
        "@semantic-release/git": ("outdated", "^11.0.3"),
    }
    assert by(report, "NuGet", "xunit.v3")[0].write == "3.2.0"  # stays on major 3
    assert by(report, "NuGet tool", "docfx")[0].write == "2.81.0"
    assert by(report, "PyPI", "ruff")[0].write == ">=0.17.6"
    assert by(report, "Bicep module")[0].write == "0.33.2"
    assert by(report, "pre-commit")[0].write == "v6.0.0"
    assert not [i for i in report.items if i.name == "left"]  # node_modules is skipped


def test_write_rewrites_every_pin_in_place(repo):
    report = lv.build_report(repo, fetcher, tags_for, TODAY, allow_major=True)
    changed = lv.apply_writes(repo, report)
    assert ".github/workflows/ci.yml" in changed
    ci = (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert f"uses: actions/checkout@{CHECKOUT_SHA} # v7.0.1" in ci
    assert "uses: 'actions/setup-node@" + "b" * 40 + "' # v7.1.0" in ci
    assert "uses: github/codeql-action/init@" + "c" * 40 + " # v4.31.0" in ci
    assert "node-version: '26'" in ci
    assert "uses: ./.github/actions/local" in ci
    assert json.loads((repo / "global.json").read_text())["sdk"]["version"] == "11.0.100"
    assert (repo / ".nvmrc").read_text() == "26\n"
    package = json.loads((repo / "package.json").read_text())
    assert package["devDependencies"]["semantic-release"] == "^26.0.1"
    assert package["devDependencies"]["local"] == "workspace:*"
    assert package["packageManager"] == "pnpm@12.23.0"
    assert 'Version="3.2.0"' in (repo / "Directory.Packages.props").read_text()
    assert '"version": "2.81.0"' in (repo / ".config/dotnet-tools.json").read_text()
    assert '"ruff>=0.17.6"' in (repo / "pyproject.toml").read_text()
    assert "storage-account:0.33.2" in (repo / "infra/main.bicep").read_text()
    assert "rev: v6.0.0" in (repo / ".pre-commit-config.yaml").read_text()

    again = lv.build_report(repo, fetcher, tags_for, TODAY, allow_major=True)
    outdated = [i for i in again.items if i.status in {"outdated", "unpinned"}]
    assert outdated == []


def test_failed_lookups_are_reported_not_raised(repo):
    def broken(url):
        raise OSError("offline")

    def no_tags(repo_name):
        raise OSError("offline")

    report = lv.build_report(repo, broken, no_tags, TODAY)
    assert report.runtimes == {}
    assert any("dotnet" in e for e in report.errors)
    assert by(report, "action")  # still listed, with an unknown status
    assert all(i.status == "unknown" for i in by(report, "action"))


def test_latest_tag_prefers_full_versions_and_peeled_commits():
    assert lv.latest_tag({"v7": "x" * 40, "v7.0.1": "y" * 40, "v6.9.9": "z" * 40}) == (
        "v7.0.1",
        "y" * 40,
    )
    assert lv.latest_tag({"v2": "a" * 40, "main": "b" * 40}) == ("v2", "a" * 40)
    with pytest.raises(ValueError):
        lv.latest_tag({"main": "b" * 40})


def test_cli_prints_json_and_exit_code(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    # An empty folder pins nothing; the exit code only depends on network lookups.
    assert result.returncode in {0, 2}
    assert json.loads(result.stdout)["items"] == []
