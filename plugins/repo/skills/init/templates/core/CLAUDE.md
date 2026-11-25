# CLAUDE.md

Guidance for Claude Code in this repository. One rule per bullet: the fact or
the instruction, then why in one clause, with exact names.

## What this is

{{One paragraph: what the project does, for whom, and what it deliberately does
not do.}}

## Commands

```bash
{{build, test, format and lint commands, exactly as CI runs them}}
```

## Rules

- Pull request titles are Conventional Commits, because the squash commit
  decides the next version (`feat` a minor, `fix` and `perf` a patch,
  `build(pack)` and `docs(readme)` a patch, the rest nothing).
- Never bump a version or edit `CHANGELOG.md` by hand: semantic-release owns
  both.
- Merging publishes nothing; a release is a dispatch of `release.yml` approved
  in the `release` environment.
- Workflows pin actions by full SHA and are locked in
  `.github/workflows/actions.lock`: after changing a `uses:`, run
  `gh actions-lock`.
- Everything is written in American English.
- {{Project rules: invariants, conventions, things not to relitigate.}}

## Layout

{{Where things live, and where the nested CLAUDE.md files are.}}

## Known traps

- {{Traps a newcomer would fall into, each with the reason.}}
