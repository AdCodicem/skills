"""Package portable skills as zip files for claude.ai and the Claude API.

A skill is portable when its `metadata.surfaces` frontmatter lists `claude-ai`
or `api`. Each one becomes `<out>/<package-name>.zip`, laid out as
`<package-name>/SKILL.md` plus its other files. Outside Claude Code skills are
not namespaced, so the package name is prefixed with the plugin name
(`dotnet` + `repo-init` -> `dotnet-repo-init`). The packaged SKILL.md keeps only
the `name` and `description` frontmatter fields, the only ones claude.ai and
the API document.

`<out>/manifest.json` lists what was built, for upload_skills.py.

Usage: python scripts/package_skills.py [--plugin NAME ...] [--out dist] [--include-examples]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

from skills_lib import (
    REPO_ROOT,
    Plugin,
    Skill,
    discover_plugins,
    iter_files,
    render_frontmatter,
    write_json,
)

#: Fixed timestamp so that packaging the same files always gives the same zip.
ZIP_DATE = (1980, 1, 1, 0, 0, 0)
EXCLUDED_DIRS = ("tests",)


def packaged_skill_md(skill: Skill) -> str:
    frontmatter = {"name": skill.package_name, "description": skill.description}
    return render_frontmatter(frontmatter, skill.body)


def _add(archive: zipfile.ZipFile, arcname: str, data: bytes, executable: bool = False) -> None:
    info = zipfile.ZipInfo(arcname, date_time=ZIP_DATE)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o755 if executable else 0o644) << 16
    archive.writestr(info, data)


def package_skill(skill: Skill, out_dir: Path) -> Path:
    """Write `<out_dir>/<package-name>.zip` and return its path."""
    pkg = skill.package_name
    target = out_dir / f"{pkg}.zip"
    with zipfile.ZipFile(target, "w") as archive:
        _add(archive, f"{pkg}/SKILL.md", packaged_skill_md(skill).encode("utf-8"))
        for file in iter_files(skill.path, exclude_dirs=EXCLUDED_DIRS):
            rel = file.relative_to(skill.path).as_posix()
            if rel == "SKILL.md":
                continue
            executable = file.suffix in {".py", ".sh"} or bool(file.stat().st_mode & 0o111)
            _add(archive, f"{pkg}/{rel}", file.read_bytes(), executable)
    return target


def select_plugins(root: Path, names: list[str], include_examples: bool) -> list[Plugin]:
    plugins = [p for p in discover_plugins(root, include_examples) if not p.error]
    if names:
        unknown = set(names) - {p.name for p in plugins}
        if unknown:
            raise SystemExit(f"Unknown plugin(s): {', '.join(sorted(unknown))}")
        plugins = [p for p in plugins if p.name in names]
    return plugins


def package(plugins: list[Plugin], out_dir: Path) -> list[dict]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    built = []
    for plugin in plugins:
        for skill in plugin.skills():
            if skill.error or not skill.portable:
                continue
            archive = package_skill(skill, out_dir)
            built.append(
                {
                    "package": skill.package_name,
                    "plugin": plugin.name,
                    "skill": skill.name,
                    "surfaces": sorted(skill.surfaces),
                    "zip": archive.name,
                }
            )
    write_json(out_dir / "manifest.json", {"skills": built})
    return built


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plugin", action="append", default=[], help="plugin to package")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "dist", help="output folder")
    parser.add_argument("--include-examples", action="store_true", help="also package examples/")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    plugins = select_plugins(args.root.resolve(), args.plugin, args.include_examples)
    built = package(plugins, args.out.resolve())
    for item in built:
        print(f"{item['zip']}  ({item['plugin']}:{item['skill']}, {', '.join(item['surfaces'])})")
    print(f"\n{len(built)} skill(s) packaged into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
