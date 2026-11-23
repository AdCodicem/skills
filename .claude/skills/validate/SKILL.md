---
name: validate
description: Run every local check of this repository (claude plugin validate, conventions linter, ruff, pytest, packaging dry run, markdownlint) and fix what fails. Use before committing, after adding or changing a plugin, skill, agent, hook or script, or when CI fails.
---

# Validate

Run the same checks as CI, in one command, from the repository root:

```bash
python scripts/check.py
```

It needs the development dependencies (`pip install -r requirements-dev.txt`).
Steps whose tool is missing (`claude`, `npx`) are reported as skipped.

## Fixing failures

- **claude plugin validate**: manifest, naming, path or frontmatter problems
  reported by Claude Code itself. Fix the file it names.
- **conventions** (`scripts/lint_skills.py`): repository rules from
  `docs/conventions.md`. Each line names the file and the rule. Warnings never
  fail the build, but read them.
- **ruff**: run `python -m ruff check --fix .` and `python -m ruff format .`,
  then fix what remains by hand.
- **pytest**: rerun a single failing test with `python -m pytest <path>::<test> -x`.
- **packaging**: usually a frontmatter problem in a portable skill.
- **markdownlint**: run `npx markdownlint-cli2 --fix "**/*.md"`, then fix the rest.

Fix the cause, never silence a rule to get green. If a rule itself looks wrong,
tell the user and propose changing the rule in its own commit.

Evals are not part of this check: they are optional and run with `/run-evals`.
