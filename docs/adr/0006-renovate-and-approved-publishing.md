# 6. Renovate for updates, SHA pins, an approved environment for publishing

Date: 2026-11-27

## Status

Accepted. Amends the consequences of ADR 3 (the release token).

## Context

The repository was brought to AdCodicem's repository standard: two layered
rulesets on `main` (`main` for everyone; `main-human-gates`, with an up-to-date
branch and the `CodeQL` check, that bot Apps are exempt from), a single `gate`
check, and releases that are attested and published only after a person
approves.

Dependabot cannot meet `main-human-gates` unattended: it does not rebase a
branch that is only behind `main`, CodeQL leaves its pull requests `neutral`,
and the auto-merge a workflow enables runs as `GITHUB_TOKEN`, which no ruleset
can exempt. Release PRs opened with `GITHUB_TOKEN` do not trigger CI, and the
optional personal access token that fixed it is a long-lived secret.

The standard's release model (semantic-release, one version for the
repository, dispatched by hand) was rejected: it would push an update of every
plugin whenever any plugin changes (ADR 3).

## Decision

- **Renovate**, self-hosted from the private `AdCodicem/renovate` runner with
  the account's GitHub App and the public `AdCodicem/renovate-config` preset,
  opens every dependency update, GitHub Actions included, and merges
  non-majors itself after a three-day release age. Dependabot keeps the alerts
  only.
- **Actions are pinned by full commit SHA** with a `# vX.Y.Z` comment, which
  Renovate updates, and the "require SHA pinning" setting is on. No workflow
  lockfile: gh-actions-lock 0.5.1 rewrites SHA pins back to tags and keys its
  lockfile by tag, so the two cannot be combined, and Renovate's lockfile
  support is experimental.
- **release-please stays** (ADR 3), with a release GitHub App token, kept in
  the `release-please` environment, instead of `RELEASE_PLEASE_TOKEN`.
- **Merging a release PR tags and drafts, and publishes nothing.** A
  credential-free `pack` job builds the zips and records their digests; the
  `publish` job runs in the `release` environment, which requires the
  maintainer's approval, checks the digests, attests the zips, attaches them to
  the draft, publishes it and uploads API skills.

## Consequences

- Renovate needs the runner repository and its App, set up by hand once per
  account; without them, no dependency update is opened.
- Each release waits for an approval click in the Actions tab.
- Released zips carry a build provenance attestation
  (`gh attestation verify`).
- Actions called inside composite actions stay unpinned, which a lockfile
  would cover. Revisit when Renovate's lockfile support is stable and
  Scorecard reads lockfiles.
- `upload_skills.py` stays standard-library only, so the credentialed job
  installs no third-party package.

## Rejected alternatives

- Dependabot with a workflow-enabled auto-merge: blocked by the human gates,
  as above.
- The Mend-hosted Renovate app: write access to every repository held by a
  third party, and one job every four hours.
- semantic-release with one repository version: see ADR 3.
- Full semver tags with the workflow lockfile and the "Require lockfile"
  policy: locks transitive actions and detects impostor commits, but drops
  the SHA-pinning setting and Scorecard's Pinned-Dependencies score, and
  depends on experimental Renovate support.
