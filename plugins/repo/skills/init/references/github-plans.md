# What each GitHub plan allows

Checked against GitHub's documentation and pricing on 2026-11-25. Plans and
prices change: when a setting fails with a plan error, trust the error, not
this table, and update it.

Public repositories get every feature below for free, on every plan.

| Feature | Public | Private, personal Free | Private, personal Pro | Private, organization Team | Private, Enterprise Cloud |
| --- | --- | --- | --- | --- | --- |
| Actions, standard runners | free, unlimited | about 2,000 min/month (a $12 pool) | about 3,000 min (an $18 pool) | about 3,000 min per organization | 50,000 min |
| Rulesets, branch protection | yes | **no** | yes | yes | yes |
| Environments, deployment branches, environment secrets | yes | **no** | yes | yes | yes |
| Environment required reviewers, wait timers | yes | no | **no** | **no** | yes |
| CodeQL, secret scanning, push protection | yes | no | no | paid add-ons: Code Security ($30) and Secret Protection ($19) per active committer per month | add-ons |
| Artifact attestations | yes | no | no | no | yes |
| Private vulnerability reporting | yes | no | no | no | no |
| GitHub Pages | yes | no | yes | yes | yes |
| Merge queue | organization-owned only | no | no | no | yes |
| Dependabot alerts and updates | yes | yes | yes | yes | yes |
| Packages and GHCR | free for public | 500 MB storage | 2 GB | 2 GB | 50 GB |

Sources: [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments),
[security plans](https://github.com/security/plans),
[attestations](https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds),
[Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages),
[merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue).

Open points: whether immutable releases are fully available on private
repositories of non-Enterprise plans (they create a release attestation);
`scripts/github_settings.py` tries and reports the answer.

## Other services

| Service | Free for | Paid beyond |
| --- | --- | --- |
| Codecov | public repositories; 1 user on private | about $5 per user per month |
| OpenSSF Scorecard action | public repositories | private needs GitHub Advanced Security |
| npm, NuGet.org, PyPI | public packages | npm private packages, PyPI corporate organizations |
| Mend-hosted Renovate | every repository (1 job at a time, every 4 hours) | not used: the skill self-hosts Renovate ([renovate](renovate.md)) |
| Netlify Free | commercial use allowed | |
| Cloudflare Pages Free | no non-commercial clause in the terms | |
| Vercel Hobby | **personal, non-commercial use only** | Pro for any company project |

## How the skill adapts

Detection (`scripts/detect.py`) reads the visibility, the owner type and, when
the token can see it, the plan. Then:

- **Private, personal Free**: no ruleset, no environments. Say that `main` can
  only be protected by upgrading to Pro or making the repository public. CI,
  Renovate, Dependabot and releases still work; the release approval is the
  dispatch itself (only people with write access can dispatch), and there is no
  attestation.
- **Private, Pro or Team**: rulesets and environments yes, but no required
  reviewers on environments: the release and production gates are a
  `workflow_dispatch` restricted to the `main` branch through the environment's
  deployment branch rule. No attestations, no CodeQL or secret scanning unless
  the add-ons are bought (ask before assuming they are).
- **Private, Enterprise Cloud**: everything, as for public repositories, except
  private vulnerability reporting.
- **Codecov on private**: free for one user; for a team, ask, or keep coverage
  in the job summary only.
- **Vercel for a company project**: say that Hobby forbids it.

Never enable a paid add-on, and never suggest changing the repository's
visibility as a fix: report the trade-off and let the user decide.
