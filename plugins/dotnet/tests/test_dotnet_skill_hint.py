"""Tests for hooks/dotnet_skill_hint.py, fed with UserPromptSubmit events on stdin."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
HOOK = PLUGIN / "hooks" / "dotnet_skill_hint.py"


def run_hook(payload: object, executable: str = sys.executable) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [executable, str(HOOK)], input=data, capture_output=True, text=True, encoding="utf-8"
    )


def context(result: subprocess.CompletedProcess) -> str:
    assert result.returncode == 0
    if not result.stdout.strip():
        return ""
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "UserPromptSubmit"
    return output["additionalContext"]


def event(prompt: str, cwd: Path | str = "") -> dict:
    return {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "cwd": str(cwd)}


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        (
            "net10.0 console app: map an IAsyncEnumerable<int> with an async call. Code only.",
            {"csharp", "runtime-libraries"},
        ),
        ("Add a POST endpoint with validation to my ASP.NET Core minimal API", {"aspnetcore"}),
        ("Write an EF Core query that left joins orders", {"efcore"}),
        ("Upgrade this solution to .NET 10", {"migrate"}),
        ("Fix NU1903 in our csproj", {"tooling"}),
        ("Modernise ce code C# s'il te plaît", {"csharp"}),
    ],
)
def test_dotnet_prompts_get_matching_skills(tmp_path: Path, prompt: str, expected: set) -> None:
    text = context(run_hook(event(prompt, tmp_path)))
    assert "dotnet plugin" in text
    for skill in expected:
        assert f"- dotnet:{skill}:" in text


@pytest.mark.parametrize(
    "prompt",
    [
        "Write a Python function that parses an ISO 8601 date",
        "What is the capital of Australia?",
        "Initialize this repo for a Node.js CLI",
        "Explain the difference between C and C++",
    ],
)
def test_other_prompts_get_nothing(tmp_path: Path, prompt: str) -> None:
    assert context(run_hook(event(prompt, tmp_path))) == ""


def test_dotnet_repository_triggers_without_keywords(tmp_path: Path) -> None:
    (tmp_path / "src" / "Api").mkdir(parents=True)
    (tmp_path / "src" / "Api" / "Api.csproj").write_text("<Project />", encoding="utf-8")
    text = context(run_hook(event("Add a property to the Contact class", tmp_path)))
    assert "- dotnet:csharp:" in text


@pytest.mark.parametrize("payload", ["not json", "[]", {"prompt": 42}, {}])
def test_bad_input_never_breaks(payload: object) -> None:
    result = run_hook(payload)
    assert result.returncode == 0
    assert result.stdout == ""


def test_hooks_json_points_to_the_script() -> None:
    config = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    command = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    assert "${CLAUDE_PLUGIN_ROOT}/hooks/dotnet_skill_hint.py" in command


@pytest.mark.skipif(shutil.which("sh") is None, reason="needs a POSIX shell")
def test_hook_command_finds_a_working_python(tmp_path: Path) -> None:
    config = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    command = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
    command = command.replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN.as_posix())
    result = subprocess.run(
        ["sh", "-c", command],
        input=json.dumps(event("Write C# code for .NET 10", tmp_path)),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert "dotnet:csharp" in result.stdout
