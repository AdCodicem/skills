# The private operations repository

Where infrastructure lives:

| Profile | Infrastructure |
| --- | --- |
| Personal open source, company open source | A separate **private** repository, `{{project}}-ops`. The public repository holds **no** infrastructure: no Bicep, no Pulumi program, no deployment workflow |
| Personal private, company private | `infra/` in the application's repository; a dedicated repository on request (several applications, a separate operations team) |

Why, for open source: the public repository is the product; how and where the
maintainer runs an instance (subscription, resource groups, domains, sizes,
environment settings) is theirs. Keeping it private removes a whole class of
leaks (plans, resource names, identifiers in logs and pull requests) and keeps
deployment credentials out of a repository that accepts pull requests from
anyone.

Templates: `templates/iac/ops-repo/` (`README.md`, `renovate-rules.json`),
plus the chosen tool's files ([bicep](bicep.md) or [pulumi](pulumi.md),
[cloudflare](cloudflare.md)) with `{{infra-dir}}` set to `.`.

## Setting it up

Run the whole skill on the new repository, as its own project:

1. **Project kind**: infrastructure; **profile**: personal private or company
   private (it is private whatever the application's profile); **tier**:
   minimal is usually enough.
2. The core applies as for any repository: ruleset on `main` (the plan must
   allow rulesets on private repositories: Pro, Team or above, see
   [github-plans](../github-plans.md)), `ci.yml` with `gate`, `lint.yml`,
   Renovate (actions included), `CLAUDE.md`. There is no release
   workflow: what ships from here is a deployment, not a package.
3. The tool's files at the root, `ci-jobs.yml` merged into `ci.yml`, and
   `deploy.yml` without its `paths` filter.
4. `README.md` from the template: what the repository is, its layout, how a
   release reaches production.
5. `renovate-rules.json` from both the tool and `ops-repo/`, merged into
   `renovate.json`.

The application's repository gets a line in its `CLAUDE.md` and
`CONTRIBUTING.md` saying where deployments are defined, without linking a
private repository contributors cannot open (say "a private operations
repository").

## How a release reaches production

The application repository releases; the operations repository deploys. No
token crosses from one to the other:

1. The application's approved release publishes an artifact with a version: a
   container image on GHCR (tag `<version>` and its digest, see
   [deploy/ghcr](../deploy/ghcr.md)), or a release asset.
2. The operations repository pins it, **tag and digest**, in the parameter or
   stack files:
   - Bicep: `param appImage = 'ghcr.io/{{owner}}/{{project}}:1.4.0@sha256:<digest>'`
     in each `main.<environment>.bicepparam`;
   - Pulumi: `{{project}}:appImage: ghcr.io/{{owner}}/{{project}}:1.4.0@sha256:<digest>`
     in each `Pulumi.<environment>.yaml`.
3. Renovate's custom manager (`ops-repo/renovate-rules.json`) sees the new
   release on GHCR and opens one pull request that bumps the tag and the
   digest everywhere. CI shows the plan of both environments in the job
   summary.
4. Merging deploys staging; approving `production` deploys production.

Details of that rule:

- `minimumReleaseAge` is disabled for the project's own images: GHCR exposes
  no release timestamps, so a release age would hold these updates forever
  ([Renovate minimum release age](https://docs.renovatebot.com/key-concepts/minimum-release-age/)),
  and the application's own approved release already gates them.
- Never merged unattended: a new application version is a deployment decision.
- A private image needs Renovate to read GHCR: give the runner a
  `hostRules` entry for `ghcr.io` with a token that can read packages, or keep
  the image public (the default for an open-source project).
- To deploy a version to staging without waiting for Renovate, edit the
  staging file in a pull request; production follows when the production file
  is bumped.

## What stays in the public repository

- The `Dockerfile` or build that produces the artifact, its CI, and its
  release (which publishes the image and attests it).
- Optionally, a **generic, deployable example** for people who want to run
  their own instance, without any value of the maintainer's instance, under
  `examples/deploy/`, built in CI but never deployed by it. Offer it, do not
  impose it.

## Manual steps

1. Create the private repository `{{project}}-ops` (same owner as the
   application).
2. Install the Renovate App on it.
3. The tool's own manual steps (identities with federated credentials whose
   subjects name `{{owner}}/{{project}}-ops`, environments, state storage for
   Pulumi, Cloudflare tokens).

## Audit checklist

- An open-source repository contains no infrastructure code and no deployment
  workflow with cloud credentials.
- The operations repository is private, protected by a ruleset, with
  `production` behind an approval or a dispatch.
- Application versions are pinned by tag **and** digest, and bumped by pull
  requests.
- No token of the operations repository exists in the application repository.
