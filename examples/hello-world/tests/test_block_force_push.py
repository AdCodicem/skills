"""Tests for hooks/block_force_push.py, fed with PreToolUse events on stdin."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "block_force_push.py"


def run_hook(payload: object) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOK)], input=data, capture_output=True, text=True, encoding="utf-8"
    )


def bash_event(command: str) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin main",
        "git push -f origin master",
        "git push origin main --force",
        "git fetch && git push -uf origin main",
    ],
)
def test_blocks_force_push_to_protected_branch(command):
    result = run_hook(bash_event(command))
    assert result.returncode == 2
    assert "blocked" in result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",
        "git push --force-with-lease origin main",
        "git push --force origin feature/login",
        "git push --follow-tags origin main",
        "echo main --force",
    ],
)
def test_allows_other_commands(command):
    assert run_hook(bash_event(command)).returncode == 0


def test_ignores_invalid_json():
    assert run_hook("not json").returncode == 0
