# Choosing the infrastructure tool

Infrastructure is code only when the project deploys to the cloud: GitHub
Pages, a GHCR image consumed elsewhere, or an external platform's Git
integration need none. When it does, the skill supports two tools, **Bicep**
and **Pulumi**, and **always asks the user which one**, with a recommendation
and its reason. Never pick silently.

## The recommendation

Take the first row that matches what detection and step 2 found:

| Situation | Recommend | Reason to give |
| --- | --- | --- |
| A tool is already in the repository (`*.bicep`, `Pulumi.yaml`, `*.tf`) | Keep it | A migration is a project of its own, not part of a setup |
| Azure and Cloudflare are both targets | **Pulumi** | One tool and one state for both clouds, instead of Bicep plus Wrangler |
| Conditional or reused infrastructure logic, unit tests wanted, several similar environments generated from code | **Pulumi** | Real language, loops and functions, unit tests with mocks, in the project's language |
| Azure only | **Bicep** | No state to host, new Azure APIs from day one, Azure Verified Modules, deployment stacks, supported by Microsoft |
| Operations repository without application, solo maintainer | **Bicep** | Fewest moving parts: no state storage, no language toolchain |

Show the consequences of both options in the question, so the user decides on
facts:

| | Bicep | Pulumi |
| --- | --- | --- |
| Clouds | Azure only; Cloudflare through Wrangler ([cloudflare](cloudflare.md)) | Azure and Cloudflare (and any other provider) |
| Language | Bicep DSL, `.bicepparam` per environment | The project's: C# (.NET), TypeScript (Node, React), Python; C# in an operations repository |
| State | None: Azure Resource Manager is the state; deployment stacks track what they manage | Self-managed in Azure Blob Storage, secrets encrypted with Azure Key Vault |
| Plan on pull requests | what-if | `pulumi preview` |
| Updates of dependencies | Renovate: resource API versions natively, Azure Verified Modules through a custom manager (best effort); Dependabot: none | Renovate or Dependabot through the language's packages (NuGet, npm, PyPI), like any dependency |
| Tests | `bicep lint`, `bicep build`, optional PSRule for Azure | Unit tests with mocks in the project's test framework, optional policy packs |
| Cost | Free (MIT) | Free (Apache 2.0); state storage costs cents per month; Pulumi Cloud optional (free for one user) |

Then read [bicep.md](bicep.md) or [pulumi.md](pulumi.md), and
[ops-repo.md](ops-repo.md) for where the code lives.

## Where it lives

| Profile | Infrastructure |
| --- | --- |
| Personal open source, company open source | A separate **private** operations repository `{{project}}-ops`; the public repository holds none ([ops-repo](ops-repo.md)) |
| Personal private, company private | `infra/` in the application's repository; a dedicated repository on request (several applications, a separate operations team) |

## Apply model, for both tools

- **Plan on pull requests** from the repository's own branches only: forks
  get no OIDC token, so a fork's pull request runs the credential-free checks
  (lint, build, unit tests) and nothing else. The plan identity is read-only.
- **Staging is applied on every merge to `main`** (push), from the `staging`
  environment.
- **Production waits for the `production` environment's approval**. Where the
  plan has no required reviewers on environments (private repositories below
  Enterprise Cloud, see [github-plans](../github-plans.md)), production runs
  only on a manual dispatch, restricted to `main` by the environment's
  deployment branch rule.
- **The plan of production is never posted in a pull request comment of a
  public repository**: job summary only. Comments are fine in a private
  repository, but the summary is enough.
- **No stored cloud secret**: Azure through OIDC federated credentials, one
  per GitHub environment (subject `repo:{{owner}}/{{repo}}:environment:<name>`)
  plus one for pull requests (`repo:{{owner}}/{{repo}}:pull_request`). The
  only stored secret is Cloudflare's API token, in the environments that
  deploy to Cloudflare.
- The environment holds the identifiers (`AZURE_CLIENT_ID`,
  `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`) as **variables**: they are not
  secrets, and variables keep them readable in logs.

## Terraform and OpenTofu found in a repository

Keep them; do not scaffold them. Audit against the same rules:

- providers and modules pinned, `.terraform.lock.hcl` committed, Dependabot
  (`terraform` or `opentofu` ecosystem) or Renovate updating them;
- `fmt -check`, `validate` and `test` in CI, TFLint and Trivy pinned by SHA;
- remote state with OIDC (`use_oidc` on the azurerm backend), encrypted at
  rest (OpenTofu state encryption where used);
- plan on same-repository pull requests, apply behind environments;
- note the license: Terraform is BSL 1.1, OpenTofu MPL 2.0 under the Linux
  Foundation ([OpenTofu FAQ](https://opentofu.org/faq)).

## Audit checklist

- The tool in use is the one the repository already had, or the one the user
  chose with the recommendation in front of them.
- An open-source project keeps its infrastructure out of the public
  repository.
- Every environment authenticates through OIDC; no client secret anywhere.
- Production cannot be applied without an approval or a deliberate dispatch.
