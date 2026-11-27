# {{project}}-ops

Infrastructure and deployments of [{{project}}](https://github.com/{{owner}}/{{project}}).
This repository is **private**: it holds what is specific to our own instance
(subscription, resource groups, domains, environment settings). The public
repository holds no infrastructure.

## Layout

| Path | Content |
| --- | --- |
| `main.bicep`, `main.<environment>.bicepparam` (Bicep) or `Pulumi.yaml`, `Pulumi.<environment>.yaml` (Pulumi) | The infrastructure, one parameter or stack file per environment |
| `.github/workflows/ci.yml` | Lint, build and unit tests on every pull request; the plan of each environment on pull requests from this repository's branches |
| `.github/workflows/deploy.yml` | Staging on every push to `main`; production after the `production` environment's approval |
| `renovate.json` | Updates of the infrastructure's dependencies **and of the application's version** |

## How a release reaches production

1. `{{project}}` publishes a release (a container image on GHCR, or a release
   asset), through its own approved release workflow.
2. Renovate opens a pull request here that bumps the application's version
   (image tag and digest) in the parameter or stack files.
3. CI shows the plan of staging and production in the job summary.
4. Merging deploys staging; approving the `production` environment deploys
   production.

Nothing in the public repository can reach this one: no token crosses the two.

## Access

- `CODEOWNERS`: `* @{{codeowner}}`.
- Azure: OIDC federated credentials per GitHub environment, no client secret.
- Cloudflare (when used): a scoped API token per environment, as an environment
  secret.
