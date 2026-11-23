# Testing: dotnet test and Microsoft.Testing.Platform

## `dotnet test` with Microsoft.Testing.Platform (MTP)

**Version/status:** MTP mode of `dotnet test` introduced in .NET 10 SDK (GA). VSTest remains the **default** runner in both 10 and 11. Requires MTP 1.7+.

**Enable (repo-wide):**

```json
// global.json
{ "test": { "runner": "Microsoft.Testing.Platform" } }
```

.NET 11: `DOTNET_TEST_RUNNER=Microsoft.Testing.Platform|VSTest` (case-insensitive) overrides `global.json` per process; empty/unknown value falls back to `global.json`, then VSTest. `dotnet new globaljson --test-runner` exists (.NET 10).

**MTP-mode CLI shape (differs from VSTest mode):**

```bash
dotnet test                                   # discovers project/solution in CWD
dotnet test --project tests/A/A.csproj
dotnet test --solution My.slnx
dotnet test --test-modules "**/bin/**/*Tests.dll"   # .NET 11: '!' prefix excludes
dotnet test --report-trx                      # needs Microsoft.Testing.Extensions.TrxReport in each project
dotnet test -- --zero-tests-policy strict     # after '--' = forwarded to each test app
```

Migration from VSTest-mode MTP: remove `TestingPlatformDotnetTestSupport`, `TestingPlatformCaptureOutput`, `TestingPlatformShowTestsFailure`; `--` becomes optional; positional sln/proj/dll args become `--solution`/`--project`/`--test-modules`. Running MTP projects via VSTest mode (`TestingPlatformDotnetTestSupport=true`) is legacy and is removed in MTP v2 when used with the .NET 10 SDK. Projects that support only VSTest error out in MTP mode. Mixed-framework solutions: route framework-specific args via conditional `TestingPlatformCommandLineArguments` (e.g. `$(UsingMSTestSdk)`).

**.NET 11 additions (GA, MTP mode):** `--no-dependencies`; `--use-current-runtime|--ucr`; `--artifacts-path`; run-level `--timeout 90s` (exit 3) and `--maximum-failed-tests N` (exit 13) placed before `--`; `--results-directory-layout per-module`; artifacts layout -> `<ArtifactsPath>/test/<project>/<pivot>`; `--nologo` maps to `--no-banner`; `--tl/--tlp` forwarded to MSBuild; live in-flight test display; two-stage Ctrl+C; traversal projects (`dotnet test dirs.proj`); mobile device testing (`--device`); whole-run zero-test verdict (a single empty module no longer fails the run); experimental affected-tests (`DOTNET_CLI_ENABLE_AFFECTED_TESTS=1`, `--collect-test-map`, `--affected-tests`).

**Use:** new test projects (MSTest.Sdk, xUnit v3, TUnit, NUnit runner), CI speed, AOT tests. **Avoid:** solutions with frameworks/adapters that only support VSTest; tooling depending on `--logger`, runsettings data collectors, or Coverlet collector (Coverlet not supported on MTP per xunit.net).

Sources: <https://learn.microsoft.com/dotnet/core/testing/unit-testing-with-dotnet-test> , <https://learn.microsoft.com/dotnet/core/tools/dotnet-test> , <https://learn.microsoft.com/dotnet/core/tools/dotnet-test-mtp> , <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk#test-improvements>

## Test framework MTP support

| Framework | MTP support | How to enable | Notes |
| --- | --- | --- | --- |
| MSTest | MSTest 3.2+ runner | `<Project Sdk="MSTest.Sdk/4.x">` (MTP default; sets `EnableMSTestRunner` + `TestingPlatformDotnetTestSupport`) or `EnableMSTestRunner=true` + `OutputType=Exe` | `<UseVSTest>true</UseVSTest>` to switch MSTest.Sdk back. MTP 2.5 / MSTest 4.5 add UWP/WinUI 3 hosts. MSTest.Sdk can't replace `Microsoft.NET.Sdk.Web`. |
| NUnit | NUnit3TestAdapter 5.0+ | `<EnableNUnitRunner>true</EnableNUnitRunner>` + `OutputType=Exe` | .NET 11 template: `dotnet new nunit --test-runner Microsoft.Testing.Platform`. |
| xUnit.net v3 | built in | `<UseMicrosoftTestingPlatformRunner>true</UseMicrosoftTestingPlatformRunner>`; package variants from 3.2.0: `xunit.v3` (default), `xunit.v3.mtp-v1`, `xunit.v3.mtp-v2`, `xunit.v3.mtp-off` | 3.x defaults to MTP v1; 4.0.0+ defaults to MTP v2 and drops v1 (per xunit.net). .NET 11 template: `dotnet new xunit --xunit-version v3` (MTP by default; `--test-runner VSTest` to opt out). Filter flags differ (`--filter-class`, `--filter-trait`). |
| xUnit.net v2 | via adapter package | see xunit.net v2 MTP docs | |
| TUnit | MTP only | requires MTP mode `global.json` | no VSTest. |

MTP itself: supports .NET 8+, .NET Framework 4.6.2+, netstandard2.0. From MTP 2.4, Microsoft extension packages constrain `Microsoft.Testing.Platform` to the same major (`[2.4.0, 3.0.0)`): keep platform and extensions on one release line. Extensions auto-register via `Microsoft.Testing.Platform.MSBuild` unless `GenerateTestingPlatformEntryPoint=false`. Toggle extensions with `Enable<PackageIdWithoutDots>` (e.g. `EnableMicrosoftTestingExtensionsCrashDump`).

Sources: <https://learn.microsoft.com/dotnet/core/testing/microsoft-testing-platform-intro> , <https://learn.microsoft.com/dotnet/core/testing/unit-testing-mstest-sdk> , <https://learn.microsoft.com/dotnet/core/testing/unit-testing-nunit-runner-intro> , <https://xunit.net/docs/getting-started/v3/microsoft-testing-platform>
