# Deployment model

How every application target deploys: staging on merge, production on approval,
and how `release.yml` hands over to the deployment. The targets:
[GitHub Pages](github-pages.md), [GHCR](ghcr.md), [Azure](azure.md),
[external platforms](external.md).

An application's release is a deployment. Merging deploys **staging**; a
stable release deploys **production**, after one approval.

| Event | Workflow | Environment | Gate |
| --- | --- | --- | --- |
| Push to `main` | `staging.yml`: `ci.yml` again (the merge result), then `deploy.yml` | `staging` | none |
| Dispatch of `release.yml` | `plan`, `verify`, `pack`, then `deploy-production` (`deploy.yml`), then `publish` (semantic-release) | `production` | its required reviewer |
| Dispatch of `deploy.yml` with an older tag | `deploy.yml` | `production` (or `staging`) | its required reviewer |

Templates: `templates/deploy/staging.yml`, `templates/deploy/release-jobs.yml`
(jobs to paste into `release.yml`), and one `deploy.yml` per target under
`templates/deploy/<target>/`, copied to `.github/workflows/deploy.yml`.

How `release.yml` hands over:

1. `deploy.yml` is a reusable workflow (`workflow_call` and
   `workflow_dispatch`) with three inputs: `environment`, `ref` (the commit or
   tag to deploy) and `version` (the label stamped into the build).
2. `release-jobs.yml` adds `deploy-production` after `pack`, calling
   `deploy.yml` with `environment: production`, `ref: github.sha` and
   `version: needs.plan.outputs.next_version`; container targets add an
   `image` job first ([ghcr.md](ghcr.md)).
3. `publish` then `needs: deploy-production`: the tag, the changelog and the
   GitHub release record what production runs, and a refused or failed
   deployment leaves no tag behind. An application that ships no package has
   no `release-publish.yml` fragment.
4. The required reviewer sits on `production`, not on `release`, so a release
   asks for one approval, just before production changes. A repository that
   publishes packages **and** deploys keeps the reviewer on `release`, gives
   `production` none, and makes `deploy-production` follow `publish`.
5. Where the plan has no required reviewers (private repositories below
   Enterprise Cloud, see [github-plans.md](../github-plans.md)), the dispatch
   of `release.yml` is the approval; `production` still allows `main` only.

Rules every `deploy.yml` follows:

- `concurrency: group: deploy-<environment>`, `cancel-in-progress: false`: a
  deployment in progress is never cancelled; the next one queues. `staging.yml`
  cancels superseded runs before they deploy.
- The build job holds no credential; the deploy job builds nothing and holds
  only `id-token: write` (OIDC) and what the target needs.
- The environment's `url` is set from the deployment, and a smoke check
  (`curl --fail --retry`) fails the job when the site does not answer.
- Values that identify the target (client ID, tenant, subscription, resource
  names) are **environment variables**, not secrets; there is no secret.
- The caller job grants what the called workflow declares: `permissions` of
  `deploy-production` and of `staging.yml`'s `deploy` job list the same scopes
  as the target's deploy job (Pages adds `pages: write`).
- Rollback is a dispatch of `deploy.yml` with the previous release's tag (or,
  for containers, its commit), unless the target offers faster (a slot swap, a
  revision, a platform's instant rollback).
