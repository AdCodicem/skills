"""Unit tests for skills/greet/scripts/greet.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "greet" / "scripts" / "greet.py"
spec = importlib.util.spec_from_file_location("greet", SCRIPT)
greet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(greet)


@pytest.mark.parametrize(
    ("lang", "expected"),
    [("en", "Hello, Ada!"), ("fr", "Bonjour, Ada !"), ("es", "¡Hola, Ada!"), ("de", "Hallo, Ada!")],
)
def test_greet_supported_languages(lang, expected):
    assert greet.greet("Ada", lang) == expected


def test_greet_rejects_unknown_language():
    with pytest.raises(ValueError, match="Supported: de, en, es, fr"):
        greet.greet("Ada", "it")


def test_greet_blank_name_falls_back():
    assert greet.greet("  ") == "Hello, friend!"


def test_banner_frames_text():
    assert greet.banner("Hi") == "+----+\n| Hi |\n+----+"


def test_cli_prints_greeting():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--name", "Ada", "--lang", "fr"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    assert result.stdout.strip() == "Bonjour, Ada !"


def test_cli_fails_on_unknown_language():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--name", "Ada", "--lang", "it"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 1
    assert "Unsupported language" in result.stderr
