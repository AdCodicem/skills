# Pulumi

Infrastructure in the project's own language, for Azure and Cloudflare in one
program, with the state in Azure Blob Storage and its secrets encrypted by
Azure Key Vault. Read [choosing.md](choosing.md) first: the user chose Pulumi
with the recommendation in front of them.

Templates: `templates/iac/pulumi/` (`ci-jobs.yml`, `deploy.yml`,
`toolchains/<language>.yml`, `dot-pulumi.version`, `renovate-rules.json`,
`tests/`). `{{infra-dir}}` is `infra` in an application repository and `.` in
an operations repository ([ops-repo](ops-repo.md)).

## Language and generator

| Project | Language | Generator (latest CLI) | Unit tests |
| --- | --- | --- | --- |
| .NET | C# | `pulumi new azure-csharp` | xUnit, `Deployment.TestAsync` with `IMocks` (`tests/StackTests.cs`) |
| Node, React | TypeScript | `pulumi new azure-typescript` | Vitest, `pulumi.runtime.setMocks` (`tests/index.spec.ts`) |
| Python | Python | `pulumi new azure-python` | pytest, `pulumi.runtime.set_mocks` (`tests/stack_tests.py`, copied as `tests/test_stack.py`) |
| Operations repository without application | C# | `pulumi new azure-csharp` | as .NET |

- Run the generator with `--generate-only` (no stack, no login), then apply
  the ecosystem module's configuration to the program like any other project
  of that language (analyzers, strict TypeScript, ruff).
- Use the **Azure Native** provider (`Pulumi.AzureNative`,
  `@pulumi/azure-native`, `pulumi-azure-native`) and, when Cloudflare is a
  target, the **Cloudflare** provider (`Pulumi.Cloudflare`,
  `@pulumi/cloudflare`, `pulumi-cloudflare`).
- Pin the CLI in `{{infra-dir}}/.pulumi.version` (from `dot-pulumi.version`,
  the latest release from `scripts/latest_versions.py`); `pulumi/actions`
  reads it, and Renovate bumps it.
- Unit tests run on every pull request without credentials: mocks replace the
  engine, so they check the program's logic (tags, names, conditions, loops),
  not the cloud. Policy packs (`pulumi preview --policy-pack`) are optional.

## State and secrets

- **Backend**: self-managed Azure Blob Storage,
  `azblob://<container>?storage_account=<account>`, stored in the repository
  variable `PULUMI_BACKEND_URL`. Without a key or SAS token, the backend
  authenticates through the Azure SDK's default credential chain, which picks
  up the Azure CLI session `azure/login` opens; the identity needs Storage Blob
  Data Contributor on the container. The provider's `ARM_*` variables do not
  apply to the backend
  ([DIY backends](https://www.pulumi.com/docs/iac/operations/stack-management/using-a-diy-backend/)).
- **Secrets provider**: Azure Key Vault, chosen when each stack is created:
  `pulumi stack init staging --secrets-provider "azurekeyvault://<vault>.vault.azure.net/keys/<key>"`.
  Secret configuration values (`pulumi config set --secret`) are stored
  encrypted in `Pulumi.<stack>.yaml`; the identities need Key Vault Crypto
  User on the key
  ([secrets](https://www.pulumi.com/docs/iac/concepts/secrets/)).
- A self-managed backend has no transactional checkpoints and no web history:
  enable blob versioning and soft delete on the state container, so a bad
  update can be rolled back.
- **Pulumi Cloud** is the alternative: history, locking, OIDC from GitHub,
  ESC for secrets, free for one user and paid per resource for teams. Offer it
  when the user asks for that experience; the workflows then drop `cloud-url`
  and authenticate with Pulumi's OIDC integration.

## One stack per environment

`staging` and `production`, each with its `Pulumi.<stack>.yaml`
(configuration, encrypted secrets, the secrets provider). The stacks differ
only in configuration; a conditional on the stack name in code is a smell.

## CI (`ci-jobs.yml`)

| Job | Credentials | Does |
| --- | --- | --- |
| `pulumi-test` | none | The language's build, lint and unit tests (toolchain file) |
| `pulumi-preview` | the **plan identity**, pull requests from this repository only | `pulumi preview` of `staging` and `production`, into the job summary |

Replace the `# {{pulumi-toolchain-setup}}` and `# {{pulumi-toolchain-test}}`
lines with the steps of `toolchains/<language>.yml`. `pulumi-preview` runs on
every event and skips its steps without a token, so `gate` sees a success.
The preview goes to the **job summary only** (`comment-on-summary`, never
`comment-on-pr`), with `suppress-outputs`.

The Azure Native provider requests its own OIDC token with `ARM_USE_OIDC`,
`ARM_CLIENT_ID`, `ARM_TENANT_ID` and `ARM_SUBSCRIPTION_ID`; the backend and
Key Vault use the Azure CLI session. A preview of Cloudflare resources needs a
**read-only** Cloudflare token as the repository secret
`CLOUDFLARE_PLAN_API_TOKEN` (never available to fork pull requests).

## Deployment (`deploy.yml`)

Same shape as Bicep's: `staging` (`pulumi up`) on every push to `main`,
`production-plan` (preview into the summary for the reviewer), `production`
(`pulumi up`) behind the environment's approval, or on dispatch only where the
plan has no required reviewers. Each environment holds its own Azure identity
variables and, with Cloudflare, its own `CLOUDFLARE_API_TOKEN` secret.

`pulumi/actions@v7` inputs used: `command`, `stack-name`, `work-dir`,
`cloud-url`, `pulumi-version-file`, `comment-on-summary`, `suppress-outputs`
([action](https://github.com/pulumi/actions)).

## Identities and permissions

| Identity | Federated credential subjects | Roles |
| --- | --- | --- |
| Plan | `repo:{{owner}}/{{repo}}:pull_request`, `repo:{{owner}}/{{repo}}:ref:refs/heads/main` | Reader on the resource groups; Storage Blob Data Contributor on the state container (a preview takes the stack lock); Key Vault Crypto User on the key |
| Staging, production | `repo:{{owner}}/{{repo}}:environment:<name>` | Contributor on the environment's resource group; Storage Blob Data Contributor on the state container; Key Vault Crypto User on the key |

## Dependencies

Pulumi's SDK and providers are ordinary NuGet, npm or PyPI packages: Renovate
updates them through the ecosystem's manager. `renovate-rules.json` groups
them (`pulumi`), bumps `.pulumi.version` from Pulumi's GitHub releases, and
types infrastructure updates `build`, so a provider update never releases the
application's package. Provider majors (Azure Native 3 to 4, for example)
stay manual.

## Manual steps

1. A storage account with a private container for the state (blob versioning
   and soft delete on), and a Key Vault with an RSA key for the secrets
   provider, in a resource group of their own that no stack manages.
2. The identities above, with their federated credentials and roles.
3. `pulumi login "$PULUMI_BACKEND_URL"` then `pulumi stack init <name>
   --secrets-provider ...` for each environment, locally once; commit the
   `Pulumi.<stack>.yaml` files.
4. The repository variables (`PULUMI_BACKEND_URL`, `AZURE_PLAN_CLIENT_ID`,
   `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`) and the environments `staging`
   and `production` with their variables (and Cloudflare secrets).
5. With Cloudflare: two API tokens per environment scope (see
   [cloudflare.md](cloudflare.md)), plus a read-only one for previews.

## Audit checklist

- The program's language is the project's; unit tests with mocks run in CI.
- The CLI version is pinned and current; providers are current or a major
  behind at most.
- The state is in a private container with versioning; secrets use Key Vault,
  not a passphrase.
- No client secret, no Pulumi access token in repository secrets when the
  backend is Azure Blob.
- Previews never post to a pull request comment of a public repository.
