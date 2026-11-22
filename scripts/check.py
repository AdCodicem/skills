"""Run every local check the CI runs, in the same order.

1. `claude plugin validate --strict` on the marketplace, each plugin and example
2. Repository conventions (lint_skills.py)
3. Ruff lint and format check
4. Pytest (tooling, skill scripts, hooks)
5. Packaging dry run
6. Markdown lint (only when `npx` is available)

Steps whose tool is missing are reported as skipped, not failed.

Usage: python scripts/check.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile

from skills_lib import REPO_ROOT, discover_plugins


def run(label: str, command: list[str]) -> bool:
    print(f"\n=== {label}\n$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=REPO_ROOT).returncode == 0


def main() -> int:
    python = sys.executable
    results: dict[str, str] = {}

    def record(label: str, ok: bool) -> None:
        results[label] = "passed" if ok else "FAILED"

    if shutil.which("claude"):
        targets = ["."] + [
            p.path.relative_to(REPO_ROOT).as_posix() for p in discover_plugins(REPO_ROOT)
        ]
        ok = all(
            run(f"claude plugin validate {t}", ["claude", "plugin", "validate", t, "--strict"])
            for t in targets
        )
        record("claude plugin validate", ok)
    else:
        results["claude plugin validate"] = "skipped (claude not found)"

    record("conventions", run("conventions", [python, "scripts/lint_skills.py"]))
    record("ruff check", run("ruff check", [python, "-m", "ruff", "check", "."]))
    record("ruff format", run("ruff format", [python, "-m", "ruff", "format", "--check", "."]))
    record("pytest", run("pytest", [python, "-m", "pytest", "-q"]))
    with tempfile.TemporaryDirectory() as out:
        command = [python, "scripts/package_skills.py", "--include-examples", "--out", out]
        record("packaging", run("packaging", command))

    if shutil.which("npx"):
        command = ["npx", "--yes", "markdownlint-cli2", "**/*.md"]
        record("markdownlint", run("markdownlint", command))
    else:
        results["markdownlint"] = "skipped (npx not found)"

    print("\n=== Summary")
    for label, outcome in results.items():
        print(f"{outcome:>28}  {label}")
    return 1 if any(outcome == "FAILED" for outcome in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
