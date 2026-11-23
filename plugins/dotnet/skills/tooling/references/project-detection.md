# Project detection: target framework, C# version, SDK

How MSBuild decides the values that `detect_target.py` approximates.

## Default `LangVersion` per target framework (verified)

| Target | Default C# |
| --- | --- |
| net11.0 (.NET 11.x) | 15 |
| net10.0 | 14 |
| net9.0 | 13 |
| net8.0 | 12 |
| net7.0 | 11 |
| net6.0 | 10 |
| net5.0 | 9.0 |
| netcoreapp3.x | 8.0 |
| netcoreapp2.x | 7.3 |
| netstandard2.1 | 8.0 |
| netstandard2.0 / 1.x | 7.3 |
| .NET Framework (all) | 7.3 |

Exact MSBuild logic (Roslyn `Microsoft.CSharp.Core.targets`, main branch):

- `.NETCoreApp` >= 5.0: `_MaxSupportedLangVersion = 9 + (major - 5)` → i.e. **C# = TFM major + 4**.
- `.NETCoreApp` < 3.0 or non-netcore/non-netstandard2.1: 7.3; `.NETCoreApp` 3.x or netstandard2.1: 8.0.
- Capped at `_MaxAvailableLangVersion` (the compiler's max, `15.0` on current main). So a future TFM with an older compiler gets the compiler max.
- `<LangVersion Condition="'$(LangVersion)' == '' AND '$(_MaxSupportedLangVersion)' != ''">$(_MaxSupportedLangVersion)</LangVersion>`; also exposes `MaxSupportedLangVersion`.
- Preview TFMs with a matching preview language use the preview version.

Special values: `preview`, `latest` (latest released incl. minor; machine-dependent, discouraged), `latestMajor`/`default` (latest major the compiler supports, **ignores TFM**: not the same as omitting). Using a language version newer than the TFM default is unsupported. Ground truth from the compiler: put `#error version` in code → CS8304 shows compiler version and selected language version.

Sources: <https://learn.microsoft.com/dotnet/csharp/language-reference/language-versioning> , <https://learn.microsoft.com/dotnet/csharp/language-reference/configure-language-version> , <https://raw.githubusercontent.com/dotnet/roslyn/main/src/Compilers/Core/MSBuildTask/Microsoft.CSharp.Core.targets>

## `EnablePreviewFeatures`

`<EnablePreviewFeatures>true</EnablePreviewFeatures>` lets the project consume `[RequiresPreviewFeatures]` APIs (else CA2252 error), adds `[assembly: RequiresPreviewFeatures]` (unless `GenerateRequiresPreviewFeaturesAttribute=false`), and **also sets `LangVersion` to `Preview`**. `[Experimental]` APIs are separate: consent by suppressing their specific diagnostic ID in `NoWarn`.
Sources: <https://learn.microsoft.com/dotnet/core/project-sdk/msbuild-props#enablepreviewfeatures> , <https://learn.microsoft.com/dotnet/fundamentals/runtime-libraries/preview-apis>

## Where TargetFramework(s) / LangVersion / EnablePreviewFeatures can be set

Any MSBuild property can come from any of these; static file parsing is a heuristic, evaluation is authoritative.

| Location | Import point | Notes |
| --- | --- | --- |
| `*.csproj` | the project | Most common. `TargetFramework` (singular) wins: if set, `TargetFrameworks` is ignored. |
| `Directory.Build.props` | early, from `Microsoft.Common.props` (via `Sdk.props`) | Nearest file walking up from the project dir; **stops at the first one found** unless it imports the parent via `$([MSBuild]::GetPathOfFileAbove('Directory.Build.props', '$(MSBuildThisFileDirectory)../'))`. Overridable by csproj. Controlled by `ImportDirectoryBuildProps`/`DirectoryBuildPropsPath`. Case-sensitive filename on Linux. |
| `Directory.Build.targets` | late, from `Microsoft.Common.targets` after NuGet package targets | Overrides csproj values. Note: `LangVersion` default is computed in `Microsoft.CSharp.Core.targets`; a value set here may come after that **[ordering relative to CSharp.Core.targets not verified]**. |
| `Directory.Packages.props` | imported by the SDK when present (nearest file only) | Intended for CPM (`ManagePackageVersionsCentrally`, `PackageVersion`), but any property placed there is a real MSBuild property. CPM docs state `CentralPackageTransitivePinningEnabled` may live in project, `Directory.Packages.props`, or `Directory.Build.props`. |
| `Directory.Build.rsp` | CLI args (`dotnet build`, `msbuild.exe`) | e.g. `-p:LangVersion=preview` applies only to CLI builds. |
| Command line / env | `-p:Prop=Val` overrides project values; env vars are read as properties if not defined | |
| File-based apps | `#:property TargetFramework=net10.0`, `#:property LangVersion=preview` | plus inherited Directory.Build.* files. Default TFM when absent: the running SDK's TFM **[inferred, not stated in docs]**. |
| `.props` from NuGet packages / custom `<Import>` | varies | |

`TargetFramework` is an **alias**: the SDK parses it into `TargetFrameworkIdentifier` (`.NETCoreApp`, `.NETStandard`, `.NETFramework`), `TargetFrameworkVersion` (`v10.0`), `TargetFrameworkMoniker`, and `TargetPlatformIdentifier/Version` for OS-specific TFMs (`net10.0-windows`). From **SDK 10.0.300**, custom aliases are allowed (`<TargetFrameworks>linux;mac</TargetFrameworks>` both resolving to net10.0), so string-matching `netX.Y` is no longer sufficient: read `TargetFrameworkIdentifier` + `TargetFrameworkVersion` per inner build.

Sources: <https://learn.microsoft.com/visualstudio/msbuild/customize-by-directory> , <https://learn.microsoft.com/nuget/consume-packages/central-package-management> , <https://learn.microsoft.com/dotnet/core/project-sdk/msbuild-props#framework-properties>

## Authoritative evaluation commands (MSBuild 17.8+ / SDK 8.0.100+)

```bash
# single-targeted project: plain text output
dotnet msbuild MyProj.csproj -getProperty:TargetFramework
# multiple props -> JSON {"Properties":{...}}
dotnet msbuild MyProj.csproj -getProperty:TargetFramework,TargetFrameworks,LangVersion,MaxSupportedLangVersion,EnablePreviewFeatures,TargetFrameworkIdentifier,TargetFrameworkVersion,AnalysisLevel,Nullable,ManagePackageVersionsCentrally
# multi-targeted: outer build has empty TargetFramework; evaluate each inner build
dotnet msbuild MyProj.csproj -p:TargetFramework=net10.0 -getProperty:LangVersion,TargetFrameworkIdentifier,TargetFrameworkVersion
# file-based app (10.0.100+ supports build/msbuild verbs on .cs) [msbuild verb on .cs not verified; dotnet build app.cs -getProperty is the safer form]
dotnet build app.cs -getProperty:TargetFramework
```

- Without `-t`, values are post-evaluation (no build). Requires restore? No for property evaluation, but NuGet-package-provided props only appear after restore.
- Avoid combining `-f` with `-getProperty` on `dotnet build/publish` (8.0.200 duplicate-output regression, fixed after 8.0.202).
- `dotnet msbuild -pp:out.xml` shows the fully preprocessed import chain (to find where a property was set).
- `-getProperty` triggers the `.NET` evaluation including `Microsoft.CSharp.Core.targets`, so `LangVersion` comes back already defaulted from the TFM.

Sources: <https://learn.microsoft.com/visualstudio/msbuild/evaluate-items-and-properties> , <https://learn.microsoft.com/dotnet/core/compatibility/sdk/8.0/getx-duplicate-output>

## How global.json pins the SDK

- Lookup: the **muxer** (`dotnet` CLI) searches from the **current working directory** upward; the **MSBuild SDK resolver** searches from the solution directory (or project directory, or CWD) upward. These can differ when running from another directory.
- `sdk.version`: full version only (e.g. `10.0.100`); no `10`, `10.0`, `10.0.x`, wildcards, or ranges (invalid: "Version '10.0' is not valid for the 'sdk/version' value" in `dotnet --info`).
- `sdk.rollForward` (default `patch` when a version is set): `patch`, `feature`, `minor`, `major`, `latestPatch`, `latestFeature`, `latestMinor`, `latestMajor`, `disable`. Version format `x.y.znn` (z = feature band, nn = patch). Use `disable` with package lock files.
- No global.json, or no `version` → highest installed SDK (`latestMajor` semantics). Prerelease considered outside VS unless `allowPrerelease: false`.
- `allowPrerelease` default: `true` outside VS; inside VS depends on VS preview setting.
- `paths` (10.0.100+): ordered SDK search locations, relative to global.json; `$host$` = running dotnet's location. Only SDK commands.
- `errorMessage` (10.0.100+): custom message when no matching SDK.
- `msbuild-sdks`: pins MSBuild project SDK versions (e.g. `MSTest.Sdk`, `Microsoft.Build.Traversal`).
- `test.runner` (10.0.100+): `VSTest` (default) or `Microsoft.Testing.Platform`.
- Comments (`//`, `/* */`) are allowed: a detection script must use a JSON parser tolerant of comments (strip them before `json.loads`).
- Exceptions: `dnx` script ignores global.json (10.0.302+/11). `SdkAnalysisLevel` is the alternative when pinning isn't possible.
- Commands: `dotnet --version` (SDK selected for CWD, global.json-aware) **[standard behavior, not re-fetched]**, `dotnet --list-sdks`, `dotnet --info`, `dotnet new globaljson --sdk-version 10.0.100 --roll-forward latestFeature [--test-runner Microsoft.Testing.Platform]`.
- Visual Studio installs one SDK copy and removes the previous on upgrade; install standalone SDKs to keep a pinned version.

Source: <https://learn.microsoft.com/dotnet/core/tools/global-json>

## Suggested detection algorithm (static, Python stdlib)

1. Walk up from the target dir to find `global.json` (strip comments) → `sdk.version`, `rollForward`, `allowPrerelease`, `paths`, `test.runner`, `msbuild-sdks`.
2. Find project files (`*.csproj`, `*.fsproj`, `*.vbproj`), solutions (`*.slnx`, `*.sln`, `*.slnf`), file-based apps (`*.cs` with leading `#!` or `#:` lines).
3. For each project, build the property layer stack: nearest `Directory.Build.props` (follow explicit parent imports), nearest `Directory.Packages.props`, the project file, nearest `Directory.Build.targets` (overrides). Parse `PropertyGroup` children for `TargetFramework`, `TargetFrameworks`, `LangVersion`, `EnablePreviewFeatures`, `Nullable`, `AnalysisLevel`, `ManagePackageVersionsCentrally`, `TreatWarningsAsErrors`, `NuGetAuditMode`, `RestoreEnablePackagePruning`, `SdkAnalysisLevel`. Note but don't evaluate `Condition` attributes; flag `$(...)` values as unresolved.
4. Effective LangVersion: explicit `LangVersion` (or `preview` if `EnablePreviewFeatures=true`), else table/formula from the TFM (net N≥5 → N+4; netstandard2.1/netcoreapp3.x → 8.0; others → 7.3), capped by the compiler of the selected SDK (SDK 10 → 14, SDK 11 → 15).
5. If `dotnet` is available, confirm with `dotnet msbuild <proj> -getProperty:...` (per TFM for multi-targeting) and prefer those values.
6. Warn when: TFM uses a custom alias (10.0.300+), `LangVersion` is `latest`/`default`/`latestMajor`, LangVersion exceeds TFM default (unsupported), `global.json` pins an SDK older than required by the TFM (net10.0 needs SDK 10+, net11.0 needs SDK 11+), or MTP runner configured while test projects reference only VSTest adapters.
