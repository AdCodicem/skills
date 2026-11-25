# CI

One workflow, `ci.yml`, runs every job on every pull request and on every push
to `main`, and ends with a **`gate`** job that fails unless every other job
succeeded. The ruleset on `main` requires `gate` and nothing else, so adding a
job never means editing the ruleset, and renaming one never leaves pull
requests waiting for a check that no longer reports.

Templates: `templates/core/dot-github/workflows/ci.yml` (skeleton and gate),
`templates/core/dot-github/workflows/lint.yml` (pull request title, workflows,
pre-commit), one `ci-jobs.yml` fragment per module.

## Composing `ci.yml`

1. Copy the skeleton. It triggers on `pull_request` and `push` to `main`, on
   `workflow_dispatch`, and on `workflow_call`, so `release.yml` and
   `preview.yml` run the very same jobs before publishing anything.
2. For each module present, paste the jobs of its `ci-jobs.yml` fragment under
   `jobs:`, above `gate`. Job ids are prefixed with the module (`dotnet-build`,
   `node-test`, `python-lint`, `bicep-validate`), so fragments never collide.
3. List every job id in `gate.needs`. A job that must block a merge goes into
   `needs`, never into the ruleset.
4. Run every job on every pull request: no `paths` filters. Skipping saves
   little, and a skipped job that should have run is a silent hole (the gate
   accepts only `success`).

A fragment's jobs follow these rules, which the skeleton's own jobs show:

- `permissions: contents: read` at job level (the workflow sets
  `permissions: {}`), plus exactly what the job needs (`id-token: write` for a
  tokenless Codecov upload, for example).
- `timeout-minutes` on every job, sized to twice its usual duration.
- `actions/checkout` with `persist-credentials: false`.
- The toolchain comes from the repository's pin (`global-json-file`,
  `node-version-file`, `python-version-file`), never a version written in the
  workflow.
- Caches keyed on the lock file (`cache: pnpm`, `cache: true` with uv,
  `cache: nuget` with `packages.lock.json` when it exists), in CI jobs only:
  the `pack` and `publish` jobs of `release.yml` and `preview.yml` never
  restore a cache, so a poisoned cache cannot reach a release.
- No secret: pull requests from forks run the same jobs with a read-only token.
- Coverage, when the profile and tier ask for it, goes to Codecov with
  `use_oidc: true` (no stored token) and to the job summary.

## Workflow security

Applied to every workflow the skill writes, and checked in audit mode:

- **Top-level `permissions: {}`** and per-job grants. The repository's default
  workflow token is read-only (`scripts/github_settings.py` sets it).
- **Actions pinned by full commit SHA** with the version in a comment
  (`uses: actions/checkout@<sha> # v7.0.1`). `scripts/latest_versions.py
  --write` writes these pins; the repository policy "require actions to be
  pinned to a full-length commit SHA" enforces them.
- **Workflow lockfile** `.github/workflows/actions.lock`, which also locks the
  actions that composite actions call (generally available since 2026-10-28;
  GitHub's documentation now recommends it over SHA pinning alone). The skill
  keeps both: SHA pins stay readable by Scorecard and by people, the lockfile
  covers what pins cannot. Generate it with the `gh actions-lock` extension
  (see "Lockfile" below). Dependabot updates the pin and the lockfile in the
  same pull request.
- **No `pull_request_target`**: GitHub blocks it by default in public
  repositories from 2026-12-02, and it is the root of most workflow takeovers.
  Bot pull requests are handled on `pull_request` with explicit permissions.
- **No untrusted input in `run:`**: pass `${{ github.event.* }}` values through
  `env:` and quote them.
- **`concurrency`**: one run per pull request, cancelled when a new push
  arrives; runs on `main` are never cancelled.
- `actionlint`, `zizmor` and the lockfile check run in `lint.yml` on every
  pull request (see below).

## `lint.yml`

A second workflow, kept apart because it must run on pull request title edits
(`types: [opened, edited, synchronize, reopened]`), which would otherwise rerun
every build:

| Job | Checks |
| --- | --- |
| `pr-title` | The title is a Conventional Commit with an allowed type (it becomes the squash commit) |
| `workflows` | `actionlint`, `zizmor` (configured by `.github/zizmor.yml`) and `gh actions-lock --verify` over `.github/workflows` |
| `pre-commit` | Every hook of `.pre-commit-config.yaml` over every file |

The ruleset requires `gate`, `pr-title`, `workflows` and `pre-commit`. These
four names are the contract: renaming a job means updating the ruleset.

`templates/core/dot-github/zizmor.yml` disables one audit, `self-repository`:
zizmor recommends GitHub's `$/` syntax for same-repository workflows and
actions ([changelog](https://github.blog/changelog/2026-07-30-reference-same-repository-actions-with-self-repository-syntax/)),
but actionlint 1.7.12 rejects it. When actionlint accepts it, switch
`uses: ./.github/workflows/ci.yml` to `uses: $/.github/workflows/ci.yml` and
delete the exception. Any other zizmor finding is fixed, never silenced
without a written reason in that file.

## Lockfile

Install the extension once (it needs an authenticated `gh`), then run it from
the repository root after every workflow change and commit the lockfile with
the workflows:

```bash
gh extension install github/gh-actions-lock
gh actions-lock            # onboard every workflow, or refresh after a `uses:` change
gh actions-lock --verify   # what CI runs: fails when the lockfile is stale, writes nothing
```

- Adoption is recorded in the lockfile itself (its `workflows` section), not
  in the workflow files; every action an onboarded workflow uses must have an
  entry. Never edit the file by hand.
- Reusable workflows (`jobs.<id>.uses`) are not covered by the lockfile: pin
  them by full SHA.
- `--relock` advances refs that moved (a branch, a partial tag such as `v3`);
  `--accept-moved` accepts rewritten history and is never used in automation.
- In review, a changed `commit` deserves a look, a changed `owner_id` or
  `repo_id` is a red flag. CODEOWNERS covers `.github/workflows/actions.lock`.
- The "Require lockfile" policy (repository, organization or enterprise
  policies) blocks the runs of workflows that are not onboarded. Turn it on only
  once every workflow is onboarded.

When the extension is not available (no `gh`, claude.ai), say that the
lockfile is still to generate and list it in the manual steps.

Sources: [workflow dependency lockfiles](https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles),
[lock workflow dependencies](https://docs.github.com/en/actions/how-tos/secure-your-work/lock-workflow-dependencies),
[github/gh-actions-lock](https://github.com/github/gh-actions-lock),
[secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).

## Audit checklist

- A single required check aggregates every job; no `paths` filter on required
  jobs.
- `permissions: {}` at the top of every workflow; no `write-all`.
- Every `uses:` is a full SHA with a version comment; the lockfile exists and
  is current.
- No `pull_request_target`, no `workflow_run` running pull request code.
- `persist-credentials: false` on every checkout that does not push.
- No secret used in a job that runs on pull requests from forks.
- Toolchains read from the repository's pin files.
