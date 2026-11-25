# Documentation

What every repository documents, and, at the complete tier, the documentation
site.

## Every tier

- **README.md** (`templates/core/README.md`), written for the project, never
  copied as is. In order: name and one-sentence description, badges (CI,
  package version, license; Scorecard and coverage when present), what it does
  and for whom, install, a quick start that reaches a first success in five
  minutes, links to the documentation, contributing, license. The structure
  follows [standard-readme](https://github.com/RichardLitt/standard-readme/blob/main/spec.md)
  and [Make a README](https://www.makeareadme.com/).
- A package README for each published package when it differs from the
  repository's (NuGet `PackageReadmeFile`, npm `README.md` in the package, the
  PyPI long description). Changing it is a `docs(readme)` commit, which
  releases a patch.
- `CHANGELOG.md`, written by semantic-release only.

## Standard tier: decisions

`docs/adr/` with `adr-template.md` and `0001-record-architecture-decisions.md`
(`templates/core/docs/adr/`), in [Michael Nygard's format](https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions):
Status, Context, Decision, Consequences, plus a *Rejected alternatives*
section when there were real alternatives. Record only decisions a future
contributor would otherwise re-derive from history. A changed decision is
superseded by a new record, never edited.

## Complete tier: the site

- **Docusaurus**, in `docs/website/`, created with
  `npx create-docusaurus@latest website classic --typescript` at the latest
  version, then adjusted: the repository's name, URL and edit links, the blog
  removed, the default theme, and `markdown: { format: "detect" }` in
  `docusaurus.config.ts`, so generated `.md` pages are read as CommonMark
  rather than MDX (generated API references contain braces and HTML entities
  that MDX rejects).
- **[Diátaxis](https://diataxis.fr/)**: four sections under
  `docs/website/docs/`, one mode per page: `tutorials/`, `guides/` (how-to),
  `reference/` (with the generated API under `reference/api/`), `concepts/`
  (explanation). A page that mixes modes is split, and the parts link to each
  other.
- **The API reference is generated**, never written by hand, by the module of
  each ecosystem present, as Markdown into `docs/website/docs/reference/api/`
  (ignored by git): DocFX for .NET, TypeDoc with `typedoc-plugin-markdown` for
  TypeScript, griffe or pydoc-markdown for Python (see each ecosystem file). The
  module provides its `docs-api.yml` steps, which run before the Docusaurus
  build.
- **Versioned**: the release commits a snapshot of the docs for each stable
  line (`npm run docusaurus docs:version <line>`, a line being `0.<minor>`
  below 1.0 and the major after) through `@semantic-release/git`; `main` is
  served as the preview version.
- A tutorial's code is a sample under `samples/`, built in CI, so the tutorial
  never drifts from code that compiles.
- **Deployed to GitHub Pages** by `docs.yml` (`templates/release/docs.yml`),
  called by `release.yml` after a stable release and by `preview.yml` after a
  preview, with `concurrency: pages`. The site builds in CI on every pull
  request (a CI job), so a broken page never reaches `main`.
- `ARCHITECTURE.md` at the root (`templates/core/ARCHITECTURE.md`): the map of
  the code, where to start reading, the main moving parts, links to the ADRs.

## Audit checklist

- The README's quick start works as written.
- No hand-written API reference.
- Every documentation page builds in CI.
- The site's versions match the released lines.
