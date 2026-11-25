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
| CodeQL default setup | standard tier: public, or private with Code Security | Static analysis on every pull request and weekly; GitHub recommends starting with the default setup |
| Immutable releases | all where available | A published release's tag and files cannot change |
| Workflow token read-only by default | all | Least privilege for every workflow that forgets to declare permissions |
| Actions pinned to a full SHA (policy) | all | A moved tag cannot change what runs |

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
