# .NET repository standards

The full checklist behind the `repo-init` skill. SKILL.md holds the workflow;
read the sections below that apply before generating or changing the files
they cover. Section numbers (§1 to §14) are referenced from SKILL.md.

Template paths use the `dot-` prefix convention described in SKILL.md:
`templates/dot-github/` becomes `.github/` in the target repository.

## 1. Target framework & SDK

- Target the current **latest stable LTS** release of .NET (verified per
  step 2 of SKILL.md — do not hardcode from memory).
- `global.json` pins the SDK with `rollForward: latestMinor` so patch/minor
  SDK updates apply automatically without silently jumping major versions.
- `LangVersion` = `latest`, `Nullable` = `enable`, `ImplicitUsings` = `enable`,
  file-scoped namespaces, on every project via `Directory.Build.props` (see
  `templates/Directory.Build.props`) — don't repeat these per-`.csproj`.

## 2. Code style & quality

- `.editorconfig` at repo root (`templates/dot-editorconfig`) — naming
  conventions, `dotnet_diagnostic` severities, code-style-as-error in CI.
- `EnableNETAnalyzers` + `AnalysisLevel=latest` in `Directory.Build.props`.
- `dotnet format --verify-no-changes` runs in CI (not just locally) so style
  drift fails the build, not just a local warning.
- SonarCloud is opt-in per project (free for public repos) — ask whether
  this specific repo warrants it (small CLI tool: usually skip; library with
  real logic: usually worth it) rather than adding it everywhere by default.
- Code, comments, commit messages, docs: **American English** (en-US
  spelling), per AdCodicem's global preference — this applies inside every generated file, not just prose
  Claude writes in chat.

## 3. Tests

- Unit tests: **xUnit**, one test project per source project
  (`tests/Foo.Tests`), Coverlet for coverage, collected in CI.
- Integration tests touching SQL Server: **Testcontainers**
  (`Testcontainers.MsSql`) — spins up a real SQL Server container per test
  run, no shared state, works identically on a dev machine and in GitHub
  Actions (`ubuntu-latest` has Docker available natively).
- Both suites run in `ci.yml` on every push/PR to `main`.

## 4. Branching & commits

- **GitHub Flow**: `main` is always releasable, short-lived feature
  branches, PRs required (no direct pushes to `main`).
- **Conventional Commits** enforced on PR titles/commits in CI (a
  commitlint-style GitHub Action) — this is a hard dependency of the release
  pipeline below, not a style nicety: semantic-release parses commit types
  (`fix:`, `feat:`, `feat!:` / `BREAKING CHANGE:`) to compute the next
  version. A malformed commit silently produces no release.

## 5. Versioning & release — Conventional Commits + semantic-release

- `.releaserc.json` (`templates/dot-releaserc.json`): `commit-analyzer` →
  `release-notes-generator` → `changelog` (updates `CHANGELOG.md`) → `exec`
  (runs `dotnet pack` with the computed version, then `dotnet nuget push`) →
  `git` (commits the changelog + tags) → `github` (creates the GitHub
  Release).
- Runs from `release.yml`, triggered on push to `main` (i.e. after a PR
  merges), Node-based tooling (`npx semantic-release`) even though the repo
  is C# — this is normal, semantic-release doesn't touch your source, it
  only orchestrates version + changelog + publish.
- **Assumption to confirm on multi-package repos**: default is one unified
  version number for the whole repo — every package bumps together and gets
  published together, even if only one changed. Simpler, and fine for
  tightly-coupled packages (e.g. `Core` + `Core.Extensions`). If two packages
  in the same repo need to version independently, that needs
  `multi-semantic-release` instead — flag this explicitly rather than
  assuming, since it changes the release workflow shape.

## 6. Publishing — NuGet trusted publishing

- No stored `NUGET_API_KEY` secret. The workflow requests a GitHub OIDC
  token (`id-token: write` permission), exchanges it for a short-lived
  NuGet.org API key via the `NuGet/login` action, then `dotnet nuget push`
  as normal.
- **One-time manual step Claude cannot do for the user**: register the
  trusted publisher on nuget.org (package → Manage → Trusted Publishers →
  add the GitHub owner/repo/workflow filename). Always call this out
  explicitly as a manual step, not something the generated files handle.

## 7. Documentation — Docusaurus + generated API reference

- `docs/website`: standard Docusaurus site for hand-written guides/concepts.
- API reference is **generated, not hand-written**: DocFX's metadata step
  extracts triple-slash XML comments from the source into YAML, which is
  then converted to Markdown (DocFX's own experimental Markdown output, or
  the `DocFxMarkdownGen` community tool) and dropped into a `docs/api/`
  folder inside the Docusaurus source tree. Docusaurus then builds guides +
  generated reference as one site.
- `docs.yml` runs the DocFX metadata step, the Markdown conversion, then
  `npm run build` in `docs/website`, then deploys to GitHub Pages.
- `GenerateDocumentationFile=true` must be set in `Directory.Build.props` —
  without it there are no XML doc comments for DocFX to extract.

## 8. Dependency updates

- Dependabot (`templates/dot-github/dependabot.yml`), three ecosystems:
  `nuget` (source), `npm` (docs site), `github-actions` (workflow pins).
  Weekly, grouped by minor/patch to avoid PR noise.

## 9. Community & legal files

- `LICENSE`: MIT by default (`templates/LICENSE`) — ask for the copyright
  name/year to fill in, don't guess.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant),
  `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.md`,
  `.github/CODEOWNERS` (from `templates/dot-github/`) — this repo is open to contributions, so these are
  not optional the way they might be for a strictly-private repo.
- `README.md`: generated per-project from `templates/README.template.md`,
  not copied verbatim — quick start must get a new user to first success in
  under 5 minutes, badges (build status, NuGet version, license) at the top.

## 10. Security & supply-chain

- `SECURITY.md` — points to GitHub's private vulnerability reporting
  (Security tab → Report a vulnerability), not a public issue.
- **CodeQL** (`codeql.yml`): static analysis on push/PR to `main` + weekly
  schedule, results in the repo's Security tab.
- **OpenSSF Scorecard** (`scorecards.yml`): weekly supply-chain health scan,
  `publish_results: true` feeds the README badge
  (`api.scorecard.dev/projects/github.com/{owner}/{repo}/badge`).
- **Coverage** (Codecov): `ci.yml` uploads coverage via
  `codecov/codecov-action` — needs a `CODECOV_TOKEN` repo secret (see
  the manual steps in SKILL.md), don't rely on tokenless upload for the main branch.

## 11. Repo automation (bots)

- **Dependabot auto-merge** (`dependabot-auto-merge.yml`): merges
  Dependabot PRs automatically unless the bump is a major version — a major
  bump always needs a human look. Requires "Allow auto-merge" enabled in
  repo settings (manual step in SKILL.md) and a required status check so it can't
  merge a red build.
- **Stale bot** (`stale.yml`): marks issues/PRs inactive after 60 days,
  closes 14 days later unless labeled `pinned` (or `security` for issues).

## 12. Extra docs

- `ARCHITECTURE.md`: the "where do I start reading" map — project layout,
  main moving parts, links out to ADRs for the reasoning.
- `docs/adr/`: Architecture Decision Records (Nygard format) for
  significant, hard-to-reverse decisions — not every decision, only ones a
  future contributor would otherwise have to re-derive from git blame.
- `samples/`: minimal runnable examples referencing `src/` directly (not
  the published package), excluded from Pack/Publish.
- `benchmarks/`: BenchmarkDotNet projects. Deliberately **not** run on every
  CI push (noisy shared runners, slow) — manual `workflow_dispatch` only
  (`benchmarks.yml`), or run locally before a release.

## 13. Funding & community

- `.github/FUNDING.yml`: GitHub Sponsors — only works once GitHub Sponsors
  is actually enabled on the account (manual step in SKILL.md).
- **GitHub Discussions**: a repo setting Claude can't toggle from files
  (Settings → Features → Discussions) — flag it as a manual step when this
  section is applied. `.github/DISCUSSION_TEMPLATE/q-a.yml` is scaffolded
  ready for when it's on.

## 14. API compatibility validation

- `EnablePackageValidation=true` in `Directory.Build.props` fails the build
  on an accidental breaking API change.
- The baseline is **not** hardcoded — the release workflow passes
  `-p:PackageValidationBaselineVersion=${lastRelease.version}` from
  semantic-release itself, so it's always "compared against whatever we
  last actually published." Empty/no-op on the very first release.
- Consistent with the unified-versioning assumption in §5: since every
  package in a multi-package repo shares the same previous version number,
  one baseline value is correct for all of them.
