"""Tests for hooks/repo_skill_hint.py, fed with UserPromptSubmit events on stdin."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
HOOK = PLUGIN / "hooks" / "repo_skill_hint.py"


def run_hook(payload: object) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)], input=data, capture_output=True, text=True, encoding="utf-8"
    )


def context(result: subprocess.CompletedProcess) -> str:
    assert result.returncode == 0
    if not result.stdout.strip():
        return ""
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "UserPromptSubmit"
    return output["additionalContext"]


def event(prompt: str) -> dict:
    return {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "cwd": "/tmp"}


@pytest.mark.parametrize(
    "prompt",
    [
        "Initialise ce repo Python : pytest, ruff et une CI GitHub Actions.",
        "Set up this repo with my usual standards",
        "Add CI to this project",
        "Audit this repository against my standards",
        "Mets ce repo à niveau",
        "Configure Renovate for this repository",
        "Why does my ruleset block Dependabot pull requests?",
        "Set up the infrastructure and the deployment pipeline of this API",
        "Write the Bicep for a storage account",
        "Create a release workflow with semantic-release",
        "Ajoute une CI/CD à ce projet",
    ],
)
def test_repository_tooling_prompts_get_the_hint(prompt: str) -> None:
    assert "repo:init" in context(run_hook(event(prompt)))


@pytest.mark.parametrize(
    "prompt",
    [
        "Write a Python function that parses an ISO 8601 duration.",
        "Add a POST endpoint with validation to my API",
        "Explique-moi celle-ci et la ligne ci-dessous",
        "Add tests for this function",
        "Create a new React component for the login form",
        "What does this error mean?",
    ],
)
def test_other_prompts_get_nothing(prompt: str) -> None:
    assert context(run_hook(event(prompt))) == ""


@pytest.mark.parametrize("payload", ["not json", "[]", {"prompt": 3}, {}])
def test_unexpected_input_never_fails(payload: object) -> None:
    result = run_hook(payload)
    assert result.returncode == 0
    assert result.stdout == ""
