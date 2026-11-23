# 3. Per-plugin semantic versioning with release-please

Date: 2026-11-22

## Status

Accepted

## Context

Claude Code updates a plugin when the version it computes changes: the
`version` in `plugin.json` when set, otherwise the commit SHA. A single
repository-wide version (semantic-release, as in AdCodicem's .NET standard)
would push an update of every plugin whenever any plugin changes. Omitting the
version would update users on every commit, without a readable changelog.

## Decision

Each plugin has its own semantic version, set only in its `plugin.json`, and its
own `CHANGELOG.md`. release-please in manifest mode computes versions from
Conventional Commits (PR titles, squash-merged), opens one release PR per
plugin, tags `<plugin>-v<version>` and bumps `plugin.json` through an
`extra-files` JSON updater. `marketplace.json` entries carry no version.

## Consequences

- Users only get updates for plugins that changed.
- PR titles must be Conventional Commits, checked in CI.
- Release PRs opened with `GITHUB_TOKEN` do not trigger CI; a
  `RELEASE_PLEASE_TOKEN` secret fixes that (see docs/releasing.md).
- Every new plugin must be registered in `release-please-config.json`; the
  linter checks it and `scripts/new_plugin.py` does it.
