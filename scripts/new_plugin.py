"""Scaffold a new plugin from templates/plugin and register it.

Creates `plugins/<name>/`, adds the plugin to `.claude-plugin/marketplace.json`
and registers it as a release-please package starting at 0.1.0.

Usage: python scripts/new_plugin.py NAME --description TEXT [--category CAT] [--tag TAG ...]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skills_lib import NAME_PATTERN, REPO_ROOT, load_json, render_template, write_json

INITIAL_VERSION = "0.1.0"


def create_plugin(root: Path, name: str, description: str, category: str, tags: list[str]) -> Path:
    if not NAME_PATTERN.match(name):
        raise SystemExit(f"Invalid plugin name '{name}': use lowercase letters, digits, hyphens.")
    target = root / "plugins" / name
    if target.exists():
        raise SystemExit(f"{target.relative_to(root)} already exists.")

    render_template(
        root / "templates" / "plugin",
        target,
        {
            "PLUGIN_NAME": name,
            "PLUGIN_DESCRIPTION": description,
            "PLUGIN_KEYWORDS": json.dumps(tags),
        },
    )

    marketplace_path = root / ".claude-plugin" / "marketplace.json"
    marketplace = load_json(marketplace_path)
    entry = {"name": name, "source": f"./plugins/{name}", "description": description}
    if category:
        entry["category"] = category
    if tags:
        entry["tags"] = tags
    marketplace["plugins"] = sorted(
        [*marketplace.get("plugins", []), entry], key=lambda e: e["name"]
    )
    write_json(marketplace_path, marketplace)

    config_path = root / "release-please-config.json"
    config = load_json(config_path)
    packages = config.setdefault("packages", {})
    packages[f"plugins/{name}"] = {
        "component": name,
        "initial-version": INITIAL_VERSION,
        "extra-files": [
            {"type": "json", "path": ".claude-plugin/plugin.json", "jsonpath": "$.version"}
        ],
    }
    config["packages"] = dict(sorted(packages.items()))
    write_json(config_path, config)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="plugin name, e.g. 'github'")
    parser.add_argument("--description", required=True, help="one-sentence description")
    parser.add_argument("--category", default="", help="marketplace category")
    parser.add_argument("--tag", action="append", default=[], help="marketplace tag")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    target = create_plugin(root, args.name, args.description, args.category, args.tag)
    print(f"Created {target.relative_to(root).as_posix()}/ and registered it.")
    print(f"Next: python scripts/new_skill.py {args.name} <skill-name> --description '...'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
