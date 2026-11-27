# Deployment: Azure

Three services, one way in: `azure/login` with **OpenID Connect**, a
user-assigned managed identity (or an Entra application) that trusts the
repository's GitHub environments, and no stored credential. No publish profile,
no client secret.

The shared model (staging on merge, production on approval, the hand-over from
`release.yml`) is in [model.md](model.md).
The Azure resources themselves come from the infrastructure module
([Bicep or Pulumi](../iac/choosing.md)), which also creates the identity and
its federated credentials.

## Sign-in

- One identity per environment (`id-{{project}}-staging`,
  `id-{{project}}-production`), each with a **federated credential** whose
  subject is the GitHub environment:
  `repo:{{owner}}/{{repo}}:environment:staging` and
  `repo:{{owner}}/{{repo}}:environment:production`, issuer
  `https://token.actions.githubusercontent.com`, audience
  `api://AzureADTokenExchange`. A job outside that environment, or a pull
  request from a fork, cannot obtain a token.
- Each identity gets the narrowest role on its own resources: `Website
  Contributor` on the web app, `Contributor` on the static web app (to read its
  deployment token), `Container Apps Contributor` on the container app. Never a
  subscription-wide role.
- Each GitHub environment holds `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
  `AZURE_SUBSCRIPTION_ID` and the resource names as **variables**: they
  identify, they do not authenticate.
- The deploy job declares `id-token: write` and runs in the environment.

## Static Web Apps (static front ends)

Template: `templates/deploy/azure-static-web-apps/deploy.yml`.

- `staging` deploys to the **named environment** `staging` of the same static
  web app (`deployment_environment: staging`), at a stable
  `<host>-staging.<region>.azurestaticapps.net` URL; `production` deploys to
  its production environment (empty `deployment_environment`). Custom domains
  apply to production only.
- The action needs the app's deployment token. The job reads it at run time
  with `az staticwebapp secrets list ... --query properties.apiKey`, masks it,
  and passes it on: nothing is stored in GitHub. Do not let Static Web Apps
  write its own workflow and secret when creating the resource; create it
  without a GitHub link (from Bicep or Pulumi).
- Prebuilt: `skip_app_build: true`, `app_location: dist`,
  `output_location: ""`; `staticwebapp.config.json` must be in `dist/`
  (navigation fallback for the single-page application, headers).
- Pull request previews of Static Web Apps are not used: they would need the
  token in pull request workflows.
- Rollback: dispatch `deploy.yml` with the previous tag.

## App Service (server applications)

Template: `templates/deploy/azure-app-service/deploy.yml`.

- With **deployment slots** (Standard tier and up): `staging` deploys to the
  `staging` slot; `production` deploys to a `release` slot, smoke-checks it,
  then swaps it into production (`az webapp deployment slot swap`). The swap
  warms the new version up before it takes traffic, and the previous version
  stays in `release`: **rollback is the same swap again**.
- Without slots (Free and Basic tiers): `AZURE_WEBAPP_SLOT` empty, the job
  deploys straight to production; rollback is a dispatch with the previous tag.
- Code: `azure/webapps-deploy` with the published folder. Containers (Web App
  for Containers): the same action with `images:` pointing at the `sha-<commit>`
  image from [ghcr.md](ghcr.md), and no build job.
- Mark slot-specific settings (connection strings that differ per slot) as
  deployment slot settings, so a swap does not carry them.

## Container Apps (containers)

Template: `templates/deploy/azure-container-apps/deploy.yml`.

- One container app per environment (`{{project}}-staging`, `{{project}}`),
  in one Container Apps environment or two.
- The job runs `az containerapp update --image ghcr.io/<owner>/<repo>:sha-<commit>
  --revision-suffix <version>-r<run>`: a new revision of the image
  [`container.yml`](ghcr.md) built for the commit. In single revision mode
  (the default) traffic moves to the new revision only once its replicas are
  running, and stays on the old one if it fails.
- For blue-green or canary, switch the production app to multiple revision
  mode and move traffic with `az containerapp ingress traffic set`; rollback
  is sending 100 % back to the previous revision.
- A private image needs registry credentials on the container app (a GHCR
  token held by the app as a secret, or Azure Container Registry with a managed
  identity); an open-source image is public and needs none.

## Rollback summary

| Service | Fastest rollback |
| --- | --- |
| Static Web Apps | Dispatch `deploy.yml` with the previous tag |
| App Service with slots | Swap `release` and production again |
| App Service without slots | Dispatch `deploy.yml` with the previous tag |
| Container Apps | Traffic back to the previous revision, or dispatch with the previous release's commit |

Sources: [use the Azure Login action with OpenID Connect](https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect),
[deploy to App Service with GitHub Actions](https://learn.microsoft.com/azure/app-service/deploy-github-actions),
[App Service deployment slots](https://learn.microsoft.com/azure/app-service/deploy-staging-slots),
[Static Web Apps build configuration](https://learn.microsoft.com/azure/static-web-apps/build-configuration),
[Static Web Apps named environments](https://learn.microsoft.com/azure/static-web-apps/named-environments),
[`az staticwebapp secrets list`](https://learn.microsoft.com/cli/azure/staticwebapp/secrets),
[Container Apps revisions](https://learn.microsoft.com/azure/container-apps/revisions),
[traffic splitting](https://learn.microsoft.com/azure/container-apps/traffic-splitting).
Action majors checked on 2026-11-25: `azure/login` v3, `azure/webapps-deploy`
v3, `Azure/static-web-apps-deploy` v1.

## Manual steps

- If the infrastructure module did not: create the identities, their
  federated credentials (one per GitHub environment) and their role
  assignments.
- Put the variables on each GitHub environment.
- App Service: create the `staging` and `release` slots (Standard tier), or
  leave `AZURE_WEBAPP_SLOT` empty.
- Container Apps with a private image: registry credentials on each app.

## Audit checklist

- `azure/login` with `client-id`, `tenant-id`, `subscription-id` only: no
  `creds`, no client secret, no publish profile, no stored Static Web Apps
  token.
- Federated credentials scoped to environments, not to branches or
  `pull_request`.
- Roles scoped to the resource, one identity per environment.
- Production changes only after the approval; rollback documented and tried
  once.
