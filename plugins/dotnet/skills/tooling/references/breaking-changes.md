# Breaking changes when upgrading the SDK and tooling

## Upgrading to .NET 10 SDK

| Change | Type | Mitigation |
| --- | --- | --- |
| `--interactive` defaults to true in interactive terminals | behavioral | `--interactive false` |
| First-run and some messages to stderr; `dotnet watch` logs to stderr | behavioral | PowerShell 7.2+; don't parse stderr as failure |
| `dotnet new sln` creates `.slnx` | behavioral | `--format sln` |
| `NuGetAuditMode=all` for net10.0+ (transitive vulnerabilities warn; breaks `TreatWarningsAsErrors`) | behavioral | `WarningsNotAsErrors` NU1901-1904; `NuGetAuditSuppress`; `NuGetAuditMode=direct`; fix with `dotnet package update --vulnerable` |
| NU1510 for direct references pruned by NuGet (net10.0+) | source | remove reference or condition it by TFM with `IsTargetFrameworkCompatible` |
| PrunePackageReference privatizes direct prunable refs (removed from nuspec deps for that TFM) | behavioral | verify package deps; remove unneeded refs |
| deps.json excludes packages with no runtime assets | source | `TrimDepsJsonLibrariesWithoutAssets=false` |
| PackageReference without version: NU1015 error (was NU1604) | behavioral | add `Version`, use CPM, or `Version="0.0.0"` for lowest; or `SdkAnalysisLevel` <= 9.0.300 |
| TFM `DefineConstants` (`NET9_0_OR_GREATER`, ...) not available at evaluation | behavioral | use `$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)','net9.0'))` in conditions |
| Tool pack honors `RuntimeIdentifiers` (RID-specific tool packages) | behavioral | `ToolPackageRuntimeIdentifiers`, or `CreateRidSpecificToolPackages=false` + `UseAppHost=false` |
| `ToolCommandName` only set when `PackAsTool=true` | source | set explicitly |
| `dotnet tool install --local` auto-creates manifest | behavioral | `--create-manifest-if-needed=false`; stop using `-d` |
| `dotnet package list` restores first | behavioral | `--no-restore` |
| HTTP sources: errors in `dotnet package list/search` | behavioral | HTTPS or `allowInsecureConnections` |
| Audit sources over HTTP: NU1302 (10.0.400+) | behavioral | HTTPS or `allowInsecureConnections="true"` |
| NuGet invalid package IDs error | behavioral | `NUGET_DISABLE_PACKAGEID_VALIDATION=true` |
| `dotnet nuget sign` SHA-1 fingerprint: NU3043 error | behavioral | SHA-256/384/512 fingerprint |
| `NUGET_ENABLE_ENHANCED_HTTP_RETRY` removed | behavioral | remove env var **[detail page not fetched]** |
| project.json not supported in restore | source | migrate to PackageReference |
| Workloads default to workload-set mode | behavioral | `dotnet workload config --update-mode manifests` |
| Code coverage `EnableDynamicNativeInstrumentation` defaults false | behavioral | static native instrumentation, or Microsoft.CodeCoverage 18.0.1 + runsettings `true` / `VSTEST_DISABLE_DYNAMICNATIVE_CODECOVERAGE_DEFAULT_SETTING=1` |
| MSBuild custom culture resource dirs opt-in (MSBuild 17.14) | behavioral | `EnableCustomCulture=true`, `CustomCultureExcludeDirectories` |
| `MSBUILDCUSTOMBUILDEVENTWARNING` escape hatch removed | behavioral | use `Extended*EventArgs` |
| Double quotes in `#:` directives are an error (10.0 GA) | source | move to Directory.Build.props or `dotnet project convert` (.NET 11 adds proper quoting) |
| `dnx.ps1` removed | source | use `dnx.cmd` |
| `dnx` scripts bypass global.json (10.0.302/10.0.400+) | behavioral | `dotnet dnx` |
| Template installs verify NuGet signatures (10.0.115 / 10.0.404) | behavioral | `--diagnostics`, `dotnet nuget verify`; get signed package |
| VSTest private artifacts dir in containers (10.0.404 / 10.0.115) | behavioral | `VSTEST_ARTIFACTS_BASE_DIRECTORY=/tmp` (official SDK images set it) |
| New CA warnings at AnalysisLevel 10 (CA2023, CA2266) | source (warnings) | `<AnalysisLevel>9</AnalysisLevel>` to defer |

Source index: <https://learn.microsoft.com/dotnet/core/compatibility/10#sdk-and-msbuild>

## Upgrading to .NET 11 SDK

| Change | Type | Mitigation |
| --- | --- | --- |
| Native AOT CLI command handling on by default | behavioral | `DOTNET_CLI_ENABLEAOT=false`; report differences |
| MSBuild server on by default | behavioral | `DOTNET_CLI_USE_MSBUILD_SERVER=false` or `MSBUILDUSESERVER=0` |
| Restore no longer searches global packages folder for "next best" version | source | reference versions that exist on sources (may now get NU1102 or a higher version) |
| Template package installs verify NuGet signatures (`--force` doesn't bypass) | behavioral | use signed packages; check `signatureValidationMode` |
| VSTest / Microsoft.NET.Test.Sdk drop Newtonsoft.Json dependency | binary/source | add explicit `<PackageReference Include="Newtonsoft.Json" .../>`; remove `ExcludeAssets=runtime` reliance; update test extensions |
| `dotnet test` (VSTest) needs writable private artifacts base dir in containers | behavioral | `VSTEST_ARTIFACTS_BASE_DIRECTORY=/tmp` (Linux) or `C:\Windows\Temp` (Nano Server) |
| Local container runtime prefers `wslc` / Apple `container` | behavioral | `-p:LocalRegistry=Docker` |
| NU5052 on pack for restricted package ID chars | behavioral | rename ID; `NoWarn` NU5052 or `SdkAnalysisLevel` < 11.0.100 |
| NU1703 for MonoAndroid assets (Android net11.0+) | source | update package; suppress; `SdkAnalysisLevel` < 11.0.100 |
| `mono` launch target not set for .NET Framework apps on Linux | behavioral | set `RunCommand`/`RunArguments` manually |
| Template engine packages drop netstandard2.0 (net9.0, net11.0, net472 only) | binary/source | retarget consumer |
| `dnx` scripts bypass global.json | behavioral | `dotnet dnx` |
| `#:property` names can't contain `:` | source | use valid MSBuild property name |
| NU1512 when `--locked-mode` + `--force-evaluate` | warning | pick one |
| NU1019 non-ASCII in TargetFramework becomes error | source | ASCII TFM aliases |
| New CA warning CA2267 at AnalysisLevel 11; `AnalysisLevel=latest` now really uses 11 rules | warnings | `<AnalysisLevel>10</AnalysisLevel>` to defer |
| NuGet locks dir moves to `~/.nuget/locks` on Linux | **future band SDK 11.0.200** | same SDK everywhere or common `NUGET_SCRATCH` |

Source index: <https://learn.microsoft.com/dotnet/core/compatibility/11#sdk-and-msbuild>
