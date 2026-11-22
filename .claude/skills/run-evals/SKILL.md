---
name: run-evals
description: Run or write the behavioral eval suites of this repository's plugins with claude plugin eval, using the user's Claude subscription so that no API billing occurs. Use when the user wants to evaluate a plugin or skill, check whether a skill triggers correctly, compare against the no-plugin baseline, or add eval cases.
---

# Run evals

Evals are **recommended, not required**: run them before releasing a plugin
whose skills changed, and whenever a skill's description changes (that is what
decides when it triggers). They never run in CI.

## Avoid API billing

`claude plugin eval` uses the same credentials as a normal Claude Code session.
To bill nothing beyond the user's subscription:

1. Check that Claude Code is logged in with the subscription (`/status` shows
   the account).
2. Make sure `ANTHROPIC_API_KEY` is **not** set in the shell: when it is set,
   Claude Code uses it and the API bills every run and every LLM judge.

   ```bash
   env -u ANTHROPIC_API_KEY claude plugin eval plugins/<plugin>
   ```

Runs still count toward the subscription's usage limits: start small.

## Run

From the repository root:

```bash
# All cases of a plugin, with the no-plugin baseline (2 arms x 3 runs per case)
env -u ANTHROPIC_API_KEY claude plugin eval plugins/<plugin>

# Cheaper while iterating: one arm, one run, a single case
env -u ANTHROPIC_API_KEY claude plugin eval plugins/<plugin> --ablation none --runs 1 --case <case>
```

Results land in `plugins/<plugin>/evals/results/<timestamp>/` (git-ignored):
`report.html` and `aggregate-result.json`. Summarize for the user: score per
case, the with/without delta, and failing graders with their reason.

## Write cases

A case is a folder `plugins/<plugin>/evals/<case>/` with a `prompt.md` (the user
message, written the way a user would type it, plus `max_turns` and
`allowed_tools` in frontmatter) and at least one grader in `graders/`. Give each
skill one case that should trigger it and one that should not. Copy from
`examples/hello-world/evals/`.

Prefer graders that cost nothing to evaluate:

- `tool_used` with `tool: Skill` and an `input_match` on the skill name, to
  check the skill fired (`min: 0`, `max: 0` and `arm: both` for "must not fire").
- `regex` over `last_message` or a produced file.

Use `llm` graders only for short outputs with concrete PASS/FAIL criteria: each
one calls a judge model. Runs only get read-only tools by default; granting
`Bash`, `Write` or `Edit` needs `--allow-tools` and a sandbox (WSL2 on Windows).

Full reference: [plugin evals](https://code.claude.com/docs/en/plugin-evals).
