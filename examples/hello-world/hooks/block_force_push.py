"""PreToolUse hook: block `git push --force` to main or master.

Reads the hook event as JSON on stdin. Exit code 2 blocks the tool call and
shows stderr to Claude; exit code 0 lets it through. `--force-with-lease` is
allowed. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys

FORCE_FLAG = re.compile(r"(?:^|\s)(?:--force(?!-)|-[a-zA-Z]*f[a-zA-Z]*)(?=\s|$)")
PROTECTED = re.compile(r"(?:^|[\s:+/])(?:main|master)(?=\s|$)")


def is_blocked(command: str) -> bool:
    """True when `command` force-pushes to a protected branch."""
    for segment in re.split(r"&&|\|\||;|\|", command):
        is_push = re.search(r"\bgit\s+push\b", segment)
        if is_push and FORCE_FLAG.search(segment) and PROTECTED.search(segment):
            return True
    return False


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # Not our business: never break the session on bad input.
    command = (event.get("tool_input") or {}).get("command", "")
    if isinstance(command, str) and is_blocked(command):
        print(
            "Force pushing to main/master is blocked by the hello-world plugin. "
            "Push to a feature branch or use --force-with-lease on your own branch.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
