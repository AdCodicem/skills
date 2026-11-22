"""Shared helpers for the repository tooling.

This module is used by the scripts in this folder and by the tests. It is not
shipped inside any plugin, so it may use third-party packages (PyYAML).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Surfaces a skill can declare in its `metadata.surfaces` frontmatter field.
SURFACES = ("claude-code", "claude-ai", "api")
#: Surfaces that load a skill outside of the Claude Code plugin system.
PORTABLE_SURFACES = frozenset({"claude-ai", "api"})
#: Surface assumed when a skill declares none.
DEFAULT_SURFACES = frozenset({"claude-code"})

#: Skill and plugin names: lowercase letters, digits and single hyphens.
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_MAX_LENGTH = 64
DESCRIPTION_MAX_LENGTH = 1024
#: Words the Claude API refuses in a skill name.
RESERVED_NAME_WORDS = ("anthropic", "claude")

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)


class FrontmatterError(ValueError):
    """Raised when a Markdown file has missing or invalid YAML frontmatter."""


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a Markdown document into its YAML frontmatter and its body."""
    match = _FRONTMATTER.match(text)
    if not match:
        raise FrontmatterError("missing YAML frontmatter delimited by '---' lines")
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter must be a YAML mapping")
    return data, match.group(2)


def render_frontmatter(data: dict, body: str) -> str:
    """Serialize frontmatter and body back into a Markdown document."""
    header = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=10_000)
    return f"---\n{header}---\n{body}"


def package_name(plugin_name: str, skill_name: str) -> str:
    """Name a skill takes outside Claude Code, where skills are not namespaced.

    `dotnet` + `repo-init` gives `dotnet-repo-init`. A skill whose name already
    starts with the plugin name keeps it unchanged.
    """
    if skill_name == plugin_name or skill_name.startswith(f"{plugin_name}-"):
        return skill_name
    return f"{plugin_name}-{skill_name}"


def parse_surfaces(frontmatter: dict) -> set[str]:
    """Read `metadata.surfaces` (a comma- or space-separated string, or a list)."""
    metadata = frontmatter.get("metadata") or {}
    raw = metadata.get("surfaces") if isinstance(metadata, dict) else None
    if raw is None:
        return set(DEFAULT_SURFACES)
    items = raw if isinstance(raw, list) else re.split(r"[,\s]+", str(raw))
    return {str(item).strip() for item in items if str(item).strip()}


@dataclass
class Skill:
    plugin: Plugin
    path: Path
    frontmatter: dict = field(default_factory=dict)
    body: str = ""
    error: str | None = None

    @property
    def dir_name(self) -> str:
        return self.path.name

    @property
    def skill_md(self) -> Path:
        return self.path / "SKILL.md"

    @property
    def name(self) -> str:
        return str(self.frontmatter.get("name") or self.dir_name)

    @property
    def description(self) -> str:
        return str(self.frontmatter.get("description") or "").strip()

    @property
    def surfaces(self) -> set[str]:
        return parse_surfaces(self.frontmatter)

    @property
    def portable(self) -> bool:
        return bool(self.surfaces & PORTABLE_SURFACES)

    @property
    def package_name(self) -> str:
        return package_name(self.plugin.name, self.name)


@dataclass
class Plugin:
    path: Path
    manifest: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def name(self) -> str:
        return str(self.manifest.get("name") or self.path.name)

    @property
    def manifest_path(self) -> Path:
        return self.path / ".claude-plugin" / "plugin.json"

    def skills(self) -> list[Skill]:
        skills_dir = self.path / "skills"
        if not skills_dir.is_dir():
            return []
        found = []
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            skill = Skill(plugin=self, path=skill_dir)
            if not skill.skill_md.is_file():
                skill.error = "missing SKILL.md"
            else:
                try:
                    text = skill.skill_md.read_text(encoding="utf-8")
                    skill.frontmatter, skill.body = parse_frontmatter(text)
                except FrontmatterError as exc:
                    skill.error = str(exc)
            found.append(skill)
        return found


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_plugin(path: Path) -> Plugin:
    plugin = Plugin(path=path)
    if not plugin.manifest_path.is_file():
        plugin.error = "missing .claude-plugin/plugin.json"
        return plugin
    try:
        plugin.manifest = load_json(plugin.manifest_path)
    except json.JSONDecodeError as exc:
        plugin.error = f"invalid plugin.json: {exc}"
    return plugin


def discover_plugins(root: Path = REPO_ROOT, include_examples: bool = True) -> list[Plugin]:
    """Every plugin folder under `plugins/` (and `examples/` when asked)."""
    folders = ["plugins", "examples"] if include_examples else ["plugins"]
    plugins = []
    for folder in folders:
        base = root / folder
        if base.is_dir():
            plugins.extend(load_plugin(p) for p in sorted(base.iterdir()) if p.is_dir())
    return plugins


def render_template(source: Path, target: Path, values: dict[str, str]) -> list[Path]:
    """Copy a template folder, replacing `{{KEY}}` placeholders in every file."""
    written = []
    for file in iter_files(source):
        destination = target / file.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = file.read_text(encoding="utf-8")
        for key, value in values.items():
            text = text.replace("{{" + key + "}}", value)
        destination.write_text(text, encoding="utf-8")
        written.append(destination)
    return written


def iter_files(path: Path, exclude_dirs: tuple[str, ...] = ()) -> list[Path]:
    """Files under `path`, sorted, skipping caches and the given directory names."""
    skipped = {"__pycache__", "node_modules", ".pytest_cache", ".ruff_cache", *exclude_dirs}
    return sorted(
        p
        for p in path.rglob("*")
        if p.is_file()
        and not skipped.intersection(p.relative_to(path).parts)
        and p.suffix != ".pyc"
    )
