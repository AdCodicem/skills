# Contributing

Thank you for considering a contribution. This repository follows GitHub Flow:
`main` is always releasable, work happens on short-lived branches, and every
change lands through a pull request that is squash-merged.

## Set up

Python 3.11 (the version of the Claude API code execution container, pinned in
`.python-version`) and, to validate plugins, Claude Code.

```bash
git clone https://github.com/AdCodicem/skills.git
cd skills
python -m venv .venv               # then activate it
pip install -r requirements-dev.txt
pre-commit install                 # or: prek install
```

## Build and test

```bash
python scripts/check.py            # everything CI runs
python scripts/lint_skills.py      # repository conventions only
python -m pytest -q                # tests
claude --plugin-dir plugins/<plugin>   # try a plugin without installing it
```

Read [docs/conventions.md](docs/conventions.md) before adding or changing a
plugin or a skill, and create them with `python scripts/new_plugin.py` and
`python scripts/new_skill.py` so registration stays consistent. Skill and hook
scripts use the Python standard library only.

## Pull request titles: Conventional Commits

Pull requests are squash-merged, and the title becomes the commit on `main`.
release-please computes each plugin's version and changelog from those
commits, so the title must follow
[Conventional Commits](https://www.conventionalcommits.org/), scoped with the
plugin name when the change touches one plugin:

```text
<type>(<plugin>): <description>
```

| Type | Use for | Releases the plugin |
| --- | --- | --- |
| `feat` | a new skill, agent, hook or capability | a minor version |
| `fix` | a bug fix | a patch |
| `perf` | a performance improvement | a patch |
| `docs` | documentation | a patch when it changes the plugin's files |
| `refactor`, `test`, `build`, `ci`, `chore` | everything else | nothing |

A breaking change adds `!` after the type (`feat(dotnet)!: rename the skill`)
or a `BREAKING CHANGE:` footer: a minor version while the plugin is 0.x, a
major one afterwards. CI checks every pull request title. Never edit a
`version` by hand: release-please owns it ([docs/releasing.md](docs/releasing.md)).

## Pull requests

1. Branch from `main`.
2. Keep each pull request to one logical change.
3. Add or update tests and eval cases for every behavior change.
4. Run `python scripts/check.py` before pushing; CI runs it too.
5. Fill in the pull request template.

## Code style

`.editorconfig`, ruff (configured in `pyproject.toml`) and markdownlint
(`.markdownlint-cli2.jsonc`) define the style. Everything is written in
American English.
