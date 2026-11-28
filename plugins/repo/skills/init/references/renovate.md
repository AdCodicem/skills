# Renovate, self-hosted, for every ecosystem

How the dependency bot is set up, once per account and then per repository.
The rules it follows (release age, groups, commit types, unattended merge,
the exemption from the human gates) are in
[areas/dependencies.md](areas/dependencies.md).

## Why self-hosted Renovate, and why not Dependabot

Evaluated on 2026-11-25 and 2026-11-26:

- The Mend-hosted Renovate app is free, but it holds write access to every
  repository it is installed on, runs one job at a time and visits a
  repository about every four hours; Renovate merges one branch per base branch
  per run, so a backlog drains slowly
  ([resource tiers](https://docs.mend.io/renovate/latest/mend-renovate-cloud-resource-tiers),
  [permissions](https://docs.renovatebot.com/security-and-permissions/)).
- Self-hosting with `renovatebot/github-action` and the account's own GitHub
  App keeps write access in the account, lets the schedule be chosen, and
  gives the bot an identity a ruleset can exempt
  ([action](https://github.com/renovatebot/github-action),
  [bypass actors](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository#granting-bypass-permissions-for-your-branch-or-tag-ruleset)).
- Dependabot cannot meet the human gates unattended: it never rebases a branch
  that is only behind (`rebase-strategy` rebases on conflict or on its own
  schedule, [options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference#rebase-strategy--)),
  CodeQL leaves its pull requests `neutral` on purpose, and the auto-merge a
  workflow enables runs as `GITHUB_TOKEN`, which cannot be exempted. Its
  alerts stay on: Renovate's `vulnerabilityAlerts` reads them.
- Renovate's support for the workflow lockfile is experimental; `lint.yml`
  refuses a stale lockfile, so the risk is a red pull request, never a broken
  `main`.
- OpenSSF Scorecard recognizes `renovate.json` for its Dependency-Update-Tool
  check.

## Once per account

### 1. The shared preset: `{{owner}}/renovate-config`

A public repository (presets are read without credentials when public) holding
`default.json` from `templates/renovate/preset/default.json`:

- `config:recommended` (Dependency Dashboard, monorepo groups),
  `:semanticCommits`, `:enablePreCommit`,
  `helpers:pinGitHubActionDigestsToSemver` and
  `customManagers:githubActionsVersions`.
- `minimumReleaseAge: "3 days"` for every manager, `internalChecksFilter:
  "strict"`; vulnerability alerts on, without the age delay.
- `automergeType: "pr"`, `platformAutomerge: false` (Renovate merges
  itself, as the exempt App), `automergeStrategy: "squash"`,
  `rebaseWhen: "conflicted"`.
- Non-major updates (minor, patch, digest, pin, lock file maintenance)
  `automerge: true`; majors not.
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
- Its own `renovate.json` extends the preset, which keeps its actions and
  `RENOVATE_VERSION` (through `customManagers:githubActionsVersions`) current.

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
4. Give the App's ID to `scripts/github_settings.py --bots-app-id`, which
   exempts it from `main-human-gates` and turns Dependabot security updates
   off (alerts stay on). Remove any `dependabot.yml`.

## Keeping the preset and runner current

The two account repositories are created once, then drift as the templates
improve. Whenever the skill touches dependencies (a new repository or an
audit), compare them with the templates:

```bash
python3 scripts/renovate_repos.py --owner {{owner}} --diff
```

It reads both repositories through `gh api` and reports each file as `ok`,
`drift`, `missing` or `unresolved` (a value it could not find: `--timezone`
when the preset has none yet, `--bot-slug` when `config.js` has no
`gitAuthor`). The comparison keeps what belongs to the account:

- `default.json`: the template's settings and package rules (matched by
  `description`) win; the account's timezone, its extra settings and its extra
  package rules stay, each right after the rule it followed, since later
  package rules win.
- `renovate.yml`: the action pins and the `# renovate:` versions are masked,
  because Renovate updates them; an update keeps the live ones.
- `config.js`: the bot identity comes from the live `gitAuthor`.

To update, show the diff to the user, then clone the repository, run the
script on the clone and review the result:

```bash
gh repo clone {{owner}}/renovate-config /tmp/renovate-config
python3 scripts/renovate_repos.py --owner {{owner}} --preset-dir /tmp/renovate-config --write
git -C /tmp/renovate-config diff
```

(`--runner-dir` likewise for the runner, then `scripts/latest_versions.py
--root <clone> --write` to pin any action the template added by tag.) Commit
with a Conventional Commit (`fix:` or `feat:`, the preset is consumed by every
repository at its next run) and push or open a pull request only once the
user agrees. A preset change that could surprise repositories goes out as a
new tag (`#v2`).

## Audit checklist

- `renovate.json` extends the shared preset; no per-repository copy of rules
  the preset holds.
- Renovate updates GitHub Actions too, and no `dependabot.yml` remains.
- The Dependency Dashboard issue exists and shows nothing stuck for more than
  two weeks.
- The runner pins `renovate-version` and runs at least daily.
- `scripts/renovate_repos.py --owner {{owner}}` reports every file `ok`.
