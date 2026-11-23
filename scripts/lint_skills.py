"""Lint the marketplace, plugins and skills against the repository conventions.

`claude plugin validate` checks what Claude Code needs. This script adds the
rules from docs/conventions.md: portability to claude.ai and the Claude API,
standard-library-only Python, release-please registration, and more.

Usage: python scripts/lint_skills.py [--root PATH]
Exit code: 0 when no error was found, 1 otherwise. Warnings never fail.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from skills_lib import (
    DESCRIPTION_MAX_LENGTH,
    NAME_MAX_LENGTH,
    NAME_PATTERN,
    REPO_ROOT,
    RESERVED_NAME_WORDS,
    SURFACES,
    FrontmatterError,
    Plugin,
    Skill,
    discover_plugins,
    iter_files,
    load_json,
    parse_frontmatter,
)

SKILL_MAX_LINES = 500
API_UPLOAD_MAX_BYTES = 30 * 1024 * 1024
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
#: Runtimes that are not available on claude.ai or the Claude API.
NON_PORTABLE_SUFFIXES = {".cs", ".csx", ".js", ".mjs", ".cjs", ".ts", ".ps1", ".bat", ".cmd"}
#: Folders whose Python code is exempt from the standard-library rule.
STDLIB_EXEMPT_DIRS = ("servers", "tests")
#: Skill folders holding data files (copied or read, never executed by the skill).
DATA_DIRS = {"templates", "assets"}
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
PLUGIN_ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s\"'`\\]+)")
CLAUDE_CODE_VARIABLE = re.compile(r"\$\{CLAUDE_[A-Z_]+\}")


@dataclass(frozen=True)
class Issue:
    level: str  # "error" or "warning"
    path: Path
    message: str

    def format(self, root: Path) -> str:
        try:
            shown = self.path.relative_to(root)
        except ValueError:
            shown = self.path
        return f"{self.level.upper():7} {shown.as_posix()}: {self.message}"


class Linter:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.issues: list[Issue] = []

    def error(self, path: Path, message: str) -> None:
        self.issues.append(Issue("error", path, message))

    def warning(self, path: Path, message: str) -> None:
        self.issues.append(Issue("warning", path, message))

    # -- Marketplace ---------------------------------------------------------

    def lint_marketplace(self, plugins: list[Plugin]) -> None:
        path = self.root / ".claude-plugin" / "marketplace.json"
        if not path.is_file():
            self.error(path, "marketplace manifest not found")
            return
        marketplace = load_json(path)
        listed: dict[str, dict] = {}
        for entry in marketplace.get("plugins", []):
            name = entry.get("name", "")
            listed[name] = entry
            if "version" in entry:
                self.error(path, f"entry '{name}' sets 'version': keep it only in plugin.json")
            source = entry.get("source")
            if not isinstance(source, str) or not source.startswith("./plugins/"):
                self.error(path, f"entry '{name}' must use a './plugins/<name>' source")
                continue
            plugin_dir = (self.root / source).resolve()
            if not (plugin_dir / ".claude-plugin" / "plugin.json").is_file():
                self.error(path, f"entry '{name}' points to '{source}', which has no plugin.json")
            elif plugin_dir.name != name:
                self.error(path, f"entry '{name}' must point to './plugins/{name}'")

        for plugin in plugins:
            if plugin.path.parent.name == "plugins" and plugin.path.name not in listed:
                self.error(plugin.path, "plugin is not listed in .claude-plugin/marketplace.json")

    def lint_release_config(self, plugins: list[Plugin]) -> None:
        path = self.root / "release-please-config.json"
        if not path.is_file():
            self.error(path, "release-please config not found")
            return
        packages = load_json(path).get("packages", {})
        for plugin in plugins:
            if plugin.path.parent.name != "plugins":
                continue
            key = f"plugins/{plugin.path.name}"
            package = packages.get(key)
            if package is None:
                self.error(path, f"'{key}' is not registered as a release-please package")
                continue
            extra = package.get("extra-files", [])
            if not any(
                isinstance(item, dict)
                and item.get("path") == ".claude-plugin/plugin.json"
                and item.get("jsonpath") == "$.version"
                for item in extra
            ):
                self.error(path, f"'{key}' must bump .claude-plugin/plugin.json ($.version)")

    # -- Plugins -------------------------------------------------------------

    def lint_plugin(self, plugin: Plugin) -> None:
        if plugin.error:
            self.error(plugin.path, plugin.error)
            return
        manifest = plugin.manifest
        if manifest.get("name") != plugin.path.name:
            self.error(plugin.manifest_path, "'name' must match the plugin folder name")
        if not NAME_PATTERN.match(str(manifest.get("name", ""))):
            self.error(plugin.manifest_path, "'name' must be lowercase letters, digits and hyphens")
        if not SEMVER.match(str(manifest.get("version", ""))):
            self.error(plugin.manifest_path, "'version' must be a semantic version (x.y.z)")
        if not manifest.get("description"):
            self.error(plugin.manifest_path, "'description' is required")
        if not (plugin.path / "README.md").is_file():
            self.error(plugin.path, "README.md is required")

        for skill in plugin.skills():
            self.lint_skill(skill)
        self.lint_agents(plugin)
        self.lint_hooks(plugin)
        self.lint_python(plugin.path)

    # -- Skills --------------------------------------------------------------

    def lint_skill(self, skill: Skill) -> None:
        if skill.error:
            self.error(skill.path, skill.error)
            return
        fm, md = skill.frontmatter, skill.skill_md
        name = fm.get("name")
        if not name:
            self.error(md, "'name' is required")
        elif name != skill.dir_name:
            self.error(md, f"'name' ({name}) must match the folder name ({skill.dir_name})")
        if name and (not NAME_PATTERN.match(str(name)) or len(str(name)) > NAME_MAX_LENGTH):
            self.error(md, f"'name' must be {NAME_MAX_LENGTH} chars max: a-z, 0-9, single hyphens")

        description = skill.description
        if not description:
            self.error(md, "'description' is required")
        elif len(description) > DESCRIPTION_MAX_LENGTH:
            self.error(md, f"'description' exceeds {DESCRIPTION_MAX_LENGTH} characters")
        if re.search(r"[<>]", f"{name}{description}"):
            self.error(md, "'name' and 'description' must not contain '<' or '>'")

        unknown = skill.surfaces - set(SURFACES)
        if unknown:
            self.error(md, f"unknown surfaces {sorted(unknown)}; use {list(SURFACES)}")

        lines = skill.skill_md.read_text(encoding="utf-8").count("\n") + 1
        if lines > SKILL_MAX_LINES:
            self.error(
                md, f"{lines} lines: move details to reference files (max {SKILL_MAX_LINES})"
            )

        for target in MARKDOWN_LINK.findall(skill.body):
            if re.match(r"^[a-z][a-z0-9+.-]*:|^#", target):
                continue
            if not (skill.path / target.split("#", 1)[0]).exists():
                self.error(md, f"broken relative link '{target}'")

        if skill.portable:
            self.lint_portable_skill(skill)

    def lint_portable_skill(self, skill: Skill) -> None:
        md = skill.skill_md
        pkg = skill.package_name
        if len(pkg) > NAME_MAX_LENGTH:
            self.error(md, f"packaged name '{pkg}' exceeds {NAME_MAX_LENGTH} characters")
        for word in RESERVED_NAME_WORDS:
            if word in pkg:
                self.error(md, f"packaged name '{pkg}' contains the reserved word '{word}'")

        total = 0
        dotfiles = []
        for file in iter_files(skill.path):
            rel = file.relative_to(skill.path)
            total += file.stat().st_size
            is_data = bool(DATA_DIRS.intersection(rel.parts))
            if file.suffix.lower() in NON_PORTABLE_SUFFIXES and not is_data:
                self.error(file, "runtime not available on claude.ai or the API (use Python)")
            if any(part.startswith(".") for part in rel.parts):
                dotfiles.append(rel.as_posix())
            if file.suffix.lower() in {".md", ".py", ".sh", ".txt", ".json", ".yml", ".yaml"}:
                text = file.read_text(encoding="utf-8", errors="replace")
                if CLAUDE_CODE_VARIABLE.search(text) and not is_data:
                    self.error(file, "${CLAUDE_*} variables are only substituted by Claude Code")
        if dotfiles:
            sample = ", ".join(dotfiles[:3]) + (", ..." if len(dotfiles) > 3 else "")
            self.warning(
                skill.path,
                f"{len(dotfiles)} dotfile(s) ({sample}) may be dropped when the skill is "
                "synced from claude.ai: store them with a 'dot-' prefix",
            )
        if total > API_UPLOAD_MAX_BYTES:
            self.error(skill.path, "skill is larger than the 30 MB API upload limit")

    # -- Agents and hooks ----------------------------------------------------

    def lint_agents(self, plugin: Plugin) -> None:
        agents_dir = plugin.path / "agents"
        if not agents_dir.is_dir():
            return
        for agent in sorted(agents_dir.glob("*.md")):
            try:
                fm, _ = parse_frontmatter(agent.read_text(encoding="utf-8"))
            except FrontmatterError as exc:
                self.error(agent, str(exc))
                continue
            for key in ("name", "description"):
                if not fm.get(key):
                    self.error(agent, f"'{key}' is required")

    def lint_hooks(self, plugin: Plugin) -> None:
        path = plugin.path / "hooks" / "hooks.json"
        if not path.is_file():
            return
        try:
            data = load_json(path)
        except json.JSONDecodeError as exc:
            self.error(path, f"invalid JSON: {exc}")
            return
        if "hooks" not in data:
            self.error(path, "top-level 'hooks' key is required")
        for ref in PLUGIN_ROOT_REF.findall(path.read_text(encoding="utf-8")):
            if not (plugin.path / ref).is_file():
                self.error(path, f"referenced file '{ref}' does not exist")

    # -- Python --------------------------------------------------------------

    def lint_python(self, plugin_dir: Path) -> None:
        stdlib = set(sys.stdlib_module_names) | {"__future__"}
        for file in iter_files(plugin_dir, exclude_dirs=STDLIB_EXEMPT_DIRS):
            if file.suffix != ".py" or DATA_DIRS.intersection(file.relative_to(plugin_dir).parts):
                continue
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
            except SyntaxError as exc:
                self.error(file, f"syntax error: {exc.msg} (line {exc.lineno})")
                continue
            for module in _imported_modules(tree):
                local = file.parent / module
                if module in stdlib or local.with_suffix(".py").exists() or local.is_dir():
                    continue
                self.error(file, f"imports '{module}': skill and hook scripts are stdlib-only")

    # -- Entry point ---------------------------------------------------------

    def run(self) -> list[Issue]:
        plugins = discover_plugins(self.root)
        self.lint_marketplace(plugins)
        self.lint_release_config(plugins)
        for plugin in plugins:
            self.lint_plugin(plugin)
        return self.issues


def _imported_modules(tree: ast.AST) -> set[str]:
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def lint(root: Path = REPO_ROOT) -> list[Issue]:
    return Linter(root).run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    issues = lint(root)
    for issue in issues:
        print(issue.format(root))
    errors = sum(issue.level == "error" for issue in issues)
    warnings = len(issues) - errors
    print(f"\n{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
