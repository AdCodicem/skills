# Release

**Merging publishes nothing.** A stable release is a deliberate act: someone
dispatches `release.yml`, an approved environment holds the credentials, and
the release goes out drafted, attested, then published as immutable. Previews,
at the complete tier, are published weekly, and only when something that ships
changed.

semantic-release computes the version from the Conventional Commits on `main`,
writes the changelog and creates the tag and the GitHub release. It runs on
Node.js whatever the repository's language: it only orchestrates, it never
builds.

Templates: `templates/release/` (`dot-releaserc.json`, `package.json`,
`dot-github/workflows/release.yml`, `dot-github/workflows/preview.yml`,
`dot-github/scripts/next-version.mjs`, `dot-github/scripts/preview-gate.sh`,
`docs.yml`), plus each module's `release-pack.yml` and `release-publish.yml`
fragments.

## Versions

- [SemVer 2.0](https://semver.org/) with [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/):
  `feat` releases a minor, `fix` and `perf` a patch; `build(pack)` and
  `docs(readme)` a patch too, because package metadata and the package README
  ship inside every package; `build`, `ci`, `chore`, `docs`, `refactor`,
  `style` and `test` release nothing.
- **0.x until the API is stable.** semantic-release cannot start below 1.0.0
  on its own: place the baseline tag `v0.0.0` on the first commit when the
  repository is set up (`git tag v0.0.0 <first-commit>` then
  `git push origin v0.0.0`). The first `feat` then releases 0.1.0.
- While the major is 0, a breaking change (`!` or a `BREAKING CHANGE:` footer)
  releases a **minor**: the first `releaseRules` entry says so. At 1.0, replace
  that entry with `{ "breaking": true, "release": "major" }`, never delete it,
  or `build(pack)!` and `docs(readme)!` fall back to a patch.
- **One version for the whole repository**, every package and component
  together, independent of the framework's version (a .NET 11 release is not a
  reason for an 11.0.0).
- The version lives in tags only. Nothing commits it to a project file: the
  pack job stamps it at build time (`-p:Version`, `npm version
  --no-git-tag-version`, `uv version`).

## `release.yml`

Dispatched by hand from `main`, with a `dry_run` input (default `true`) that
stops after printing the next version and its notes.

| Job | Runs | Credentials |
| --- | --- | --- |
| `plan` | `next-version.mjs`: the next version, or nothing to release | none |
| `verify` | `ci.yml` through `workflow_call`: the very jobs of every pull request | none |
| `pack` | Each module's `release-pack.yml` steps, with `VERSION` (the next version) and `LAST_VERSION` (the last release, for API compatibility checks) set; uploads `dist/*/*` and its SHA-256 manifest | none |
| `publish` | In the **`release` environment**: checks the digests, attests `dist/`, runs semantic-release (tag, changelog commit, **draft** release with the files attached), runs each module's `release-publish.yml` steps, then publishes the draft | the environment's App key, the registries' OIDC |
| `docs` | `docs.yml` through `workflow_call` (complete tier) | Pages |

Why this shape:

- **Third-party code never shares a job with a credential.** Builds and tests
  run where no token can be read; the publish job builds nothing and refuses
  files whose digest changed since `pack`.
- **The environment is the approval gate.** Its required reviewer is the
  maintainer; its deployment branch rule allows `main` only; it alone holds
  `RELEASE_APP_PRIVATE_KEY`. Where the plan has no required reviewers
  (private repositories below Enterprise Cloud), the dispatch itself is the
  gate: only people with write access can dispatch.
- **A GitHub App pushes the changelog commit and the tag**, because the
  ruleset on `main` refuses direct pushes and `GITHUB_TOKEN` cannot be put on
  a bypass list. One App per account serves every repository: permissions
  Contents and Pull requests read and write, no webhook, installed on the
  repositories that release, and added to each ruleset's bypass list.
- **Draft, attest, publish.** Immutable releases lock the tag and the assets
  once a release is published, so everything is attached to the draft first:
  the packages and their [artifact attestation](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
  bundle (`actions/attest`, Sigstore). Publishing the draft is the last step,
  after every registry accepted the packages.
- **Resumable.** If a registry fails after the draft exists, rerunning the
  failed job skips semantic-release (the tag exists) and retries the
  registries, which skip what they already have, then publishes the draft.
- **Trusted publishing everywhere**: NuGet (`NuGet/login`), npm (OIDC, with
  provenance), PyPI (`pypa/gh-action-pypi-publish`, with PEP 740
  attestations). No registry token is ever stored. Each registry needs a
  trusted publisher registered once, naming the repository, `release.yml` and
  the `release` environment (manual step).
- Attestations need a public repository or Enterprise Cloud: the attest step
  runs only when `github.event.repository.private` is false. Remove that
  condition on Enterprise Cloud.
- semantic-release runs on the current Node.js LTS (`node-version: "26"`,
  kept current by `scripts/latest_versions.py`): its latest major requires
  it, whatever Node.js version the project itself uses.
- A module's publish steps may set up their own toolchain (the publish job has
  a checkout) and attest more than the packages (the .NET module also attests
  the assemblies inside them, because nuget.org re-signs packages).

## `.releaserc.json`

From `templates/release/dot-releaserc.json`:

- `branches: ["main"]`, `tagFormat: "v${version}"`.
- `@semantic-release/commit-analyzer` and
  `@semantic-release/release-notes-generator` with the `conventionalcommits`
  preset and the release rules above; notes sections Features, Bug fixes,
  Performance, Packaging, Documentation, Reverts.
- `@semantic-release/exec` `prepareCmd` checks that the version semantic-release
  computed is the one `pack` stamped (`PACKED_VERSION`), and refuses
  otherwise.
- `@semantic-release/changelog` (`CHANGELOG.md`, with a title that says how
  releases work) and `@semantic-release/git` (commits `CHANGELOG.md`, plus the
  versioned documentation at the complete tier, with `[skip ci]`).
- `@semantic-release/github` with `draftRelease: true`, the `dist/` files and
  attestation bundles as assets, `successCommentCondition: false` and
  `failCommentCondition: false` (comments on every linked issue are noise, and
  a 422 on one of them once broke a release).

Release tooling lives in a root `package.json` marked `private` (version
`0.0.0-managed-by-semantic-release`) with a committed lock file, so Renovate
updates it and CI installs exactly what was reviewed (`npm ci --ignore-scripts`).
In a Node repository the same devDependencies go into the existing
`package.json` instead.

## Previews (complete tier)

`preview.yml` runs every Monday morning and on dispatch, from `main` only:

1. `plan` computes `<next>-preview.<commits since the last stable tag>`
   (`next-version.mjs`), mapped per ecosystem when the registry needs another
   form (PEP 440 for PyPI: `<next>.dev<height>`).
2. `preview-gate.sh` compares the package inputs (`.github/preview-inputs`,
   one path per line, written by the modules present) between `HEAD` and the
   commit of the last **successful deployment of the `preview` environment**,
   read from GitHub's deployments API. Nothing changed: the run stops green
   with "nothing to publish". This works for every registry, without querying
   any.
3. `verify`, `pack` and `publish` as in `release.yml`, in the `preview`
   environment (deployment branch `main`, no reviewer): previews carry no
   approval, no GitHub release and no changelog entry; npm publishes them
   under the `next` dist-tag.

A preview carries no compatibility promise: the next merge may reshape what a
preview shipped. Say so in the README.

## What a module provides

| Fragment | Content |
| --- | --- |
| `release-pack.yml` | `steps:` for the `pack` job: toolchain setup, restore, pack with `$VERSION`, output under `dist/<registry>/` (`dist/nuget`, `dist/npm`, `dist/pypi`); only `dist/*/*` is uploaded, so stray build output never becomes a release asset |
| `release-publish.yml` | `steps:` for the `publish` job: the registry's OIDC login and push, idempotent (skip what exists), never building anything |
| `preview-inputs` | The paths whose change makes a new preview worth publishing |

A deployed application has no `release-publish.yml`: its release deploys
production instead. Paste the jobs of `templates/deploy/release-jobs.yml`
into `release.yml` and add `deploy-production` to `publish.needs`, so the tag
only records what production runs (see [the deployment model](../deploy/model.md));
a repository that ships a container image also grants `packages: write` to
the jobs that push it.

## Manual steps

- Create the release GitHub App once per account; install it on the
  repository; add it to the bypass list of the ruleset on `main` (mode *Always
  allow*, or `scripts/github_settings.py --release-app-id`); put
  `RELEASE_APP_CLIENT_ID` (variable) and `RELEASE_APP_PRIVATE_KEY` (secret) on
  the `release` environment only. Previews push nothing to the repository and
  need no App.
- Register the trusted publisher on each registry: repository, workflow file
  `release.yml` (and `preview.yml`), environment `release` (and `preview`).
  npm stages stable releases by default for configurations created since
  2026-09-03: each stable release then waits for a 2FA approval on npmjs.com
  ([node](../ecosystems/node.md)).
- Push the `v0.0.0` baseline tag.
- Enable immutable releases (`scripts/github_settings.py` does it where the API
  allows).

## Audit checklist

- No workflow publishes on `push` to `main`.
- Release credentials live on an environment limited to `main`, with a
  reviewer where the plan allows it.
- No long-lived registry token in secrets.
- Releases are drafted, attested where possible, then published; immutable
  releases are on.
- `releaseRules` handle 0.x, `build(pack)` and `docs(readme)`.
- A baseline tag exists below 1.0.0.
