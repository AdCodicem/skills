---
name: new-skill
description: Create or substantially rework a skill inside one of this repository's plugins, following the repository conventions for naming, portability (Claude Code, claude.ai, Claude API), scripts and evals. Use when the user wants to add a skill, turn a workflow into a skill, or migrate an existing skill into this repository.
---

# New skill

Read `docs/conventions.md` once per session before writing a skill: it holds
the rules the linter enforces. This skill is the workflow.

## 1. Pin down the skill

Ask the user, unless the request already answers it:

- **What it does and when it should trigger.** Collect two or three prompts that
  should trigger it and one that should not. They become the description and the
  eval cases.
- **Which plugin** it belongs to (`.claude-plugin/marketplace.json`). If none
  fits, create one first with `/new-plugin`.
- **Which surfaces**: `claude-code` only (default), or also `claude-ai` and/or
  `api`. Portable skills must not rely on Claude Code features: no
  `${CLAUDE_*}` variables, no Claude Code-only frontmatter semantics, scripts in
  Python standard library only, no network access on the API.

## 2. Scaffold

```bash
python scripts/new_skill.py <plugin> <skill> --description "<description>" --surfaces claude-code,claude-ai
```

## 3. Write it

- **Description** (the trigger): third person, says what the skill does *and*
  when to use it, with the words users actually type. At most 1024 characters,
  no `<` or `>`. This is what decides whether the skill fires.
- **Body**: imperative steps, decisions that need the user, how to verify the
  result. Keep `SKILL.md` under 500 lines; move reference material to
  `references/*.md` and link it with relative links.
- **Scripts** go in `scripts/`, Python standard library only (Python 3.11), and
  are called with paths relative to the skill folder. Add tests for them in the
  plugin's `tests/` folder (pytest, run with `sys.executable`).
- **Templates and assets** (files the skill copies or reads, never runs) go in
  `templates/` or `assets/`. Avoid dotfiles in portable skills when you can:
  they may be dropped when the skill is synced from claude.ai.
- Claude Code-only frontmatter (`allowed-tools`, `disable-model-invocation`,
  `argument-hint`, `context`...) is fine for `claude-code` skills; the packager
  strips everything but `name` and `description` for claude.ai and the API.

## 4. Add evals (recommended)

Add at least one case that should trigger the skill and one that should not,
under `plugins/<plugin>/evals/<case>/` (see `/run-evals` and
`examples/hello-world/evals/`). Prefer `tool_used` and `regex` graders: they cost
nothing to evaluate.

## 5. Finish

1. Update the components table in the plugin's README.
2. Run `/validate` and fix everything it reports.
3. Try the skill: `claude --plugin-dir plugins/<plugin>`, then use the trigger
   prompts collected in step 1.
4. Commit as `feat(<plugin>): add <skill> skill`.
