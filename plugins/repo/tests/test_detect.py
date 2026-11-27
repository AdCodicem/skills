"""Tests for skills/init/scripts/detect.py (no network, no gh)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "init" / "scripts" / "detect.py"
spec = importlib.util.spec_from_file_location("detect", SCRIPT)
detect = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = detect
spec.loader.exec_module(detect)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def no_commands(command):
    return None


def test_mixed_repository_is_described(tmp_path):
    write(tmp_path / "App.slnx", "<Solution />")
    write(tmp_path / "src/Lib/Lib.csproj", '<Project Sdk="Microsoft.NET.Sdk"></Project>')
    write(
        tmp_path / "tests/Lib.Tests/Lib.Tests.csproj",
        "<Project><PropertyGroup><OutputType>Exe</OutputType></PropertyGroup></Project>",
    )
    write(
        tmp_path / "web/package.json",
        json.dumps(
            {"private": True, "dependencies": {"react": "^19"}, "devDependencies": {"vite": "^8"}}
        ),
    )
    write(
        tmp_path / "package.json",
        json.dumps({"private": True, "devDependencies": {"semantic-release": "^26"}}),
    )
    write(
        tmp_path / "docs/website/package.json",
        json.dumps({"dependencies": {"@docusaurus/core": "3"}}),
    )
    write(tmp_path / "infra/main.bicep", "")
    write(tmp_path / "wrangler.jsonc", "{}")
    write(tmp_path / "Dockerfile", "FROM scratch")
    write(tmp_path / "node_modules/pkg/package.json", "{}")

    result = detect.detect(tmp_path, use_github=False, runner=no_commands)

    ecosystems = result["ecosystems"]
    assert ecosystems["dotnet"]["kinds"] == ["library"]  # test projects do not count
    assert ecosystems["react"]["kinds"] == ["application"]
    assert ecosystems["node"]["kinds"] == ["tooling"]
    assert ecosystems["docs-site"]["kinds"] == ["docusaurus"]
    assert ecosystems["bicep"]["markers"] == ["infra/main.bicep"]
    assert "cloudflare" in ecosystems and "container" in ecosystems
    assert all("node_modules" not in m for e in ecosystems.values() for m in e["markers"])
    assert result["github"] == {"available": False, "reason": "--no-github"}


def test_project_kinds(tmp_path):
    write(tmp_path / "lib/package.json", json.dumps({"name": "x", "exports": "./index.js"}))
    write(tmp_path / "cli/package.json", json.dumps({"name": "y", "bin": {"y": "y.js"}}))
    write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "z"\n[project.scripts]\nz = "z:main"\n'
        '[build-system]\nrequires = ["uv_build"]\n',
    )
    write(tmp_path / "Pulumi.yaml", "name: infra\nruntime: dotnet\n")
    result = detect.detect(tmp_path, use_github=False, runner=no_commands)
    assert sorted(result["ecosystems"]["node"]["kinds"]) == ["cli", "library"]
    assert result["ecosystems"]["python"]["kinds"] == ["cli"]
    assert result["ecosystems"]["pulumi"]["runtime"] == "dotnet"


def test_standard_files_and_workflows(tmp_path):
    write(tmp_path / "LICENSE", "MIT")
    write(tmp_path / ".github/CODEOWNERS", "* @me")
    write(
        tmp_path / ".github/workflows/automerge.yml",
        "name: x\non:\n  # comment\n  pull_request_target:\n    types: [opened]\n"
        "permissions: {}\njobs:\n  a:\n    steps:\n      - uses: actions/checkout@v4\n",
    )
    write(tmp_path / ".github/workflows/ci.yml", "on: [push, pull_request]\njobs: {}\n")
    write(tmp_path / ".github/dependabot.yml", "updates:\n  - package-ecosystem: nuget\n")
    write(tmp_path / "renovate.json", "{}")
    write(tmp_path / ".releaserc.json", "{}")

    result = detect.detect(tmp_path, use_github=False, runner=no_commands)

    governance = result["files"]["governance"]
    assert governance["LICENSE"] == "LICENSE"
    assert governance["CODEOWNERS"] == ".github/CODEOWNERS"
    assert governance["README.md"] is None
    workflows = {w["file"]: w for w in result["workflows"]}
    automerge = workflows[".github/workflows/automerge.yml"]
    assert automerge["triggers"] == ["pull_request_target"]
    assert automerge["pull_request_target"] is True
    assert automerge["unpinned_actions"] == 1
    assert workflows[".github/workflows/ci.yml"]["triggers"] == ["pull_request", "push"]
    assert result["dependencies"] == {"dependabot": ["nuget"], "renovate": "renovate.json"}
    assert result["release"] == {"tools": ["semantic-release"]}


def test_github_context_and_profile_suggestion():
    responses = {
        ("gh", "api", "repos/me/lib"): json.dumps(
            {
                "visibility": "public",
                "owner": {"type": "User", "login": "me"},
                "default_branch": "main",
                "permissions": {"admin": True},
                "allow_squash_merge": True,
            }
        ),
        ("gh", "api", "user"): json.dumps({"login": "me", "plan": {"name": "pro"}}),
    }

    def runner(command):
        return responses.get(tuple(command))

    github = detect.detect_github("me/lib", runner)
    assert github["available"] is True
    assert github["plan"] == "pro"
    assert github["merge"]["allow_squash_merge"] is True
    assert detect.suggest_profile(github) == "personal-oss"
    assert detect.suggest_profile(
        {**github, "visibility": "private", "owner_type": "Organization"}
    ) == ("company-private")
    assert detect.detect_github(None, runner)["available"] is False


def test_parse_remote():
    assert detect.parse_remote("https://github.com/o/r.git") == "o/r"
    assert detect.parse_remote("git@github.com:o/r.git\n") == "o/r"
    assert detect.parse_remote("http://local_proxy@127.0.0.1:1/git/o/r") is None


def test_cli_on_an_empty_folder(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path), "--no-github"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["empty"] is True and data["ecosystems"] == {}
    missing = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp_path / "nope")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert missing.returncode == 2
