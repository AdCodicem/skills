# Security

The repository's own security, and what it promises to the people who use
what it ships. Supply-chain rules for workflows are in [ci](ci.md), for
releases in [release](release.md), for dependencies in
[dependencies](dependencies.md).

Baselines this follows: the [OpenSSF Scorecard checks](https://github.com/ossf/scorecard/blob/main/docs/checks.md),
[OSPS Baseline](https://baseline.openssf.org/) level 1 (the minimum OpenSSF
recommends for every project), the [OpenSSF Best Practices](https://www.bestpractices.dev/en/criteria/0)
passing criteria and [SLSA](https://slsa.dev/spec/v1.2/) build level 2
(artifact attestations).

## Settings (`scripts/github_settings.py`)

| Setting | Profiles | Why |
| --- | --- | --- |
| Private vulnerability reporting | public | A private channel for reports, linked from SECURITY.md |
| Secret scanning and push protection | public, or private with Secret Protection | Refuses a push that contains a known secret format |
| Dependabot alerts | all | Known vulnerabilities in dependencies, and Renovate's input |
| CodeQL default setup **off** | standard tier, where CodeQL runs | `codeql.yml` runs advanced setup, which default setup would refuse |
| Immutable releases | all where available | A published release's tag and files cannot change |
| Workflow token read-only by default | all | Least privilege for every workflow that forgets to declare permissions |
| Actions pinned to a full SHA (policy) | all | A moved tag cannot change what runs |

## Static analysis (standard tier and up)

The bar is enforced on people's pull requests and never blocks the bots'
dependency updates ([branching-and-commits](branching-and-commits.md)).

| Where | Tool | Enforced by |
| --- | --- | --- |
| Public repositories, or private with GitHub Code Security | **CodeQL, advanced setup**: `templates/core/dot-github/workflows/codeql.yml` on pull requests, pushes to `main` and weekly, no `paths` filter, the `actions` language plus the languages of the modules present (`csharp`, `javascript-typescript`, `python`, all with build mode `none`) | the code scanning check `CodeQL`, required by `main-human-gates`: it fails on new alerts at or above the repository's threshold (default: errors, and critical or high security alerts), compared with `main`, and honors dismissed alerts; a `neutral` result passes |
| Private repositories without Code Security | **Semgrep Community Edition**: `templates/core/ci-jobs-semgrep.yml`, a job of `ci.yml` behind `gate`, with registry rules referenced at run time (`--config p/default`, never copied: their license allows running them, not redistributing them), failing on ERROR and WARNING findings that the pull request adds (`--baseline-commit`; with ERROR alone almost no rule runs) | `gate`; needs no secret, so it runs on bot pull requests too |
| Every repository | The ecosystems' own analyzers, warnings as errors: .NET security rules (`AnalysisModeSecurity`), ruff `S` rules, typescript-eslint, `bicep lint`, PSRule or Checkov for infrastructure, zizmor for workflows | `gate` and `lint.yml` |

Why not the ruleset rule "Require code scanning results": it blocks while an
analysis runs and whenever results are missing for the head commit
([rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-code-scanning-results)),
and it blocked Dependabot pull requests in practice, despite the documented
exception for them. A required status check counts `success`, `neutral` and
`skipped` as passing
([required checks](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)).

Why not CodeQL on private code without Code Security: the CodeQL CLI's terms
allow automated analysis of open source code only
([license](https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md)),
and code scanning (SARIF upload included) needs Code Security there.

Rejected as defaults: SonarQube Cloud (free on private code only up to 50,000
lines and 5 members, and it needs a token, a Dependabot-style secret problem),
Snyk Code (100 tests a month free), GitHub Code Quality (paid on private
repositories, and its ruleset rule blocks like the code scanning one), Security
Code Scan (unmaintained since 2022).

## Files

- `SECURITY.md` ([governance](governance.md)).
- `.github/workflows/scorecards.yml` (standard tier, public): the Scorecard
  results in the Security tab and the README badge.
- `.github/VULNERABILITY_REPORT.yml` (optional, public): a form for private
  vulnerability reports, which can require a CWE and ask whether AI assisted
  the finding ([changelog](https://github.blog/changelog/2026-10-01-structured-forms-for-private-vulnerability-reports)).

## Code-Review on Scorecard

A solo maintainer cannot have changes reviewed by someone else: the
Code-Review check stays low, and the skill never auto-approves to raise it.
Teams get it from the required approval.

## Manual steps

- Register the project on [bestpractices.dev](https://www.bestpractices.dev/)
  when the profile is open source and the tier standard or above (the badge
  feeds Scorecard's CII-Best-Practices check).
- For a private repository, decide whether to buy GitHub Code Security or
  Secret Protection; never assume they are there.

## Audit checklist

- Every setting of the table is on where the profile and plan allow it.
- No secret in the history (`gitleaks detect` on a full clone, or the secret
  scanning alerts tab).
- Scorecard runs and its findings are triaged, not ignored.
- SECURITY.md's channel works.
