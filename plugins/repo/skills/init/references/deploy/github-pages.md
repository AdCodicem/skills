# Deployment: GitHub Pages

The model every target follows (staging, production, the hand-over from
`release.yml`, rollback) is in [model.md](model.md).

A static single-page application (Vite `dist/`) served by Pages.

- **Production only.** Pages serves one site per repository, so there is no
  staging on Pages: do not install `staging.yml`. A staging URL needs another
  target ([Azure Static Web Apps](azure.md) has named environments; the
  [external platforms](external.md) deploy previews for every pull request).
  The site still builds on every pull request, in CI.
- **Private repositories** need GitHub Pro, Team or Enterprise for Pages, and
  a private Pages site (visible to members only) needs Enterprise Cloud.
- Template: `templates/deploy/pages/deploy.yml`.
  - `build`: checks out `ref`, runs the React module's build with
    `actions/configure-pages`' `base_path` as Vite's `--base` (a project site
    lives under `/<repository>/`; empty for a custom domain), and uploads
    `dist/` with `actions/upload-pages-artifact`.
  - `deploy`: `actions/deploy-pages` in the `github-pages` environment, with
    `pages: write` and `id-token: write`, then the smoke check.
- **The `github-pages` environment is the gate**, not `production`: Pages
  deployments run there. Put the required reviewer on `github-pages`, and grant
  `pages: write` in `deploy-production`'s permissions.
- Set the repository's Pages source to **GitHub Actions** (not a branch).
- A single-page application with client-side routes needs a `404.html` copy of
  `index.html` (Pages has no rewrite rules); the React module's build can copy
  it.
- Rollback: dispatch `deploy.yml` with the previous tag; the build is
  reproduced from that tag.

Sources: [using custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[what is GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages),
[actions/deploy-pages](https://github.com/actions/deploy-pages),
[actions/configure-pages](https://github.com/actions/configure-pages),
[reusing workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows),
[managing environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
Action majors checked on 2026-11-25: `configure-pages` v6, `upload-pages-artifact`
v5, `deploy-pages` v5.

## Manual steps

- Create the environments: `staging` (deployment branch `main`) and
  `production` (deployment branch `main`, required reviewer where the plan
  allows it); for Pages, configure `github-pages` instead of `production`.
  `scripts/github_settings.py` creates them where the API allows.
- Pages: Settings, Pages, Source: **GitHub Actions**; a custom domain and
  "Enforce HTTPS" if wanted.

## Audit checklist

- No workflow deploys production on a push; production follows an approved
  release or an approved dispatch.
- `deploy.yml` never cancels a deployment in progress.
- Build and deploy are separate jobs; the deploy job builds nothing.
- Every environment has a `url` and a smoke check.
- No deployment secret in the repository: OIDC, or a token read at run time.
- Pages: the source is GitHub Actions, the reviewer is on `github-pages`.
