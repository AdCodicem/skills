# Releasing

Each plugin is versioned on its own (semver) by
[release-please](https://github.com/googleapis/release-please) in manifest mode.
There is nothing to run by hand.

## Flow

1. PRs merge into `main` with Conventional Commit titles (squash merge).
2. On every push to `main`, the Release workflow opens or updates one release PR
   per plugin with changes, for example `chore(main): release dotnet 1.1.0`. It
   bumps `version` in `plugins/<plugin>/.claude-plugin/plugin.json` and updates
   `plugins/<plugin>/CHANGELOG.md`.
3. Merging a release PR tags `<plugin>-v<version>` (for example `dotnet-v1.1.0`)
   and creates the GitHub release as a draft.
4. The `pack` job packages the plugin's portable skills into
   `<plugin>-<skill>.zip` files, for claude.ai uploads, and records their
   SHA-256 digests. It holds no credential.
5. The `publish` job runs in the `release` environment and waits for the
   maintainer's approval (**Actions** > the run > **Review deployments**).
   Once approved, it:
   - checks the digests recorded by `pack`;
   - attests the zips (signed build provenance, `actions/attest`) and attaches
     them, with the attestation bundle, to the draft;
   - publishes the release. The repository has immutable releases enabled, so
     files cannot be attached once a release is published: that is why
     release-please creates drafts (`draft` and `force-tag-creation` in
     `release-please-config.json`). If the job fails, the release stays a
     draft; fix the cause and re-run the failed job;
   - uploads skills that target `api` to the Claude API (`/v1/skills`): a new
     version when a custom skill with the same name exists, a new skill
     otherwise. Skipped when the `ANTHROPIC_API_KEY` environment secret is not
     set. Uploading runs no model and consumes no tokens.

Claude Code users get the new version when their marketplace refreshes: the
version in `plugin.json` is what Claude Code compares.

Evals are recommended before merging a release PR that changes skills, but not
required: see [testing](testing.md).

## Bumps

| Commit | 0.x plugin | 1.x+ plugin |
| --- | --- | --- |
| `fix:` | patch | patch |
| `feat:` | minor | minor |
| `feat!:` or `BREAKING CHANGE:` | minor | major |

New plugins start at 0.1.0; `dotnet` starts at 1.0.0. To force a version, add
`"release-as": "x.y.z"` to the package in `release-please-config.json`, then
remove it after the release.

## One-time GitHub setup

These settings cannot be committed:

- **General > Pull Requests**: squash merging only, with the pull request
  title as the commit; auto-merge allowed; head branches deleted after merge.
- **Rules > Rulesets**: `main` (everyone: no deletion, no force push, linear
  history, pull requests only, squash only, required checks `gate`,
  `pr-title`, `workflows`, `pre-commit`) and `main-human-gates` (the same
  checks plus `CodeQL`, with the branch up to date; the Renovate App and the
  release App are exempt).
- **Security**: private vulnerability reporting, secret scanning and push
  protection, Dependabot alerts on (Dependabot updates off: Renovate opens
  update PRs); CodeQL default setup off (`codeql.yml` is the advanced setup).
- **Actions > General**: workflow token read-only by default; actions must be
  pinned to a full-length commit SHA.

And what only the maintainer can create:

- **Release GitHub App** (once per account): permissions Contents, Pull
  requests and Issues read and write, no webhook, installed on this
  repository. Put its client ID in the `RELEASE_APP_CLIENT_ID` variable and its
  private key in the `RELEASE_APP_PRIVATE_KEY` secret of the
  `release-please` environment (deployment branch `main`, no reviewer). Its
  token makes GitHub run CI on release PRs, which `GITHUB_TOKEN` cannot.
- **`release` environment**: required reviewer the maintainer, deployment
  branch `main`, secret `ANTHROPIC_API_KEY` (optional: enables the automatic
  upload of `api` skills).
- **Immutable releases** stay enabled; the workflow publishes each release
  only after attaching its files.
