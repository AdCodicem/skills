# 5. Testing without paid API calls

Date: 2026-11-22

## Status

Accepted

## Context

`claude plugin eval` measures what matters most for a skill, whether it fires
and produces the right result, but every run and every LLM judge calls a model.
In CI that requires an API key and is billed. The repository owner does not want
billed calls.

## Decision

- CI runs only deterministic, free checks: `claude plugin validate --strict`,
  the conventions linter, ruff, markdownlint, pytest on Linux and Windows, and a
  packaging dry run.
- Eval suites are versioned in each plugin's `evals/` folder and run locally,
  with Claude Code logged in to a Claude subscription and `ANTHROPIC_API_KEY`
  unset, so they are covered by the subscription.
- Evals are recommended before releasing changed skills, not required.
- Graders prefer `tool_used` and `regex`, which cost nothing to evaluate.

## Consequences

- A regression in skill triggering can reach a release if evals are skipped.
- Eval runs count toward the subscription's usage limits.
