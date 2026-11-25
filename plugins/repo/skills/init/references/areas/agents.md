# Agent instructions

A `CLAUDE.md` at the root tells Claude Code (and anyone reading it) the rules
of the repository that the code does not say on its own. Template:
`templates/core/CLAUDE.md`.

## Content

- What the project is, and what it deliberately is not.
- The commands, exactly as CI runs them.
- The rules that every change needs, one per bullet: the fact or the
  instruction, then why in one clause, with exact names (files, jobs,
  settings). The template starts with the rules this standard implies:
  Conventional Commit titles, semantic-release owns versions and the
  changelog, merging publishes nothing, workflows are locked.
- Where things live, and the known traps.

Keep it short: it is loaded into every session. A rule that only concerns one
package or folder goes into a `CLAUDE.md` next to that code (complete tier),
which Claude Code loads when it reads a file under that folder
([memory docs](https://code.claude.com/docs/en/memory)). Where a document
already explains something, keep a one-line rule and point to the document.

`AGENTS.md`, read by other agents, is not created: Claude Code reads it only
when no `CLAUDE.md` exists. Add it only if the user asks, and then make
`CLAUDE.md` import it (`@AGENTS.md`) so there is one source.

## Audit checklist

- `CLAUDE.md` exists, its commands work, and it contradicts no other document.
- No rule in it that the tooling already enforces silently and no one needs to
  know.
