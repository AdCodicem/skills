# Cloudflare

How a project deploys to Cloudflare. With **Bicep**, Cloudflare goes through
**Wrangler**, Cloudflare's own configuration and CLI. With **Pulumi**, the
Cloudflare provider manages it in the same program as Azure
([pulumi.md](pulumi.md)); this file still applies for the API tokens.

Templates: `templates/iac/cloudflare/` (`wrangler.jsonc`, `ci-jobs.yml`,
`deploy.yml`).

## Workers, not Pages, for new projects

Deploy static sites and full-stack applications as a **Worker with static
assets**. Workers offer what Pages offers (static asset requests are free) and
more (Durable Objects, cron triggers, observability); Cloudflare documents the
move from Pages to Workers
([migrate from Pages](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/)).
Keep an existing Pages project unless the user asks to migrate.

## Configuration (`wrangler.jsonc`)

- JSON with comments, validated by Wrangler's schema
  (`node_modules/wrangler/config-schema.json`).
- `compatibility_date` set to the day of the setup (`{{today}}`), then moved
  forward deliberately, staging first: it selects the runtime's behavior.
- One `env` per environment (`staging`, `production`), each with its Worker
  name; routes and custom domains on `production` only.
- `assets.directory` points at the build output; `not_found_handling:
  "single-page-application"` for a single-page application.
- Secrets are never in the file: `wrangler secret put <NAME> --env <env>`, or
  the action's `secrets` input fed from environment secrets.
- Wrangler is a **devDependency** of the project, so Renovate updates it like
  any package, and the action uses that version.
- DNS records and zones stay in the Cloudflare dashboard when the project uses
  Bicep and Wrangler: Wrangler manages Workers, not zones. To manage them in
  code, Pulumi is the recommended route ([choosing.md](choosing.md)).

## CI (`ci-jobs.yml`)

`wrangler-check`, without credentials, so fork pull requests run it too:
regenerates the runtime types (`wrangler types`) and fails when the committed
`worker-configuration.d.ts` drifts, then bundles the Worker with
`wrangler deploy --dry-run --outdir`.

## Deployment (`deploy.yml`)

`staging` on every push to `main`, `production` behind the environment's
approval (or on dispatch only where the plan has no required reviewers),
through `cloudflare/wrangler-action@v4` with `command: deploy --env <name>`.
The environment's URL comes from the action's `deployment-url` output
([wrangler-action](https://github.com/cloudflare/wrangler-action)).

## API tokens: the one stored secret

Cloudflare does not accept GitHub's OIDC tokens, so each environment holds an
**API token** as an environment secret (`CLOUDFLARE_API_TOKEN`) and the
account ID as a variable (`CLOUDFLARE_ACCOUNT_ID`). Keep them narrow:

| Token | Permissions | Resources |
| --- | --- | --- |
| Deploy (Wrangler), per environment | Account: Workers Scripts Edit, Account Settings Read; Zone: Workers Routes Edit (only when the Worker has routes) | The one account; the one zone |
| Deploy (Pulumi), per environment | The above, plus Zone: DNS Edit and the other resource types the program manages | The one account; the zones it manages |
| Plan (Pulumi previews), repository secret `CLOUDFLARE_PLAN_API_TOKEN` | Read permissions of the same resource types | Same |

Create them from the "Edit Cloudflare Workers" template, then remove what the
project does not use (KV, R2, tail) and restrict accounts and zones
([token templates](https://developers.cloudflare.com/fundamentals/api/reference/template/)).
Set an expiry and a reminder to rotate; an environment secret is readable only
by jobs of that environment, after its approval.

## Manual steps

1. Create the API tokens above and put them on the `staging` and `production`
   environments (and the plan token in repository secrets, with Pulumi).
2. Put `CLOUDFLARE_ACCOUNT_ID` on both environments as a variable.
3. First deployment: dispatch `deploy.yml` on `staging`, check the Worker's
   URL, then add the production route or custom domain.

## Audit checklist

- Tokens are scoped to one account and the zones needed, never the Global API
  Key.
- Tokens live in environment secrets, not repository secrets (except the
  read-only plan token).
- `compatibility_date` is recent, and moved through staging first.
- No secret in `wrangler.jsonc`.
