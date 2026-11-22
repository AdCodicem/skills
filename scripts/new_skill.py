"""Scaffold a new skill inside an existing plugin from templates/skill.

Usage: python scripts/new_skill.py PLUGIN SKILL --description TEXT [--surfaces LIST]

--surfaces is a comma-separated subset of: claude-code, claude-ai, api
(default: claude-code). See docs/conventions.md before targeting claude-ai or api.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from skills_lib import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_PATTERN,
    REPO_ROOT,
    SURFACES,
    package_name,
    render_template,
)


def create_skill(
    root: Path, plugin: str, skill: str, description: str, surfaces: list[str]
) -> Path:
    plugin_dir = root / "plugins" / plugin
    if not (plugin_dir / ".claude-plugin" / "plugin.json").is_file():
        raise SystemExit(f"Plugin '{plugin}' not found under plugins/.")
    if not NAME_PATTERN.match(skill) or len(skill) > NAME_MAX_LENGTH:
        raise SystemExit(f"Invalid skill name '{skill}': use lowercase letters, digits, hyphens.")
    if not description or len(description) > DESCRIPTION_MAX_LENGTH or "<" in description:
        raise SystemExit(f"Description must be 1-{DESCRIPTION_MAX_LENGTH} chars, without '<'.")
    unknown = set(surfaces) - set(SURFACES)
    if unknown or not surfaces:
        raise SystemExit(f"Surfaces must be a subset of {', '.join(SURFACES)}.")
    portable = {"claude-ai", "api"} & set(surfaces)
    if portable and len(package_name(plugin, skill)) > NAME_MAX_LENGTH:
        raise SystemExit("The packaged name '<plugin>-<skill>' would exceed 64 characters.")

    target = plugin_dir / "skills" / skill
    if target.exists():
        raise SystemExit(f"{target.relative_to(root)} already exists.")
    render_template(
        root / "templates" / "skill",
        target,
        {
            "SKILL_NAME": skill,
            "SKILL_TITLE": skill.replace("-", " ").capitalize(),
            "SKILL_DESCRIPTION": description,
            "SKILL_SURFACES": ", ".join(s for s in SURFACES if s in surfaces),
        },
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plugin", help="existing plugin name")
    parser.add_argument("skill", help="new skill name, e.g. 'repo-init'")
    parser.add_argument("--description", required=True, help="what it does and when to use it")
    parser.add_argument("--surfaces", default="claude-code", help="comma-separated surfaces")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    surfaces = [s.strip() for s in args.surfaces.split(",") if s.strip()]
    target = create_skill(root, args.plugin, args.skill, args.description, surfaces)
    print(f"Created {target.relative_to(root).as_posix()}/SKILL.md")
    print(f"Invoke it in Claude Code as /{args.plugin}:{args.skill}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
