# 1. Record architecture decisions

Date: 2026-11-22

## Status

Accepted

## Context

Choices about this repository's structure, versioning, portability and testing
are hard to reverse and easy to forget. Without a record, a future change would
have to rediscover them from git history.

## Decision

Record significant, hard-to-reverse decisions as Architecture Decision Records
in `docs/adr/`, in Michael Nygard's format: one numbered Markdown file per
decision, with Status, Context, Decision and Consequences. A decision that
changes is superseded by a new record, not edited.

## Consequences

Only decisions a contributor would otherwise have to re-derive get a record.
Routine choices stay in `docs/conventions.md`.
