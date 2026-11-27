# Deployment: external platforms

Vercel, Netlify and Cloudflare Pages build and deploy from the repository
through their own **Git integration**: production from `main`, a preview
deployment for every pull request, a URL posted on the pull request. The
repository holds no deployment workflow and no credential; it holds the
platform's configuration file, and the platform is set up by hand.

The shared model of the other targets ([model.md](model.md))
does not apply as is: the platform deploys production on every merge to
`main`. To keep "production on a release" with a platform, set its production
branch to a branch nobody pushes to and promote from the platform's dashboard,
or use a deploy target that runs from `release.yml` ([azure.md](azure.md),
[github-pages.md](github-pages.md)). Say this trade-off to the user.

## Choosing

| Platform | Free plan | Commercial use on the free plan | Configuration file | Template |
| --- | --- | --- | --- | --- |
| Netlify | Free (credit-based) | **Allowed** | `netlify.toml` | `templates/deploy/external/netlify.toml` |
| Cloudflare Pages | Free, 500 builds a month | No non-commercial clause in the terms | `wrangler.jsonc` (optional) | see [cloudflare](../iac/cloudflare.md) |
| Vercel | Hobby | **Forbidden**: personal, non-commercial use only; a company project needs Pro | `vercel.json` | `templates/deploy/external/vercel.json` |

For a company profile, never propose Vercel Hobby; for a personal project that
may become commercial, say that Hobby would then have to move to Pro.

## Setup

1. Copy the configuration file and keep its build command identical to the
   React module's (`pnpm install --frozen-lockfile && pnpm run build`, output
   `dist/`), with the single-page application fallback (every unknown path
   serves `index.html`).
2. The user connects the repository on the platform (manual step): production
   branch `main`, build settings read from the file, Node.js version from
   `.nvmrc`.
3. CI still builds the site on every pull request: the platform's build is a
   deployment, not the check that blocks a merge. The ruleset does not require
   the platform's status.
4. Preview deployments of pull requests from forks: allow them only after a
   maintainer's approval (each platform has a setting), since a preview build
   runs the fork's code with the project's environment variables.
5. Environment variables live on the platform, per environment (production,
   preview); none is committed.

## Rollback

All three keep every deployment and can put a previous one back in
production instantly from the dashboard (Vercel "Instant Rollback", Netlify
"Publish deploy", Cloudflare Pages "Rollback"). A fix then goes through a pull
request as usual.

Sources: [Vercel fair use and Hobby terms](https://vercel.com/legal/terms),
[Netlify Free plan](https://www.netlify.com/blog/introducing-netlify-free-plan/),
[Netlify file-based configuration](https://docs.netlify.com/build/configure-builds/file-based-configuration/),
[Vercel project configuration](https://vercel.com/docs/project-configuration),
[Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/),
[Cloudflare terms](https://www.cloudflare.com/terms/). Plans checked on
2026-11-25.

## Manual steps

- Create the project on the platform and connect the repository (the
  platform's GitHub App, limited to this repository).
- Set the production branch, the environment variables per environment, and
  the approval of fork previews.
- Add the custom domain on the platform.

## Audit checklist

- The platform's build command matches CI's.
- No platform token in the repository's secrets (none is needed with the Git
  integration).
- Fork previews need approval.
- Vercel Hobby is not used for a commercial project.
- The trade-off "production on every merge" was accepted, or the production
  branch is gated.
