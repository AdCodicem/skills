"""Shared fixtures for the repository tooling tests."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(TESTS_DIR), str(TESTS_DIR.parent / "scripts")]

from helpers import REPO_ROOT, write  # noqa: E402


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal valid repository with an empty marketplace and the real templates."""
    shutil.copytree(REPO_ROOT / "templates", tmp_path / "templates")
    write(
        tmp_path / ".claude-plugin" / "marketplace.json",
        json.dumps({"name": "test", "owner": {"name": "Test"}, "plugins": []}),
    )
    write(tmp_path / "release-please-config.json", json.dumps({"packages": {}}))
    return tmp_path
