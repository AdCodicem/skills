---
name: tooling
description: 'Use the .NET 10 and .NET 11 SDK, CLI, MSBuild, NuGet and test tooling well: file-based apps (dotnet run app.cs, #:package and other directives), dnx and dotnet tool exec, .slnx solutions, dotnet test on Microsoft.Testing.Platform with xUnit v3, MSTest, NUnit or TUnit, noun-first commands (dotnet package add), global.json options, transitive NuGet audit, package pruning, central package management, minimum package age, container publishing, plus the SDK breaking changes when upgrading. Use when creating or editing .csproj, Directory.Build.props, Directory.Packages.props, global.json, nuget.config or solution files, writing a C# script, running dotnet CLI commands, setting up or running tests, or when NuGet audit warnings, NU1510 or SDK upgrade problems appear. Example requests: "write a quick C# script to rename files", "migrate to slnx", "switch our tests to Microsoft.Testing.Platform", "corrige les warnings NuGetAudit", "crée un script C# exécutable". Not for MSBuild-free build systems.'
metadata:
  surfaces: claude-code
---

# .NET 10 and 11 SDK, CLI and tooling

Use the current SDK commands, project settings and test runners, with secure
NuGet defaults. .NET SDK 10 is the LTS line; SDK 11 (11.0.100) shipped with
.NET 11 on 2026-11-10.

## Before acting

1. **Detect the SDK and projects** (use `python` if `python3` is missing):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/csharp/scripts/detect_target.py" <path>
   ```

   It reports the SDK resolved for the folder, the `global.json` pin,
   roll-forward and test runner, every project's frameworks, CPM and audit
   settings, and test frameworks. Add `--evaluate` to get MSBuild's real values
   (`dotnet msbuild -getProperty`) when properties come from imports, conditions
   or custom TFM aliases.
2. **Check what the installed CLI supports** instead of guessing options:
   `dotnet <command> --cli-schema` prints the exact arguments and options as JSON
   (SDK 10+).
3. **Load the reference you need**:
   - [references/cli.md](references/cli.md): file-based apps, `dnx`, tools, `.slnx`, CLI changes, containers, .NET 11 CLI performance.
   - [references/testing.md](references/testing.md): `dotnet test` with Microsoft.Testing.Platform and per-framework setup.
   - [references/nuget-and-build.md](references/nuget-and-build.md): NuGet audit, pruning, CPM, `global.json`, analyzers, security and performance settings.
   - [references/breaking-changes.md](references/breaking-changes.md): upgrading to SDK 10 and 11.
   - [references/project-detection.md](references/project-detection.md): how MSBuild resolves TFM, `LangVersion` and the SDK.
4. **When a detail is not covered or looks uncertain**, check Microsoft Learn
   with the `microsoft_docs_search` / `microsoft_docs_fetch` tools if they are
   available.

## Rules

- **Change only what the task needs.** Mention outdated settings in files you
  touch; do not rewrite build files wholesale unless asked.
- **Ask before repository-wide changes**: switching the test runner, migrating
  to `.slnx`, enabling CPM or lock files, raising `AnalysisLevel`, changing the
  `global.json` pin. They affect every developer and CI.
- **Never weaken security settings to make a build pass**: do not disable
  `NuGetAudit`, suppress NU190x globally or allow HTTP sources. Fix the package,
  or suppress one advisory with `NuGetAuditSuppress` and say why.
- **Respect the pinned SDK.** If a feature needs a newer SDK than `global.json`
  allows, say so instead of using it.

## Use this, not that

| Instead of | Prefer | Needs |
| --- | --- | --- |
| A throwaway console project for a script | File-based app: `app.cs` with `#:package Name@1.2.3`, run with `dotnet run app.cs`; `dotnet project convert app.cs` when it grows | SDK 10 |
| Shell script calling a C# project on Unix | `#!/usr/bin/env -S dotnet --` shebang (LF, no BOM) + `chmod +x` | SDK 10 |
| `dotnet tool install -g` for a one-off run | `dnx <tool>` or `dotnet tool exec <tool>@<version>`; a local tool manifest for pinned versions | SDK 10 |
| `.sln` in new repositories | `.slnx` (default of `dotnet new sln`); `dotnet sln migrate`, then delete the old `.sln` | SDK 10 |
| `dotnet add package` / `dotnet add reference` | `dotnet package add` / `dotnet reference add` (verb-first still works) | SDK 10 |
| `dotnet list package --vulnerable` + manual edits | `dotnet package update --vulnerable`, `dotnet nuget why <proj> <pkg>` | SDK 10 |
| VSTest bridge (`TestingPlatformDotnetTestSupport`) | `"test": { "runner": "Microsoft.Testing.Platform" }` in `global.json` with an MTP-capable framework | SDK 10 |
| Versions repeated in every `.csproj` | Central Package Management (`Directory.Packages.props`) | NuGet 6.2 |
| Explicit references to framework-provided packages | Remove them (NU1510), or condition them by TFM | SDK 10 |
| `System.Linq.Async` / extension abstractions packages on `net11.0` | Nothing: they are in-box (NU1510) | .NET 10 / 11 |
| Floating `Version="*"` | Exact versions; on SDK 11, a `minPublishAgeHours` source setting against fresh malicious releases | SDK 11 |
| `Dockerfile` for a plain .NET app | `dotnet publish /t:PublishContainer` (console apps too) | SDK 10 |

## Security defaults to keep

- `NuGetAuditMode` is `all` (transitive) for `net10.0+`: keep it. With
  `TreatWarningsAsErrors`, add `NU1901;NU1902;NU1903;NU1904` to
  `WarningsNotAsErrors` only if new advisories must not break the build, and fix
  them promptly.
- HTTPS-only package sources; package source mapping when more than one feed
  (avoids dependency confusion, fixes NU1507).
- Lock files (`RestorePackagesWithLockFile`) and `dotnet restore --locked-mode`
  in CI for reproducible restores; pin the SDK when doing so.
- `ContinuousIntegrationBuild=true` on CI for deterministic, path-normalized
  builds; Source Link is built in.

## Testing

- Detect the framework first (the script reports it). xUnit v3, MSTest
  (MSTest.Sdk) and TUnit run natively on Microsoft.Testing.Platform; NUnit needs
  NUnit3TestAdapter 5+ with `EnableNUnitRunner`. Keep VSTest when a project
  relies on VSTest-only adapters, data collectors or the Coverlet collector.
- MTP-mode `dotnet test` uses `--project`, `--solution`, `--test-modules`;
  options after `--` go to the test apps. SDK 11 adds `--timeout`,
  `--maximum-failed-tests` and the `DOTNET_TEST_RUNNER` variable.
- New tests: follow the project's existing framework and style.

## Modes

- **Writing or editing build files**: apply the rules and tables above; keep
  `Directory.Build.props` for shared properties, `Directory.Packages.props` for
  versions.
- **Review**: report security settings first (audit, sources, floating
  versions), then deprecated settings and duplicated configuration.
- **Upgrade the SDK**: follow [references/breaking-changes.md](references/breaking-changes.md)
  and the `migrate` skill. Lock `AnalysisLevel` to the previous version first
  if new analyzer warnings must not block the upgrade.

## Verify

- `dotnet restore` with no new NU warnings, `dotnet build`, `dotnet test`.
- For file-based apps, `dotnet run app.cs` and, when it will be published,
  `dotnet publish app.cs` (NativeAOT by default: fix AOT warnings or set
  `#:property PublishAot=false`).
- After `.slnx` migration, `dotnet build` the new solution file and remove the
  old one so the folder holds a single solution.
