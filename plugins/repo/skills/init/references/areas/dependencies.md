# Dependencies

**Renovate**, self-hosted with the account's own GitHub App, updates every
ecosystem, GitHub Actions included, and merges non-major updates itself.
**Dependabot keeps the alerts only** (the Security tab, and the input from
which Renovate opens vulnerability pull requests); its version and security
updates are off. Setup of the runner and the shared preset:
[renovate.md](../renovate.md).

Why one bot: the rulesets keep two bars for people that bots cannot meet, a
branch up to date with `main` and a passing `CodeQL` check
([branching-and-commits](branching-and-commits.md)). Renovate's App is exempt
from them; Dependabot cannot be made to pass them unattended. It never rebases
a branch that is only behind `main`
([dependabot-core #2224](https://github.com/dependabot/dependabot-core/issues/2224)),
CodeQL deliberately leaves its pull requests unanalyzed (`neutral`,
[codeql-action #2858](https://github.com/github/codeql-action/issues/2858)),
and its auto-merge is enabled by `GITHUB_TOKEN`, which no ruleset can exempt.

## Rules

- **Release age**: Renovate proposes a version once it has been public for
  three days (`minimumReleaseAge: "3 days"`); a compromised release is usually
  pulled within that window. Vulnerability fixes skip it and open at once.
- **Small groups**: Renovate's monorepo groups (packages released together,
  such as `xunit.v3.*` or `@typescript-eslint/*`) and one pull request per
  package otherwise. A group of forty updates fails as a whole when one
  package breaks, and blocks thirty-nine good updates with it.
- **Unattended merge of non-majors**: minor, patch, digest, pin and lock file
  maintenance updates merge once the checks of the `main` ruleset pass; majors
  wait for a person, who reads the release notes.
- **Renovate merges itself** (`platformAutomerge: false`, `automergeType:
  "pr"`): a merge made by the App is a direct merge by an exempt actor, which
  GitHub honors; whether an exemption also covers GitHub's auto-merge is not
  documented. It merges one branch per run, and the runner runs hourly.
- **No rebasing for the sake of it** (`rebaseWhen: "conflicted"`): the App is
  exempt from the "up to date" rule, so a branch is rebased only on conflict.
- **Commit types decide releases**:

  | Update | Type | Releases |
  | --- | --- | --- |
  | A dependency that ships inside the package (npm `dependencies` and `peerDependencies`, Python `project.dependencies`, a NuGet package listed as shipped) | `fix(deps)` | a patch, so a security fix reaches users |
  | Anything else: dev and test dependencies, tooling, actions, the documentation site | `build(deps)` | nothing |

  A major update of a shipped dependency may be breaking for consumers: when
  merging it by hand, retitle it `fix(deps)!:` if it is.
- **Actions and the workflow lockfile**: Renovate updates `uses:` pinned by
  SHA with their version comment (`helpers:pinGitHubActionDigestsToSemver`
  also pins any action added by tag), and regenerates
  `.github/workflows/actions.lock`, a support still marked experimental. A
  stale lockfile fails `lint.yml`'s `gh actions-lock --verify`, so such a pull
  request stays open, red, for a person to fix with `gh actions-lock`; keep the
  "Require lockfile" Actions policy off until Renovate's support is stable.
- `*_VERSION` variables of workflows annotated `# renovate: datasource=...
  depName=...` (actionlint, Semgrep, the lockfile extension) are kept current
  by the preset's `customManagers:githubActionsVersions`.

## Templates

- `templates/renovate/renovate.json`: the repository's configuration, which
  extends the account's shared preset; each module's `renovate-rules.json`
  adds its `packageRules` (for .NET, the shipped packages that take `fix`).
- `templates/renovate/preset/` and `templates/renovate/runner/`: created once
  per account, see [renovate.md](../renovate.md).
- No `dependabot.yml`: alerts need none. An existing one is removed (or
  reduced to nothing) in audit mode, after showing the user.

## Manual steps

- Once per account: the Renovate runner repository and its GitHub App
  ([renovate.md](../renovate.md)). Install the App on the new repository, and
  give its ID to `scripts/github_settings.py --bots-app-id` so the
  `main-human-gates` ruleset exempts it.
- Check the exemption once, on the first Renovate pull request that becomes
  behind `main`: it must merge without being rebased. If it waits, the
  ruleset's bypass list is wrong.

## Audit checklist

- One bot opens update pull requests: Renovate. Dependabot alerts on, its
  version and security updates off.
- A release age is configured.
- The Renovate App is exempt from `main-human-gates` and merges non-majors
  without a person.
- No workflow runs on `pull_request_target`, none approves pull requests.
- Commit types follow what ships.
- Open update pull requests older than two weeks: find what blocks them (a red
  check, a stale lockfile, a missing exemption) and report it.
