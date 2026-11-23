"""Print a greeting for a person in one of the supported languages.

Standard library only: this script must run on claude.ai and the Claude API.
"""

from __future__ import annotations

import argparse
import sys

GREETINGS = {
    "en": "Hello, {name}!",
    "fr": "Bonjour, {name} !",
    "es": "¡Hola, {name}!",
    "de": "Hallo, {name}!",
}


def greet(name: str, lang: str = "en") -> str:
    """Return the greeting for `name` in `lang`."""
    if lang not in GREETINGS:
        supported = ", ".join(sorted(GREETINGS))
        raise ValueError(f"Unsupported language '{lang}'. Supported: {supported}.")
    return GREETINGS[lang].format(name=name.strip() or "friend")


def banner(text: str) -> str:
    """Frame `text` in an ASCII box."""
    border = "+" + "-" * (len(text) + 2) + "+"
    return f"{border}\n| {text} |\n{border}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a greeting.")
    parser.add_argument("--name", required=True, help="person to greet")
    parser.add_argument("--lang", default="en", help="language code: en, fr, es, de")
    parser.add_argument("--banner", action="store_true", help="frame the greeting")
    args = parser.parse_args(argv)
    try:
        message = greet(args.name, args.lang)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(banner(message) if args.banner else message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
