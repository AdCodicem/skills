# Node.js and TypeScript library

A TypeScript package published to npm. The shared Node.js parts (pnpm, Node.js
pin, TypeScript compilers, ESLint and Prettier) are defined here; the React
module ([react.md](react.md)) reuses them.

Templates: `templates/ecosystems/node/`.

## Defaults

| Concern | Choice | Why |
| --- | --- | --- |
| Package manager | **pnpm**, pinned by `packageManager` | Strict `node_modules`, a lockfile CI installs frozen, supply-chain settings on by default |
| Node.js | `.nvmrc` = the latest LTS major, for development, release tooling and CI | semantic-release 26 needs Node.js 26.13 or later |
| Supported Node.js | `engines.node` = `>=` the oldest maintained LTS line; CI tests every maintained LTS | The widest reach that still gets security fixes |
| Language | TypeScript, strict, ESM only | Every maintained Node.js line can `require()` an ES module |
| Compilers | TypeScript 7 (native) for `tsc`, the TypeScript 6 API for tools | See "TypeScript 6 and 7" |
| Build | **tsdown** | See "Build tool" |
| Lint, format | ESLint 10 (flat config) with typescript-eslint, Prettier | |
| Tests | Vitest, V8 coverage | |
| Package checks | publint, Are the Types Wrong (`attw`) | What consumers resolve, checked before every release |
| API reference | TypeDoc with `typedoc-plugin-markdown` and `typedoc-docusaurus-theme` | Markdown for the Docusaurus site ([docs](../areas/docs.md)) |

Keep what a repository already uses when it meets the standard: npm instead of
pnpm, Biome instead of ESLint and Prettier, another test runner with coverage.
Report it as **ok** with a note.

Maintained LTS lines on 2026-11-25: 22 (maintenance until 2027-04-30), 24
(maintenance), 26 (active LTS since 2026-10-28), from the
[release schedule](https://github.com/nodejs/Release/blob/main/schedule.json).
Re-read the schedule: when a line ends, raise `engines.node` in a commit marked
breaking (`feat!:`), since it drops a runtime consumers may still use; that is a
person's decision, never a bot's. CI follows on its own: its matrix uses the
aliases `lts/-2`, `lts/-1`, `lts/*`.

## Set up

1. A new package: `pnpm init`, then copy `package.json` from the templates over
   it, filling `{{package}}`, `{{description}}`, `{{copyright-holder}}`,
   `{{owner}}`, `{{repo}}`, `{{node-oldest-lts}}` (22 today) and
   `{{pnpm-version}}` (`npm view pnpm version`). Starter `src/index.ts` and
   `test/index.test.ts` are in the templates.
2. Copy `tsconfig.json`, `tsconfig.lib.json`, `tsdown.config.ts`,
   `eslint.config.js`, `prettier.config.js`, `dot-prettierignore` (to
   `.prettierignore`), `vitest.config.ts`, `pnpm-workspace.yaml`, `typedoc.json`
   (complete tier) and `dot-nvmrc` (to `.nvmrc`, filling `{{node-lts}}`, 26
   today). Append `gitignore` to `.gitignore`.
3. Install the development dependencies at their latest versions, so no version
   is written from memory:

   ```bash
   pnpm add -D "typescript@npm:@typescript/typescript6" "@typescript/native@npm:typescript" \
     @types/node tsdown eslint @eslint/js typescript-eslint eslint-config-prettier globals \
     prettier vitest @vitest/coverage-v8 publint @arethetypeswrong/cli
   pnpm add -D typedoc typedoc-plugin-markdown typedoc-docusaurus-theme   # complete tier
   ```

   Release tooling (semantic-release and its plugins, [release](../areas/release.md))
   goes into this same `package.json` as devDependencies: a Node repository has
   no separate release `package.json`.
4. Run `pnpm run lint`, `pnpm run typecheck`, `pnpm run test`,
   `pnpm run build` and `pnpm run check:package`; all must pass before the CI
   is written.

## `package.json`

- `"license"` is the profile's SPDX identifier (`MIT` in the template;
  `UNLICENSED` for a proprietary package).
- `"type": "module"`, an `exports` map with `types` before `default`, and
  `./package.json` exported (tools read it).
- `"files": ["lib"]`: only the build ships. The package README and LICENSE are
  included by npm automatically. Changing the README is a `docs(readme)` commit.
- `"version": "0.0.0-managed-by-semantic-release"`: the version lives in tags;
  the release's pack job stamps it into the tarball only.
- `"publishConfig": { "access": "public" }` for a scoped package. No
  `provenance` key: npm generates provenance by itself for trusted publishing
  from a public repository
  ([trusted publishers](https://docs.npmjs.com/trusted-publishers)).
- `repository.url` must name the GitHub repository exactly: npm checks it
  against the trusted publisher and the provenance.
- Scripts are the contract CI calls: `build`, `typecheck`, `lint`,
  `format:check`, `test`, `test:coverage`, `check:package`, `docs:api`.

## pnpm

- Settings live in `pnpm-workspace.yaml` (pnpm 11 and later); `.npmrc` holds
  registry authentication only, and a public package needs none
  ([pnpm 11](https://pnpm.io/blog/releases/11.0)).
- Secure defaults stay as they are: `minimumReleaseAge` of one day,
  `strictDepBuilds` (an unreviewed install script fails the install),
  `blockExoticSubdeps` ([settings](https://pnpm.io/settings)). The template
  adds `trustPolicy: no-downgrade`, which refuses a version that lost the trust
  evidence earlier versions had, and an empty `allowBuilds` allow-list.
- pnpm 12 fails on an unknown key in `pnpm-workspace.yaml` when
  `packageManager` pins it ([pnpm 12](https://pnpm.io/blog/releases/12.0)):
  check a setting's name before adding it.
- An urgent security fix younger than a day: add the package to
  `minimumReleaseAgeExclude` for that update, then remove it.
- CI gets pnpm from `pnpm/action-setup`, which reads `packageManager`; Corepack
  is not bundled with Node.js 25 and later
  ([Node.js docs](https://nodejs.org/download/release/v25.8.0/docs/api/corepack.html)),
  so never rely on `corepack enable`. `pnpm/action-setup` runs before
  `actions/setup-node`, which then caches the pnpm store.
- npm users: npm 12 no longer runs dependencies' install scripts unless
  approved (`npm approve-scripts`) ([npm 12](https://www.infoq.com/news/2026/08/npm-12-released/)).

## TypeScript 6 and 7

TypeScript 7.0 (2026-07-08) is the native compiler, about ten times faster, but
it ships no programmatic API before 7.1, and typescript-eslint and TypeDoc
still declare `typescript <6.1` as their peer
([TypeScript 7.0](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/)).
Follow Microsoft's side-by-side setup:

```json
{
  "devDependencies": {
    "@typescript/native": "npm:typescript@^7.0.2",
    "typescript": "npm:@typescript/typescript6@^6.0.2"
  }
}
```

`tsc` is then TypeScript 7 (type checking), while every tool that imports
`typescript` gets the 6.0 API. Declarations need neither: `tsconfig.lib.json`
turns on `isolatedDeclarations`, and tsdown generates them with Oxc. When
typescript-eslint and TypeDoc accept TypeScript 7 in their
`peerDependencies`, replace both aliases with a plain `typescript`.

The compiler options are strict beyond `strict` (`noUncheckedIndexedAccess`,
`exactOptionalPropertyTypes`, `verbatimModuleSyntax`, `erasableSyntaxOnly`).
`tsconfig.json` checks everything (sources, tests, configuration files);
`tsconfig.lib.json` adds `isolatedDeclarations` for the published sources only,
so `pnpm run typecheck` runs both.

## Build tool

**tsdown**, a library bundler on Rolldown, designed as tsup's successor with a
migration guide ([tsdown](https://tsdown.dev/guide/migrate-from-tsup)): one
config file, ESM output, declarations through Oxc, and the same engine as
Vite 8. It is still 0.x, so read its release notes before a minor bump (majors
and minors of 0.x packages are not auto-merged). Plain `tsc` is fine for a
package with no bundling needs; keep tsup where it already works.

The output goes to `lib/`, not `dist/`: at the repository root, `dist/` is the
release staging folder ([release](../areas/release.md)), and the pack job would
otherwise mix the build with the tarballs.

## CI

`ci-jobs.yml`: `node-lint` (Prettier, ESLint), `node-typecheck`, `node-test`
(every maintained LTS line; coverage to the job summary and, for public
profiles at the standard tier, to Codecov over OIDC), `node-build` (tsdown,
publint, attw). Each job installs with `pnpm install --frozen-lockfile`.

## Release

- `release-pack.yml`: install without cache, stamp `$VERSION` with
  `npm version --no-git-tag-version`, build, check, `pnpm pack` into
  `dist/npm/`.
- `release-publish.yml`: npm trusted publishing over OIDC, no token; needs npm
  11.15.0 or later and Node.js 22.14 or later, which the step checks
  ([staged publishing](https://docs.npmjs.com/staged-publishing)).
  - A **stable** release is **staged** (`npm stage publish`): it goes live when
    a maintainer approves it with 2FA, on npmjs.com (Staged Packages) or with
    `npm stage approve <id>`. Trusted publisher configurations created since
    2026-09-03 allow only staging unless publishing is enabled, and npm
    recommends keeping it so
    ([changelog](https://github.blog/changelog/2026-09-03-multiple-trusted-publishing-configurations-for-npm)).
    Approve right after the release run; the GitHub release is already
    published.
  - A **preview** (a version with a hyphen) is published directly under the
    `next` dist-tag by a second trusted publisher configuration, for
    `preview.yml` and the `preview` environment, allowed to publish.
  - A version already on the registry is skipped: rerunning a failed job is
    safe.
- `preview-inputs`: what makes a new preview worth publishing.
- `docs-api.yml` (complete tier): `pnpm run docs:api` before the Docusaurus
  build.

## Dependencies

Renovate's shared preset handles npm and pnpm: `dependencies` and
`peerDependencies` updates are `fix(deps)` (they ship), everything else
`build(deps)`. Merge `renovate-rules.json` into `renovate.json`: it never
touches `engines` (a support policy) and groups the two TypeScript compilers.

## Monorepo

Several packages: list them under `packages:` in `pnpm-workspace.yaml`, keep
one root `package.json` for tooling and release, one version for every package
([release](../areas/release.md)), and have `release-pack.yml` stamp and pack
each published package (`pnpm --filter <name> ...`).

## Manual steps

- The package must exist on npm before a trusted publisher can be added
  ([npm trust](https://docs.npmjs.com/cli/v11/commands/npm-trust)). For a new
  package, stage it once from your machine, logged in with 2FA
  (`npm stage publish`, which creates the public placeholder `0.0.0-stage`).
- On npmjs.com, package Settings, add two trusted publishers (GitHub Actions):
  repository `{{owner}}/{{repo}}`, workflow `release.yml`, environment
  `release`, **stage only**; and workflow `preview.yml`, environment
  `preview`, allowed to publish (complete tier). `npm trust github --help`
  does the same from the command line.
- Package Settings, Publishing access: "Require two-factor authentication and
  disallow tokens".
- Revoke any automation token the package used before.

## Audit checklist

- `packageManager` pins the package manager; the lockfile is committed and CI
  installs it frozen.
- `pnpm-workspace.yaml` keeps the secure defaults and sets
  `trustPolicy: no-downgrade`; no `.npmrc` setting besides authentication.
- `engines.node` names the oldest maintained LTS line; CI tests every
  maintained line.
- `exports` resolve for every consumer: publint and attw pass.
- No `NPM_TOKEN` secret; trusted publishing with stage-only for stable
  releases; "disallow tokens" on the package.
- No `postinstall` script in the package itself.
- TypeScript aliases still needed (tools' peer ranges), or replaced by a plain
  `typescript`.
