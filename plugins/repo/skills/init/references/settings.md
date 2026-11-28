# Repository settings

`scripts/github_settings.py` applies the settings that no file can carry. It
needs `gh`, authenticated with admin rights on the repository. Without `gh`
(claude.ai, or no admin rights), give the user the same list as manual steps,
with the path of each setting in the GitHub interface.

## Usage

```bash
python3 scripts/github_settings.py --repo OWNER/NAME --profile personal-oss \
  --tier standard --environment release --reviewer LOGIN \
  --release-app-id ID --bots-app-id ID
```

| Option | Meaning |
| --- | --- |
| `--profile` | `personal-oss`, `personal-private`, `company-private`, `company-oss`: approvals, code owners, Discussions |
| `--tier` | `minimal` leaves out the `CodeQL` check and Discussions |
| `--environment NAME` | Creates or updates an environment limited to the default branch (repeat: `release`, `preview`, `staging`, `production`); `release` and `production` get `--reviewer` as required reviewer where the plan allows it |
| `--release-app-id ID` | The release GitHub App's ID: may bypass `main` (to push the changelog commit and the tag) and is exempt from `main-human-gates` |
| `--bots-app-id ID` | The Renovate App's ID, exempt from `main-human-gates`, so its updates merge without an up-to-date branch, the `CodeQL` check or a review |
| `--admin-bypass pull-request\|none` | Lets the Admin role merge a pull request past both rulesets ("bypass rules" on the pull request), never push directly; default `pull-request` for personal profiles, `none` for company ones |
| `--check NAME` | Replaces the default required checks (`gate`, `pr-title`, `workflows`, `pre-commit`) |
| `--code-security` | The private repository has GitHub Code Security and Secret Protection |
| `--apply` | Makes the changes; without it, the script only prints the plan |
| `--json` | Prints the plan or the result as JSON |

Run it without `--apply` first, show the plan to the user, then run it again
with `--apply` once they agree. Exit codes: 0 nothing pending or everything
applied, 1 changes pending or some failed, 2 the repository cannot be read.

## What it sets

| Area | Setting | Value |
| --- | --- | --- |
| Merge | squash only; title and body from the pull request; auto-merge; delete branches after merge; update branch | on |
| Ruleset `main` | deletion, force push, linear history, pull request (squash only, threads resolved, no approval), required checks not strict; the release App may bypass; admins may bypass through a pull request on personal profiles | active on the default branch, for everyone |
| Ruleset `main-human-gates` | required checks strict (branch up to date), the `CodeQL` check where CodeQL runs, a code owner's approval for team profiles; the Renovate and release Apps exempt | active on the default branch, for people |
| Actions | default workflow token | read-only; never allowed to approve pull requests |
| Actions | actions pinned to a full SHA | required |
| Dependencies | Dependabot alerts | on |
| Dependencies | Dependabot security updates | off (Renovate opens them) |
| Security | secret scanning, push protection | on where allowed |
| Security | private vulnerability reporting | on, public repositories |
| Security | immutable releases | on where the API exposes it |
| Security | CodeQL default setup | off where CodeQL runs: `codeql.yml` runs advanced setup |
| Community | Discussions | open source profiles, standard tier |
| Environments | deployment branch `main`, required reviewers | per `--environment` and plan |

What each plan allows: [github-plans.md](github-plans.md). The script skips
what the plan forbids and says why; it never enables a paid add-on.

Not documented by GitHub, so checked on the first occasion: that the
exemption holds when Renovate merges a pull request that is behind `main`
(see [dependencies](areas/dependencies.md), manual steps).

## Manual steps it cannot do

- Create the release and Renovate GitHub Apps, and install them.
- Put the Apps' keys on the environments (`RELEASE_APP_PRIVATE_KEY` on
  `release`, `RENOVATE_APP_PRIVATE_KEY` on the runner's `renovate`).
- Register trusted publishers on nuget.org, npm and PyPI.
- Link Codecov, register on bestpractices.dev, enable Sponsors.
- Turn on the "Require lockfile" Actions policy once every workflow is
  onboarded ([ci](areas/ci.md)).
