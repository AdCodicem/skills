# Bicep

Azure infrastructure in Bicep, applied as **deployment stacks**, planned with
**what-if**, authenticated through **OIDC**. Read [choosing.md](choosing.md)
first: the user chose Bicep with the recommendation in front of them.

Templates: `templates/iac/bicep/` (`bicepconfig.json`, `main.bicep`,
`main.<environment>.bicepparam`, `ci-jobs.yml`, `deploy.yml`,
`renovate-rules.json`). `{{infra-dir}}` is `infra` in an application
repository and `.` in an operations repository ([ops-repo](ops-repo.md)).

## Layout

```text
{{infra-dir}}/
  bicepconfig.json              linter rules; the important ones are errors
  main.bicep                    the entry point, one per resource group
  main.staging.bicepparam       values per environment, never secrets
  main.production.bicepparam
  modules/                      local modules, when one file grows too large
```

- **One `.bicepparam` per environment** (`using 'main.bicep'`), the only place
  where environments differ. Secrets are never parameter values: reference Key
  Vault (`getSecret`) or let managed identities replace them.
- **Azure Verified Modules first**: `br/public:avm/res/<provider>/<type>:<x.y.z>`,
  pinned to an exact version; write a raw `resource` only when no module fits.
  AVM modules are owned and supported by Microsoft and follow SemVer, with
  breaking changes allowed in minors while they are 0.x
  ([AVM](https://azure.github.io/Azure-Verified-Modules/),
  [versioning spec](https://azure.github.io/Azure-Verified-Modules/specs/bcp/res/)).
- `targetScope = 'resourceGroup'` by default; a subscription-scope entry point
  only when the deployment creates resource groups or policies.

## Quality

- `bicepconfig.json` turns the security and hygiene rules into **errors**
  (unused parameters and variables, secrets in outputs or parameters,
  hard-coded locations and environment URLs, stable identifiers, symbolic
  references), so `az bicep build` fails on them in CI, and keeps
  `use-recent-api-versions` and `use-recent-module-versions` as warnings: they
  turn red with time, not with a change
  ([linter](https://learn.microsoft.com/azure/azure-resource-manager/bicep/linter),
  [config](https://learn.microsoft.com/azure/azure-resource-manager/bicep/bicep-config-linter)).
- `az bicep format` is the formatter; CI fails when it changes a file.
- Optional, at the complete tier: PSRule for Azure (`microsoft/ps-rule` with
  the `PSRule.Rules.Azure` module) or Checkov for Well-Architected checks; add
  it as one more job of the fragment, never as a gate the team cannot fix.

## CI (`ci-jobs.yml`)

| Job | Credentials | Does |
| --- | --- | --- |
| `bicep-lint` | none | `az bicep lint`, `build`, `build-params` of every environment, format check |
| `bicep-what-if` | the read-only **plan identity**, pull requests from this repository only | `az deployment group what-if --validation-level ProviderNoRbac` for each environment, into the job summary |

`bicep-what-if` runs on every event and skips its steps when there is no
token (fork pull requests, pushes), so the `gate` job sees a success. Its
output goes to the **job summary, never a pull request comment**: on a public
repository anyone could read the plan of production. `ProviderNoRbac` lets an
identity with read access run what-if, which otherwise needs the deployment's
own write permissions
([what-if](https://learn.microsoft.com/azure/azure-resource-manager/bicep/deploy-what-if)).

## Deployment (`deploy.yml`)

- `staging` on every push to `main` (with a `paths` filter in an application
  repository), `production-plan` (what-if of production into the summary, so
  the reviewer reads it before approving), then `production` behind the
  environment's required reviewer. Where the plan has no required reviewers,
  `production` runs only on `workflow_dispatch`; the comment in the file says
  which line to change.
- **Deployment stacks** through `azure/bicep-deploy@v2` (the action Microsoft
  recommends; it reads `.bicepparam` directly and supports stacks, what-if and
  validation): the stack records what it manages, so a resource removed from
  the code is **deleted in staging** and **detached in production**
  (`action-on-unmanage-resources`), to be deleted by hand once checked; deny
  settings `denyDelete` block deletion outside the stack
  ([deployment stacks](https://learn.microsoft.com/azure/azure-resource-manager/bicep/deployment-stacks),
  [bicep-deploy](https://github.com/Azure/bicep-deploy),
  [GitHub Actions quickstart](https://learn.microsoft.com/azure/azure-resource-manager/bicep/deploy-github-actions)).
- A stack updated on or after 2026-08-13 has a what-if baseline:
  `az stack-whatif group create` then reports drift without noise. Use it for
  drift checks once the stack exists
  ([stack what-if](https://learn.microsoft.com/azure/azure-resource-manager/bicep/deployment-stacks-what-if)).

## Identities and permissions

| Identity | Federated credential subjects | Roles, scoped to the environment's resource group |
| --- | --- | --- |
| Plan (read-only) | `repo:{{owner}}/{{repo}}:pull_request`, `repo:{{owner}}/{{repo}}:ref:refs/heads/main` | Reader, plus a custom role with `Microsoft.Resources/deployments/*` (what-if) |
| Staging | `repo:{{owner}}/{{repo}}:environment:staging` | Contributor, Azure Deployment Stack Owner (deny settings); Role Based Access Control Administrator, constrained, only if the code assigns roles |
| Production | `repo:{{owner}}/{{repo}}:environment:production` | Same as staging, on the production resource group |

Use user-assigned managed identities (or app registrations) with **federated
credentials**, never a client secret
([OIDC from GitHub](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect)).
Store `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` and
`AZURE_RESOURCE_GROUP` as **variables** of each environment, and
`AZURE_PLAN_CLIENT_ID`, `AZURE_RESOURCE_GROUP_STAGING`,
`AZURE_RESOURCE_GROUP_PRODUCTION` as repository variables.

## Dependencies

- Dependabot has no Bicep ecosystem.
- Renovate's `bicep` manager updates **resource API versions** natively
  ([Renovate bicep](https://docs.renovatebot.com/bicep/)).
- **AVM module versions** need the custom manager of `renovate-rules.json`,
  which reads the public registry's tags (MCR, through the docker datasource).
  It is best effort: the tag listing is verified
  (`https://mcr.microsoft.com/v2/bicep/avm/res/<path>/tags/list`), a full
  Renovate run is not; the `use-recent-module-versions` linter warning and
  `scripts/latest_versions.py` are the backstop.
- AVM minors may break while modules are 0.x: the rule keeps them out of
  unattended merges; patches merge on their own.

## Manual steps

1. Create the resource groups (one per environment) and the identities (plan,
   staging, production) with their federated credentials and roles above.
2. Create the GitHub environments `staging` and `production` (deployment
   branch `main`; a required reviewer on `production` where the plan allows
   it) and fill their variables. `scripts/github_settings.py` creates the
   environments.
3. First deployment: run `deploy.yml` by dispatch on `staging`, check the
   stack in the portal (Deployment stacks), then on `production`.

## Audit checklist

- `bicepconfig.json` exists and makes the security rules errors.
- Every AVM reference is pinned to an exact version; no `br/public` reference
  without a version.
- No secret in a `.bicepparam` file, no `@secure()` value with a default.
- Applies go through deployment stacks; production detaches rather than
  deletes.
- No client secret anywhere; one federated identity per environment, scoped to
  its resource group.
- The production plan never appears in a pull request comment of a public
  repository.
