# .NET module

For repositories with a `*.slnx`, `*.sln` or `*.csproj`, or a request for a
.NET, C# or NuGet project. Templates: `templates/ecosystems/dotnet/`. For C#
code and SDK details beyond repository setup, the `dotnet` plugin's skills
(`csharp`, `tooling`, `migrate`) apply when installed.

## Versions

Resolved by `scripts/latest_versions.py`, never from memory:

- **SDK: the latest release** (11.0.x on 2026-11-25), pinned in `global.json`
  with `rollForward: latestFeature` (newer feature bands and patches of the same
  major apply; a new major never does) and
  `test.runner: Microsoft.Testing.Platform`.
- **Target framework**: a **library** targets the oldest .NET still supported,
  for the widest reach; an **application** targets the latest. .NET 10 (LTS)
  and .NET 11 (STS) both reach end of support on 2028-11-14, since STS releases
  get two years: a library targets `net10.0`, an application `net11.0`
  ([support policy](https://dotnet.microsoft.com/platform/support/policy/dotnet-core)).
  Fill `{{target-framework}}` in `Directory.Build.props` and `docfx.json`.
- No `LangVersion`: the C# version follows the target framework, so code never
  uses language features its runtime does not support.
- Package versions in `Directory.Packages.props` are the latest stable at setup
  time; Renovate keeps them current.

## Project layout

Create projects with the SDK's templates, then move their package versions to
`Directory.Packages.props` (central package management refuses versions in
project files, NU1008):

```bash
dotnet new sln --name {{project}}                 # .slnx, the default since SDK 10
dotnet new classlib --output src/{{project}}
dotnet new xunit --xunit-version v3 --output tests/{{project}}.Tests
dotnet sln add src/{{project}} tests/{{project}}.Tests
```

- `src/` for what ships, `tests/` for test projects (`<Name>.Tests`, one per
  source project, plus `<Name>.IntegrationTests` when there are any),
  `samples/` and `benchmarks/` at the complete tier.
- **One solution, `.slnx`**, at the root. An existing `.sln` migrates with
  `dotnet sln migrate`, and the old file is deleted
  ([.slnx default](https://learn.microsoft.com/dotnet/core/compatibility/sdk/10.0/dotnet-new-sln-slnx-default)).
- A packable project sets `<IsPackable>true</IsPackable>`; nothing else ships
  (the shared default is false).
- A **CLI tool** sets `<PackAsTool>true</PackAsTool>` and `<ToolCommandName>`,
  with no custom `.nuspec` (NETSDK1235 since SDK 11).

## Files

| File | Content |
| --- | --- |
| `global.json` | SDK pin, `rollForward: latestFeature`, MTP test runner |
| `Directory.Build.props` | Target, nullable, warnings as errors, `AnalysisLevel` `latest-recommended`, `EnforceCodeStyleInBuild`, XML docs, determinism, NuGet audit, version `0.0.0-dev` locally, package metadata, Source Link, symbols, package validation |
| `Directory.Packages.props` | Central package management with transitive pinning; test and benchmark packages |
| `nuget.config` | nuget.org only, over HTTPS (`<clear />` first) |
| `dot-config/dotnet-tools.json` | DocFX as a local tool, `rollForward: false` (complete tier) |
| `editorconfig`, `gitignore`, `gitattributes` | Fragments appended to the core files |
| `ci-jobs.yml`, `release-pack.yml`, `release-publish.yml`, `preview-inputs`, `renovate-rules.json`, `docs-api.yml` | Fragments merged into the core workflows and configuration |
| `docs/docfx/docfx.json`, `dot-github/scripts/docfx-postprocess.py` | API reference as Markdown for Docusaurus (complete tier) |
| `dot-github/workflows/benchmarks.yml`, `benchmarks/README.md`, `samples/README.md` | Complete tier |

## Build quality

- **No warnings, ever**: `TreatWarningsAsErrors` with the recommended analyzer
  set of the latest analysis level, and the code style of `.editorconfig`
  enforced by the build. A rule that is wrong for the codebase is suppressed
  where it fires (`#pragma warning disable` or `[SuppressMessage]`) with a
  justification, never by a global `NoWarn`.
- **Style drift must not break the build**: in an existing repository, a style
  rule stays at `:suggestion` until `dotnet format style --verify-no-changes`
  passes for it (the `editorconfig` fragment says which rules a new repository
  can start at `:warning`).
- CI checks whitespace with `dotnet format whitespace --folder
  --verify-no-changes` (no restore); style and analyzers are checked by the
  build itself.
- `ContinuousIntegrationBuild` on GitHub Actions normalizes paths for
  deterministic builds. **Source Link is built into the SDK** since .NET 8: no
  package reference
  ([Source Link in the SDK](https://learn.microsoft.com/dotnet/core/compatibility/sdk/8.0/source-link)).
- Symbols ship as `.snupkg` to nuget.org's symbol server.

## Tests

- **xUnit v3 on Microsoft.Testing.Platform** (MTP): `global.json` selects the
  MTP mode of `dotnet test`, and xUnit v3 runs on it natively, without
  `Microsoft.NET.Test.Sdk` ([dotnet test with MTP](https://learn.microsoft.com/dotnet/core/tools/dotnet-test-mtp),
  [xUnit v3 and MTP](https://xunit.net/docs/getting-started/v3/microsoft-testing-platform)).
  An existing repository on another framework keeps it, reported as **ok**;
  MSTest (`MSTest.Sdk`) and TUnit run on MTP too.
- Assertions with AwesomeAssertions (the open-source continuation of
  FluentAssertions), when the repository has no assertion library yet.
- **Coverage** with `Microsoft.Testing.Extensions.CodeCoverage`, in Cobertura
  (`dotnet test --coverage --coverage-output-format cobertura`); Coverlet's
  VSTest collector does not run on MTP
  ([code coverage on MTP](https://learn.microsoft.com/dotnet/core/testing/microsoft-testing-platform-code-coverage)).
  Every test project references the extension.
- **Integration tests with Testcontainers**: a real database or broker per test
  run, the same on a laptop and on `ubuntu-latest`, which has Docker. A test
  class that needs Docker skips when it is absent rather than failing.

## Dependencies and security

- **NuGet audit**: transitive (`NuGetAuditMode` `all`, the default for
  `net10.0` and later) at every severity. With warnings as errors, NU1901 to
  NU1904 fail the build: a vulnerable dependency blocks merges until Renovate's
  vulnerability pull request lands. An advisory that does not apply is
  suppressed alone, with a `NuGetAuditSuppress` item and a comment saying why
  ([auditing packages](https://learn.microsoft.com/nuget/concepts/auditing-packages)).
- **No NuGet lock files** by default: under `rollForward: latestFeature` the
  implicit framework references move with the SDK, so a locked restore breaks
  on SDK updates. Exact versions in `Directory.Packages.props`, the audit and
  Renovate's release-age delay cover the same risk.
- On SDK 11, a minimum package age for `dotnet package add` and `update`:
  `dotnet nuget update source nuget.org --min-publish-age-hours 72 --configfile nuget.config`
  ([minimum publish age](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk#configure-minimum-package-publication-age-from-the-cli)).
  Restore does not enforce it for fixed versions: it guards the moment a
  version is chosen.
- **Commit types**: Renovate gives every NuGet update `build(deps)`, except the
  packages that ship as dependencies of the repository's packages, which take
  `fix(deps)`. List them in `renovate-rules.json` (`{{shipped-package}}`) from
  the packed `.nuspec` files:

  ```bash
  dotnet pack --configuration Release --output /tmp/packages
  for p in /tmp/packages/*.nupkg; do unzip -p "$p" '*.nuspec'; done | grep -o '<dependency id="[^"]*"' | sort -u
  ```

  Remove the rule when nothing ships as a dependency.
- **CodeQL** analyzes C# with build mode `none` (no build in the workflow):
  keep the `csharp` entry of `codeql.yml`'s matrix
  ([security](../areas/security.md)). Turn on the SDK's security rules too:
  `<AnalysisModeSecurity>All</AnalysisModeSecurity>` in
  `Directory.Build.props`, so they fail the build with warnings as errors.

## Packaging and release

- The version comes from the release workflow only: `-p:Version=$VERSION` at
  pack time; local builds are `0.0.0-dev`.
- **Package validation** checks every pack for consistency across target
  frameworks, and the release pack for API compatibility with the last release
  (`ReleaseBaselineVersion`, passed by `release-pack.yml`). A package that was
  never released sets `<SkipPackageValidationBaseline>true</SkipPackageValidationBaseline>`
  until its first release. An intentional break is recorded in a
  `CompatibilitySuppressions.xml` (`dotnet pack -p:GenerateCompatibilitySuppressionFile=true`),
  reviewed in the pull request, and removed after the release
  ([baseline validation](https://learn.microsoft.com/dotnet/fundamentals/apicompat/package-validation/baseline-version-validator)).
- **Trusted publishing** to nuget.org: `NuGet/login` exchanges the run's OIDC
  token for an API key valid one hour; no key is stored
  ([trusted publishing](https://learn.microsoft.com/nuget/nuget-org/trusted-publishing)).
- **Attestations**: the core attests the `.nupkg` and `.snupkg` files;
  `release-publish.yml` also attests the assemblies inside them, because
  nuget.org re-signs each `.nupkg` (its digest changes) but leaves the
  assemblies as packed.
- A library or tool's package README is the repository's `README.md` by
  default (`PackageReadmeFile`); a `docs(readme)` commit releases a patch
  because it changes every package.

## Documentation (complete tier)

DocFX, as a local tool, generates the API reference from the XML documentation
comments as Markdown (`outputFormat: markdown`) into
`docs/website/docs/reference/api/`; `docfx-postprocess.py` converts DocFX's
HTML heading anchors to Docusaurus heading ids. The `docs-api.yml` steps run
before the Docusaurus build. Exclude projects that are not public API (source
generators, test helpers) in `docfx.json`.

## Manual steps

- **nuget.org trusted publishing policies** (account, Trusted Publishing): one
  for stable releases (repository owner `{{owner}}`, repository `{{repo}}`,
  workflow file `release.yml`, environment `release`) and, at the complete
  tier, one for previews (`preview.yml`, environment `preview`). Put the
  nuget.org profile name, not the email, in `release-publish.yml`
  (`{{nuget-user}}`). For a private repository, the policy stays temporarily
  active for 7 days until a first publish locks it to the repository.
- Optional: reserve the package ID prefix on nuget.org, so the packages show
  the verified mark and no one else can publish under the prefix.
- Enable two-factor authentication on the nuget.org account.

## Audit checklist

- `global.json` pins the latest SDK with `latestFeature` and the MTP runner.
- The target follows the library or application rule; no `LangVersion`
  override.
- Shared settings live in `Directory.Build.props`, versions in
  `Directory.Packages.props`; no version in a project file.
- `TreatWarningsAsErrors` on, no global `NoWarn` list, NuGet audit not
  weakened.
- One `.slnx` solution.
- Tests run on MTP with coverage; integration tests use Testcontainers.
- `EnablePackageValidation` on, with the baseline wired to the last release.
- Packages pushed with trusted publishing, never with a stored API key.
