# Dependencies

Two bots, each where it is strongest:

| Bot | Updates | Why |
| --- | --- | --- |
| **Renovate**, self-hosted | Every package ecosystem: NuGet (central package management, `global.json`, tool manifests), npm and pnpm, Python (`pyproject.toml`, `uv.lock`), Docker, pre-commit hooks, Bicep API versions, Pulumi SDKs | One shared configuration for every repository; commit type per package (`fix` for what ships, `build` otherwise); native auto-merge; rebases branches that fall behind `main`; Dependency Dashboard |
| **Dependabot** | GitHub Actions only, plus **alerts** for everything | Regenerates the workflow lockfile (`actions.lock`) natively, which Renovate supports only experimentally; alerts feed the Security tab and Renovate's vulnerability pull requests |

Dependabot **security updates are turned off** (`scripts/github_settings.py`):
Renovate opens the vulnerability pull requests from the same alerts, at once,
ignoring its schedule and the release-age delay, and two bots would open two
pull requests for each advisory.

Revisit this split when Renovate's lockfile support leaves its experimental
stage: Renovate alone would then be simpler. The comparison behind it, with
sources, is in [renovate.md](../renovate.md).

## Rules for both bots

- **Cooldown**: a version must have been public for a few days before a pull
  request proposes it (Renovate `minimumReleaseAge: "3 days"`, Dependabot
  `cooldown.default-days: 7`, GitHub's default being 3). A compromised release
  is usually pulled within that window. Security updates skip it.
- **Small groups**: Renovate's monorepo groups (packages released together,
  such as `xunit.v3.*` or `@typescript-eslint/*`) and one pull request per
  package otherwise. A group of forty updates fails as a whole when one
  package breaks, and blocks thirty-nine good updates with it.
- **Unattended merge of non-majors**: minor, patch, digest and lock file
  maintenance updates merge on their own once `gate` is green; majors wait for
  a person, who reads the release notes.
- **Commit types decide releases**:

  | Update | Type | Releases |
  | --- | --- | --- |
  | A dependency that ships inside the package (npm `dependencies` and `peerDependencies`, Python `project.dependencies`, a NuGet package listed as shipped) | `fix(deps)` | a patch, so a security fix reaches users |
  | Anything else: dev and test dependencies, tooling, actions, the documentation site | `build(deps)` | nothing |

  A major update of a shipped dependency may be breaking for consumers: when
  merging it by hand, retitle it `fix(deps)!:` if it is.
- Bot pull requests are squash-merged under their title, like every pull
  request.

## Unattended merge, by profile

**Solo profiles** (no required approval):

- Renovate merges its own pull requests through GitHub auto-merge
  (`platformAutomerge`), as its App: the merge triggers the workflows of `main`.
- `templates/core/dot-github/workflows/dependabot-auto-merge.yml` queues
  auto-merge on Dependabot's non-major action updates, on `pull_request`
  (never `pull_request_target`), guarded by: author and actor are
  `dependabot[bot]`, the branch belongs to the repository, and
  `dependabot/fetch-metadata` classifies the update as a patch or a minor.
- Required: "Allow auto-merge" in the repository settings, and the ruleset's
  required checks, without which auto-merge would merge before CI ran.
- Not required: "Require branches to be up to date". Leave it off (`strict:
  false`): Renovate rebases its branches itself, but Dependabot rebases only on
  conflict, and a strict rule leaves its pull requests waiting forever.

**Team profiles** (one required approval):

- The same workflow also **approves** non-major pull requests of both bots
  (Renovate's carry the `automerge` label its preset adds), with
  `GITHUB_TOKEN`; this needs "Allow GitHub Actions to create and approve pull
  requests" (`scripts/github_settings.py --team` sets it).
- CODEOWNERS gives the dependency manifests and lock files no owner, so that
  approval is enough for them; workflows, the lockfile of actions and source
  keep their code owners, so a bot update touching them still waits for a
  person.

A merge made with `GITHUB_TOKEN` (Dependabot's auto-merge) does not trigger
the workflows of `main`; the next pull request, preview or release runs the
full suite before anything ships.

## Templates

- `templates/core/dot-github/dependabot.yml`: GitHub Actions only, in
  `/` and `/.github/actions/*`, weekly, cooldown, one group for minor and patch
  updates, `build` commit prefix.
- `templates/core/dot-github/workflows/dependabot-auto-merge.yml`: queue
  auto-merge (and approve, for teams).
- `templates/renovate/renovate.json`: the repository's configuration, which
  extends the account's shared preset and adds the modules' rules.
- Each module's `renovate-rules.json`: `packageRules` to merge into
  `renovate.json` (for .NET, the list of shipped packages that take `fix`).
- `templates/renovate/preset/` and `templates/renovate/runner/`: created once
  per account, see [renovate.md](../renovate.md).

## Manual steps

- Once per account: the Renovate runner repository and its GitHub App
  ([renovate.md](../renovate.md)); install the App on the new repository.
- "Allow auto-merge" and the merge settings are applied by
  `scripts/github_settings.py`.

## Audit checklist

- Exactly one bot per ecosystem; Dependabot security updates off when Renovate
  handles vulnerabilities.
- A cooldown or release age is configured.
- Non-majors merge without a person in practice: no required approval for a
  solo maintainer, or an approving workflow for a team; no strict "up to date"
  rule; "Allow auto-merge" on.
- No workflow runs on `pull_request_target`.
- Commit types follow what ships.
- Open bot pull requests older than two weeks: find what blocks them (a
  required review, a red check, a strict rule) and report it.
