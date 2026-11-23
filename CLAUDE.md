# CLAUDE.md

This repository is a Claude Code plugin marketplace named `adcodicem`. It holds
thematic plugins (skills, subagents, hooks, MCP servers). Some skills are also
packaged for claude.ai and the Claude API.

## Rules

- **American English only** (en-US spelling): code, comments, docs, commit
  messages, skill content. Trigger phrases in other languages inside a skill
  description are allowed.
- **Follow [docs/conventions.md](docs/conventions.md)**. `scripts/lint_skills.py`
  enforces most of it.
- **Skill and hook scripts: Python 3.11 standard library only.** Bash only for
  trivial one-liners. Repository tooling in `scripts/` may use the packages in
  `requirements-dev.txt`.
- **Never edit a plugin `version` by hand**, and never put `version` in
  `marketplace.json`: release-please bumps `plugin.json`.
- **Conventional Commits**, scoped with the plugin name when a change touches one
  plugin: `feat(dotnet): ...`, `fix(dotnet): ...`. PRs are squash-merged, so the
  PR title is the commit.
- Add a plugin with `python scripts/new_plugin.py` and a skill with
  `python scripts/new_skill.py`, so registration stays consistent.

## Commands

```bash
pip install -r requirements-dev.txt
python scripts/check.py                       # all checks, as in CI
python scripts/lint_skills.py                 # conventions only
python -m pytest -q                           # tests
python scripts/package_skills.py --out dist   # build claude.ai / API zips
claude --plugin-dir plugins/<plugin>          # load a plugin for one session
```

Authoring skills in `.claude/skills/`: `/new-plugin`, `/new-skill`, `/validate`,
`/run-evals`.

## Layout

- `plugins/<plugin>/`: published plugins, listed in `.claude-plugin/marketplace.json`
  and registered in `release-please-config.json`.
- `examples/hello-world/`: reference for every component type. Not published.
- `templates/`: scaffolding for the `new_*` scripts.
- `docs/adr/`: why the repository is shaped this way. Read before changing
  structure, versioning, portability or testing rules.
