# Deployment: container images on GHCR

The image is the unit that ships: built **once per commit**, pushed to
`ghcr.io/<owner>/<repo>:sha-<commit>`, attested, then deployed to staging and
production unchanged. A release adds version tags to the same digest. Where
the image runs (Azure Container Apps, App Service, a Kubernetes cluster, a
platform) is the deploy target's concern: [azure.md](azure.md), or an
operations repository ([ops-repo](../iac/ops-repo.md)) that pins the digest.

The shared model (staging on merge, production on approval, the hand-over from
`release.yml`) is in [model.md](model.md).

## Templates

| File | Copied to | Role |
| --- | --- | --- |
| `templates/deploy/ghcr/container.yml` | `.github/workflows/container.yml` | Reusable: build the image of a commit, push it as `sha-<commit>`, attest it; reuse it if it exists |
| `templates/deploy/ghcr/release-publish.yml` | the `publish` job of `release.yml` | Add `<version>`, `<major>.<minor>` and `latest` to the released digest |
| `templates/deploy/staging.yml` | `.github/workflows/staging.yml` | Its `image` job calls `container.yml` before deploying staging |
| `templates/deploy/release-jobs.yml` | `release.yml` | Its `image` job calls `container.yml` before `deploy-production` |

## How `container.yml` works

1. `check` looks for `sha-<commit>` on GHCR (`skopeo inspect`, preinstalled
   on GitHub's Ubuntu runners). If it exists, the workflow returns its digest
   and builds nothing: a release reuses what staging pushed.
2. `build` runs with `contents: read` only: `docker/setup-buildx-action`,
   `docker/metadata-action` (OCI labels, among them
   `org.opencontainers.image.source`, which links the package to the
   repository), and `docker/build-push-action` with `push: false`,
   `provenance: mode=max`, `sbom: true`, writing an OCI archive. The
   Dockerfile, which is third-party code in practice (base images, package
   installs), never runs next to a write token.
3. `push` holds `packages: write`, builds nothing: `skopeo copy --all
   --preserve-digests` pushes the archive, provenance and SBOM included, then
   `actions/attest` with `push-to-registry: true` attests the digest (public
   repositories and Enterprise Cloud only; the step is skipped elsewhere).

Verify the first run: `gh attestation verify oci://ghcr.io/<owner>/<repo>@<digest> --repo <owner>/<repo>`
and `docker buildx imagetools inspect ghcr.io/<owner>/<repo>@<digest> --format '{{json .Provenance}}'`.

## Rules

- **Tags**: `sha-<commit>` for every built commit; `<version>`, `<major>.<minor>`
  and `latest` only from a stable release; previews add `<preview version>`
  only (drop `latest` and `<major>.<minor>` in `preview.yml`). Deploy by digest
  or by `sha-` tag, never by `latest`.
- **Base images** pinned by digest in the Dockerfile
  (`FROM image:tag@sha256:...`); Renovate keeps both current
  (`docker:pinDigests`, see [renovate](../renovate.md)). GHCR has no release
  timestamps for Renovate's release-age check: a GHCR base image needs a
  package rule (`minimumReleaseAge: null` for it) or it waits forever.
- `.dockerignore` excludes `.git`, build output, `node_modules`, secrets and
  local environment files.
- Run as a non-root user; one process per container; a health endpoint for the
  smoke checks.
- `sha-` tags on a public image are visible: an open-source project that must
  publish nothing before a release keeps the image private until the first
  release, or builds only from `release.yml` (drop the `image` job of
  `staging.yml` and deploy staging another way).
- **Previews** (complete tier): `preview.yml` calls `container.yml` as an
  `image` job too, and its `publish` job adds the preview tag.

## Rollback

Production runs a digest: redeploy the previous release's commit (`deploy.yml`
dispatch with that commit) or, on Container Apps, send traffic back to the
previous revision. `latest` follows the last release; move it back by
re-running the promotion with the previous version if users pull it.

Sources: [working with the container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry),
[publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images),
[docker/build-push-action](https://github.com/docker/build-push-action),
[BuildKit attestations](https://docs.docker.com/build/metadata/attestations/),
[actions/attest](https://github.com/actions/attest),
[Renovate minimum release age](https://docs.renovatebot.com/key-concepts/minimum-release-age/).
Action majors checked on 2026-11-25: `setup-buildx-action` v4,
`metadata-action` v6, `build-push-action` v7, `attest` v4.

## Manual steps

- After the first push, set the package's visibility (Package settings): a new
  package is private by default; make it public for an open-source project.
- Check that the package is linked to the repository and inherits its access
  (it is when the `org.opencontainers.image.source` label is present).

## Audit checklist

- One build per commit; release and deploy jobs reuse the digest, never
  rebuild.
- The build job holds no write token; the push job builds nothing.
- Provenance and SBOM attached; the digest attested where the plan allows.
- Base images pinned by digest; Renovate updates them.
- Nothing deploys `latest`.
