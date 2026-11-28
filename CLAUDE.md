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
- **Merging a release PR publishes nothing on its own**: the `publish` job of
  `release.yml` waits for approval in the `release` environment, and no job
  that holds a credential installs or builds anything.
- **Workflows**: `permissions: {}` at the top with per-job grants, actions
  pinned by full SHA with a `# vX.Y.Z` comment, no `pull_request_target`.
  Renovate updates the pins; no workflow lockfile (gh-actions-lock rewrites
  SHA pins to tags, see ADR 6). New CI jobs go into
  `gate.needs` in `ci.yml`; the rulesets require `gate`, `pr-title`,
  `workflows` and `pre-commit`, so renaming those jobs means updating them.
- **Renovate owns dependency updates** (`renovate.json`, preset
  `AdCodicem/renovate-config`); Dependabot keeps the alerts only. Python
  stays on 3.11 (`.python-version`): skill scripts must run on the Claude API
  container.
- Files under `templates/` and `plugins/*/skills/*/templates/` are data that
  skills copy: Renovate, the pre-commit syntax hooks and the version scripts
  leave them alone, and so should repository-wide edits.

## Commands

```bash
pip install -r requirements-dev.txt
pre-commit install                            # once per clone; CI runs every hook
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
