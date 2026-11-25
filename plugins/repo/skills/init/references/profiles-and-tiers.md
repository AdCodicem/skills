# Profiles and tiers

The fixed core (SKILL.md) applies to every repository. The **profile** says who
owns the repository and who may read it; the **tier** says how much the project
needs beyond the core. Both are proposed from detection and confirmed by the
user.

## Profiles

| | Personal open source | Personal private | Company private | Company open source |
| --- | --- | --- | --- | --- |
| Suggested when | public, user-owned | private, user-owned | private or internal, organization-owned | public, organization-owned |
| License | MIT (ask for the holder) | ask; none is a valid answer (all rights reserved) | ask (often proprietary: no LICENSE, or the company's) | ask (MIT or Apache-2.0 are common) |
| Code of Conduct, FUNDING, Discussions | yes (standard tier and up) | no | no | Code of Conduct yes; FUNDING and Discussions ask |
| CODEOWNERS | `* @{{codeowner}}` | `* @{{codeowner}}` | teams per path (`@org/team`) | teams per path |
| Required approvals on `main` | 0 (solo: the gate check protects `main`) | 0 | 1, code owners | 1, code owners |
| Unattended dependency merges | auto-merge when `gate` is green | same | a workflow approves non-major bot PRs, then auto-merge | same as company private |
| Scorecard, Codecov | yes (standard tier and up) | no Scorecard (needs Advanced Security); Codecov free for 1 user | ask | yes |
| Private vulnerability reporting | yes | not available (public repositories only) | not available | yes |
| Infrastructure | private operations repository ([ops-repo](iac/ops-repo.md)) | `infra/` in the repository | `infra/` in the repository; a dedicated repository on request | private operations repository |

A company may have its own rules (signed commits, DCO or CLA, a private
registry, merge queue). Ask once whether such rules exist and follow them over
these defaults.

### Why no required approval for a solo maintainer

A maintainer cannot approve their own pull requests, and every bot pull request
would wait for a click: required approvals are what made dependency pull
requests pile up in practice (green checks, auto-merge queued, merge blocked).
For one person the protection of `main` is the ruleset itself (no direct push,
no force push, no deletion, linear history) and the `gate` check. Scorecard's
Code-Review check stays low; auto-approving with a bot to raise it would be
dishonest, so the skill does not do it for solo profiles.

For teams, approval matters. A workflow approves non-major pull requests opened
by Renovate or Dependabot (see [dependencies](areas/dependencies.md)); the
dependency manifests have no code owner, so that approval is enough, while
workflows and source keep theirs.

## Tiers

| Component | Minimal | Standard | Complete |
| --- | --- | --- | --- |
| Fixed core (hygiene, governance basics, ruleset, CI with `gate`, PR title lint, Renovate and Dependabot, release when the project publishes or deploys, security basics, `CLAUDE.md`, pre-commit) | ✓ | ✓ | ✓ |
| Issue forms, pull request template, `SUPPORT` contact links | | ✓ | ✓ |
| Code of Conduct, FUNDING, Discussions (per profile) | | ✓ | ✓ |
| CodeQL default setup (where the plan allows it) | | ✓ | ✓ |
| Scorecard workflow and badge, Codecov (public profiles) | | ✓ | ✓ |
| Stale issues and pull requests workflow | | ✓ | ✓ |
| `docs/adr/` with the first record | | ✓ | ✓ |
| Documentation site (Docusaurus, versioned, Diátaxis, generated API reference) | | | ✓ |
| `ARCHITECTURE.md`, nested `CLAUDE.md` files next to the code | | | ✓ |
| Weekly previews, published only when a package input changed | | | ✓ |
| API compatibility check against the last release | | | ✓ |
| Benchmarks (manual workflow), samples | | | ✓ |

How to recommend a tier:

- **Minimal**: a small tool, a script collection, an experiment, an internal
  service with one maintainer.
- **Standard**: anything published to a registry or deployed for others; the
  default when unsure.
- **Complete**: a library others build on, with users who need documentation,
  previews and a compatibility promise.

A tier is not a promise to stay: re-running the skill in audit mode proposes the
next tier's components as **add** items.

## Project kinds

| Kind | Release produces | Reference |
| --- | --- | --- |
| Library | Packages on a registry (NuGet, npm, PyPI) | [release](areas/release.md) and the ecosystem file |
| Application | A deployment, staging on merge, production on approval | [deploy](deploy/model.md) |
| CLI tool | Packages (`dotnet tool`, npm bin, PyPI entry point) and, optionally, binaries attached to the release | the ecosystem file |
| Infrastructure | A plan on pull requests, an apply per environment | [iac](iac/choosing.md) |

One repository may hold several kinds and ecosystems (a .NET API and a React
front end): each module adds its jobs to the same CI and the same release, and
the repository keeps **one version and one changelog**.
