# Governance

What a visitor, a contributor and a security researcher look for first.
Templates: `templates/core/` (`LICENSE`, `README.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `CODE_OF_CONDUCT.md`) and `templates/core/dot-github/`
(`CODEOWNERS`, `pull_request_template.md`, `ISSUE_TEMPLATE/`,
`DISCUSSION_TEMPLATE/`, `FUNDING.yml`). Which ones a profile and tier get:
[profiles-and-tiers.md](../profiles-and-tiers.md).

## Every repository

- **LICENSE**: the profile's license, with the holder and year asked, never
  guessed. MIT by default for personal open source. A private repository may
  have none (all rights reserved): say so rather than adding one.
- **README.md**: see [docs](docs.md).
- **CONTRIBUTING.md**: set up, build, test, pull request titles as Conventional
  Commits and what each type releases. Filled with the ecosystems' commands.
- **SECURITY.md**: report through private vulnerability reporting (public
  repositories) or the company's channel (private ones), the response delay
  (14 days, the [OpenSSF Best Practices](https://www.bestpractices.dev/en/criteria/0)
  passing criterion), the supported versions, and how to verify a release's
  attestation.
- **CODEOWNERS**: the profile's owners, `.github/` and the workflow lockfile
  always owned. Team profiles require a code owner's approval through the
  `main-human-gates` ruleset, which Renovate's App is exempt from
  ([branching-and-commits](branching-and-commits.md)).

## Standard tier and up

- **Issue forms** (YAML, not Markdown templates: required fields, dropdowns),
  `config.yml` with blank issues off and contact links to Discussions and to
  private vulnerability reporting
  ([syntax](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)).
- **Pull request template**: what, why, how it was tested, a short checklist.
- **CODE_OF_CONDUCT.md**: [Contributor Covenant](https://www.contributor-covenant.org/)
  2.1, with the contact filled in (public profiles).
- **FUNDING.yml** and **Discussions** with a Q&A form (personal open source,
  and company open source on request). FUNDING needs GitHub Sponsors enabled;
  Discussions are turned on by `scripts/github_settings.py`.

Community health files can live once in a public `{{owner}}/.github`
repository and serve every repository of the account; LICENSE cannot
([GitHub docs](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)).
When the account has one, keep only what differs.

## Manual steps

- Enable GitHub Sponsors on the account before `FUNDING.yml` shows anything.

## Audit checklist

- LICENSE, README, CONTRIBUTING, SECURITY and CODEOWNERS exist and contain no
  placeholder.
- SECURITY points to a channel that works (private vulnerability reporting is
  on, or the company address is real).
- Issue templates are forms; blank issues are off when there are forms.
