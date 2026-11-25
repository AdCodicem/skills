# React application

A React single-page application, built with Vite and deployed, never published
to a registry. It reuses the Node.js parts of [node.md](node.md): pnpm and its
settings, the `.nvmrc` pin, the two TypeScript compilers, ESLint with
typescript-eslint, and Prettier.

Templates: `templates/ecosystems/react/`, plus from `templates/ecosystems/node/`:
`pnpm-workspace.yaml`, `dot-nvmrc`, `prettier.config.js`, `dot-prettierignore`.

## Defaults

| Concern | Choice |
| --- | --- |
| Framework | Vite with React and TypeScript (the `react-ts` template) |
| Lint, format | ESLint 10 with typescript-eslint, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`; Prettier |
| Unit and component tests | Vitest with jsdom and Testing Library |
| End-to-end tests | Playwright against the production build (complete tier) |
| Node.js | `.nvmrc` only: an application runs on one version, so CI has no matrix |
| Output | `dist/`, static files for the deployment target |

Create React App is deprecated since 2025-02-14; never start a project with it,
and propose migrating one that uses it to Vite
([React blog](https://react.dev/blog/2025/02/14/sunsetting-create-react-app)).

**Next.js only when the application needs a server**: server-side rendering for
search engines or first paint, server actions, API routes beside the pages, or
per-request data. A static SPA served from GitHub Pages, a CDN or a container
does not; Vite is simpler to build, test and host. When Next.js is chosen, keep
this module's lint, test and CI shape and deploy it as a container
([ghcr](../deploy/ghcr.md)) or to Azure ([azure](../deploy/azure.md)).

## Set up

1. Generate the app at the latest version:

   ```bash
   pnpm create vite@latest <folder> --template react-ts --no-interactive
   ```

   The template currently configures **oxlint** and a plain TypeScript 7
   dependency. Replace them with the standard below (remove `.oxlintrc.json`
   and `oxlint`); a repository that already chose oxlint and runs it in CI
   keeps it, reported as **ok**.
2. Copy `vite.config.ts`, `eslint.config.js`, `src/test/setup.ts`,
   `src/App.test.tsx`, and the shared Node.js files listed above. Append
   `gitignore` to `.gitignore`.
3. In `tsconfig.app.json`, add `"strict": true`,
   `"noUncheckedIndexedAccess": true` and `"exactOptionalPropertyTypes": true`.
   In `tsconfig.node.json`, extend `include` to
   `["vite.config.ts", "playwright.config.ts", "e2e"]` so ESLint's type-aware
   rules find every file.
4. Install, at the latest versions:

   ```bash
   pnpm remove typescript oxlint
   pnpm add -D "typescript@npm:@typescript/typescript6" "@typescript/native@npm:typescript" \
     eslint @eslint/js typescript-eslint eslint-config-prettier globals \
     eslint-plugin-react-hooks eslint-plugin-react-refresh prettier \
     vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/dom @testing-library/jest-dom
   pnpm add -D @playwright/test   # complete tier, with playwright.config.ts and e2e/
   ```

5. Set the scripts CI calls in `package.json`, and pin `packageManager`
   (`pnpm@<latest>`):

   | Script | Command |
   | --- | --- |
   | `build` | `tsc -b && vite build` |
   | `typecheck` | `tsc -b` |
   | `lint` | `eslint .` |
   | `format`, `format:check` | `prettier --write .`, `prettier --check .` |
   | `test`, `test:coverage` | `vitest run`, `vitest run --coverage` |
   | `test:e2e` | `playwright test` |

6. Run `pnpm run lint --fix`, then fix what remains in the generator's sample
   code (the strict type-checked rules forbid, for example, the non-null
   assertion on `document.getElementById("root")`), and check that `lint`,
   `typecheck`, `test` and `build` pass.

## Configuration notes

- `vite.config.ts` holds the Vitest configuration (`test:`), so the app and its
  tests share one module graph. Coverage writes `coverage/lcov.info` and
  `coverage/coverage-summary.json` at a fixed path.
- `base` comes from `VITE_BASE_PATH`, which a GitHub Pages project site sets to
  `/<repository>/`; other targets serve the app at `/`.
- Testing Library's automatic cleanup needs test globals; they are off, so
  `src/test/setup.ts` cleans up after each test and registers the jest-dom
  matchers for Vitest.
- Playwright tests the production build through `vite preview`, the closest
  local equivalent of what is deployed. Its browsers come from
  `playwright install`, never from an install script.

## CI

`ci-jobs.yml`: `react-lint`, `react-typecheck`, `react-test` (coverage to the
job summary and, for public profiles at the standard tier, to Codecov over
OIDC), `react-build`, and `react-e2e` at the complete tier (Chromium only; the
HTML report is kept as an artifact when it fails).

## Release and deployment

An application has no `release-pack.yml` and no `release-publish.yml`: nothing
goes to a registry. A merge to `main` deploys to staging; a stable release
(the same `release.yml` dispatch, version and changelog as any repository)
promotes to production through the `production` environment. The deployment
workflows build from the released commit with `pnpm run build`, setting
`VITE_BASE_PATH` when needed:

- static hosting on GitHub Pages: [github-pages](../deploy/github-pages.md);
- a container image on GHCR (nginx or a Node.js server serving `dist/`):
  [ghcr](../deploy/ghcr.md);
- Azure Static Web Apps or App Service: [azure](../deploy/azure.md);
- Netlify, Cloudflare Pages or Vercel through their Git integration:
  [external](../deploy/external.md). Vercel's Hobby plan forbids commercial use.

The application's own version can be shown in the UI by passing
`VITE_APP_VERSION` from the release to the build.

## Dependencies

Renovate's shared preset applies: `dependencies` (what ends up in the bundle)
are `fix(deps)` and trigger a release, devDependencies `build(deps)`. Merge
`renovate-rules.json` into `renovate.json` to group the TypeScript compilers.

## Manual steps

- The deployment target's own one-time steps, in its reference file.
- Approve the `production` environment's first deployment, and add its
  required reviewers where the plan allows ([github-plans](../github-plans.md)).

## Audit checklist

- Built with Vite (or Next.js for a stated server need), not Create React App.
- `lint`, `typecheck`, `test` and `build` run in CI; e2e at the complete tier.
- Strict TypeScript options in `tsconfig.app.json`.
- No secret in `VITE_*` variables: everything prefixed `VITE_` ends up in the
  public bundle.
- The deployment builds from the released commit, not from a pull request
  artifact.
