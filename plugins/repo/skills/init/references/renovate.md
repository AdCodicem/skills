# Renovate, self-hosted, with Dependabot for actions

How the dependency bots are set up, once per account and then per repository.
The rules they follow (cooldown, groups, commit types, unattended merge) are in
[areas/dependencies.md](areas/dependencies.md).

## Why self-hosted, and why still Dependabot for actions

Evaluated on 2026-11-25:

- The Mend-hosted Renovate app is free, but it holds write access to every
  repository it is installed on, runs one job at a time and visits a
  repository about every four hours; Renovate merges one branch per base branch
  per run, so a backlog drains slowly
  ([resource tiers](https://docs.mend.io/renovate/latest/mend-renovate-cloud-resource-tiers),
  [permissions](https://docs.renovatebot.com/security-and-permissions/)).
- Self-hosting with `renovatebot/github-action` and the account's own GitHub
  App keeps write access in the account and lets the schedule be chosen
  ([action](https://github.com/renovatebot/github-action)).
- Renovate's support for GitHub's workflow lockfile is still experimental and
  had a regression fixed on 2026-10-22, while Dependabot regenerates the
  lockfile natively; with the "Require lockfile" policy on, a stale lockfile
  stops workflows from running
  ([github-actions manager](https://docs.renovatebot.com/modules/manager/github-actions/),
  [lockfiles GA](https://github.blog/changelog/2026-10-28-github-actions-workflow-lockfiles-are-generally-available)).
  Hence Dependabot keeps GitHub Actions; Renovate's `github-actions` manager is
  disabled.
- OpenSSF Scorecard recognizes `renovate.json` for its Dependency-Update-Tool
  check.

## Once per account

### 1. The shared preset: `{{owner}}/renovate-config`

A public repository (presets are read without credentials when public) holding
`default.json` from `templates/renovate/preset/default.json`:

- `config:recommended` (Dependency Dashboard, monorepo groups),
  `:semanticCommits`, `:enablePreCommit`, and `github-actions` disabled.
- `minimumReleaseAge: "3 days"` for every manager, `internalChecksFilter:
  "strict"`; vulnerability alerts on, without the age delay.
- `rebaseWhen: "behind-base-branch"`, `platformAutomerge: true`,
  `automergeType: "pr"`, `automergeStrategy: "squash"`.
- Non-major updates (minor, patch, digest, pin, lock file maintenance)
  `automerge: true` and the `automerge` label; majors not.
- `semanticCommitType: "build"`, `semanticCommitScope: "deps"`, and `fix` for
  runtime dependency types (`dependencies`, `peerDependencies`,
  `project.dependencies`).
- Weekly lock file maintenance.

Repositories reference it as `github>{{owner}}/renovate-config`. Version it
with tags when a change could surprise repositories
(`github>{{owner}}/renovate-config#v1`).

### 2. The runner: `{{owner}}/renovate`

A private repository from `templates/renovate/runner/`:

- `.github/workflows/renovate.yml`: hourly and on dispatch; mints a token from
  the Renovate App (`actions/create-github-app-token`) and runs
  `renovatebot/github-action` with a pinned `renovate-version`.
- `config.js`: `platform: "github"`, `autodiscover: true` restricted to the
  App's installations (`autodiscoverFilter: ["{{owner}}/*"]`),
  `onboarding: false`, `requireConfig: "required"` (a repository without
  `renovate.json` is left alone), `gitAuthor` set to the App's bot identity.
- The environment `renovate` holds `RENOVATE_APP_CLIENT_ID` (variable) and
  `RENOVATE_APP_PRIVATE_KEY` (secret); the workflow's job runs in it.
- Its own `renovate.json` extends the preset, whose
  `customManagers:githubActionsVersions` keeps `RENOVATE_VERSION` (and every
  `# renovate:`-annotated `*_VERSION` variable of a workflow) current; the core
  `dependabot.yml` keeps its actions current.

### 3. The Renovate GitHub App

Created by the user (Settings, Developer settings, GitHub Apps): no webhook;
repository permissions Contents, Pull requests, Issues, Workflows and Checks
read and write, Dependabot alerts and Administration read, Metadata read;
installable on this account only. Install it on every repository Renovate
should manage. Pull requests opened with the App's token trigger CI, unlike
those opened with `GITHUB_TOKEN`.

## Per repository

1. Copy `templates/renovate/renovate.json` to the repository root; fill
   `{{owner}}`.
2. Merge each module's `renovate-rules.json` `packageRules` into it (for .NET,
   the shipped packages that take `fix`).
3. Install the Renovate App on the repository.
4. Keep `templates/core/dot-github/dependabot.yml` (actions only) and turn
   Dependabot security updates off (`scripts/github_settings.py` does it).

## Audit checklist

- `renovate.json` extends the shared preset; no per-repository copy of rules
  the preset holds.
- Renovate's `github-actions` manager is off while Dependabot handles actions.
- The Dependency Dashboard issue exists and shows nothing stuck for more than
  two weeks.
- The runner pins `renovate-version` and runs at least daily.
