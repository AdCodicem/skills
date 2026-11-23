# NuGet, MSBuild and build settings (.NET 10 and 11)

## NuGet Audit (transitive by default)

**Version/status:** NuGetAudit since .NET 8; **`NuGetAuditMode=all` default for projects targeting net10.0+** (.NET 10 GA). Projects targeting <= net9.0 stay `direct`. Multi-targeting: if any TFM selects `all`, all TFMs use `all`.

| Property | Default | Values |
| --- | --- | --- |
| `NuGetAudit` | `true` | `true`/`false` |
| `NuGetAuditMode` | `all` (net10.0+), else `direct` | `direct`, `all` |
| `NuGetAuditLevel` | `low` | `low`, `moderate`, `high`, `critical` |
| `NuGetAuditSuppress` item | - | advisory URL |

Warnings NU1901-NU1904 (low..critical), NU1900 (source error), NU1905 (audit source lacks vulnerability data).

```xml
<!-- keep TreatWarningsAsErrors but don't let new advisories break builds -->
<WarningsNotAsErrors>$(WarningsNotAsErrors);NU1901;NU1902;NU1903;NU1904</WarningsNotAsErrors>
<ItemGroup><NuGetAuditSuppress Include="https://github.com/advisories/GHSA-xxxx" /></ItemGroup>
```

```xml
<!-- nuget.config: audit source without using nuget.org as a package source -->
<auditSources><clear /><add key="nuget.org" value="https://data.nuget.org/v3/index.json" /></auditSources>
```

Fix flow: `dotnet package update --vulnerable`; `dotnet nuget why <proj> <pkg>`; upgrade top-level package, else add direct reference or CPM transitive pinning. CI: `RestoreProjectsAuditedCount`/`RestoreProjectCount` outputs (9.0.200+) to assert audit ran (not with static graph restore). 10.0.400+: `http://` audit sources error NU1302 unless `allowInsecureConnections="true"`.

Sources: <https://learn.microsoft.com/nuget/concepts/auditing-packages> , <https://learn.microsoft.com/dotnet/core/compatibility/sdk/10.0/nugetaudit-transitive-packages>

## Package pruning (`PrunePackageReference`)

**Version/status:** opt-in in 9.0.200; **on by default for all TFMs of a project that targets net10.0+** with the .NET 10 SDK (GA). The SDK supplies the prune list from direct framework references.

**What:** Removes framework-provided packages from the restore graph. Transitive: pruned (not downloaded, not in outputs, removed from deps.json). Direct `PackageReference`: gets `PrivateAssets=all` + `IncludeAssets=none`, and NU1510 if the reference can be removed for every TFM. Matching `ProjectReference`: not pruned, NU1511.

```xml
<RestoreEnablePackagePruning>false</RestoreEnablePackagePruning>  <!-- opt out -->
<!-- multi-targeting: keep a package only where needed -->
<PackageReference Include="System.Text.Json" Version="8.0.5"
  Condition="!$([MSBuild]::IsTargetFrameworkCompatible('$(TargetFramework)', 'net8.0'))" />
```

Effects: faster restore, fewer audit false positives, smaller deps.json, lock-file diffs when regenerated. Note: the `SdkAnalysisLevel` table describes 10.0.100 pruning as "enabled by default for projects that target .NET 8+ or .NET Standard 2.0+", while what's-new/NuGet docs say "projects that target >= .NET 10"; interpretation: pruning turns on for every TFM (net8+/netstandard2.0+) of a project that includes a net10.0+ TFM **[wording conflict between docs]**.

Sources: <https://learn.microsoft.com/nuget/consume-packages/package-references-in-project-files#prunepackagereference> , <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk#pruning-of-framework-provided-package-references>

## Central Package Management (CPM)

**Version/status:** GA since NuGet 6.2 (not new in 10/11); relevant because file-based apps use it to omit `#:package` versions, and because .NET 10 makes version-less `PackageReference` without CPM an error (NU1015).

```xml
<!-- Directory.Packages.props (create with: dotnet new packagesprops) -->
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
    <CentralPackageTransitivePinningEnabled>true</CentralPackageTransitivePinningEnabled>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Serilog" Version="4.0.0" />
    <GlobalPackageReference Include="Nerdbank.GitVersioning" Version="3.5.109" />
  </ItemGroup>
</Project>
```

Projects: `<PackageReference Include="Serilog" />`; per-project override `VersionOverride="..."` (disable with `CentralPackageVersionOverrideEnabled=false`). Only the nearest `Directory.Packages.props` is imported; chain parents with `GetPathOfFileAbove`. NU1507 when multiple sources without package source mapping. Transitive pinning promotes pinned packages to nuspec dependencies when packing (be careful in libraries). Conditional `PackageVersion` per TFM allowed.

Source: <https://learn.microsoft.com/nuget/consume-packages/central-package-management>

## global.json (`sdk.paths`, `sdk.errorMessage`, `test.runner`)

**Version/status:** `paths`, `errorMessage`, `test.runner`: .NET 10 SDK GA.

```json
{
  "sdk": {
    "version": "10.0.100",
    "rollForward": "latestFeature",
    "allowPrerelease": false,
    "paths": [ ".dotnet", "$host$" ],
    "errorMessage": "Required .NET SDK not found. Run ./install.sh."
  },
  "msbuild-sdks": { "MSTest.Sdk": "4.1.0" },
  "test": { "runner": "Microsoft.Testing.Platform" }
}
```

- `paths`: searched in order, relative to global.json; `$host$` = location of the running `dotnet`. Affects only SDK commands (`dotnet run/build/...`), not `app.exe` / `dotnet app.dll`.
- Full pinning rules: [project-detection.md](project-detection.md).

Source: <https://learn.microsoft.com/dotnet/core/tools/global-json>

## Code analysis changes (CAxxxx defaults)

- `AnalysisLevel` default = TFM version, except the latest TFM the SDK supports uses `latest`. Lock with `<AnalysisLevel>10</AnalysisLevel>` (or `10-recommended`) when upgrading the SDK to avoid new warnings.
- New in .NET 10, enabled **as warning** by default: **CA2023** (invalid braces in logging message template), **CA2266** (file-based program entry point should start with `#!`). **CA1873** (avoid potentially expensive logging) enabled as suggestion.
- New in .NET 11, enabled as warning: **CA2267** (quote whitespace in file-based program directive values). CA1873 noise reduced (Information and below only; reasons in message). Bug fix: `AnalysisLevel=latest` was using .NET 9 rules; now .NET 11 rules.
- Code style (IDExxxx) still off on CLI builds unless `EnforceCodeStyleInBuild=true` + `.editorconfig` severities.
- `CodeAnalysisTreatWarningsAsErrors=false` keeps CA warnings non-fatal under `-warnaserror`.

Sources: <https://learn.microsoft.com/dotnet/fundamentals/code-analysis/overview> , <https://learn.microsoft.com/dotnet/core/project-sdk/msbuild-props#analysislevel> , <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk#code-analysis-and-warnings>

## `SdkAnalysisLevel` (newer SDK behaves like older for specific diagnostics)

**Version/status:** .NET 9+. Default = running SDK feature band. Values age out after 3 majors (11.0.100 honors down to 8.0.100).

| Level | Behavior gated |
| --- | --- |
| 9.0.100 | HTTP sources: NU1302 error instead of NU1803 |
| 10.0.100 | package pruning default; .NET 9 resolver with lock files; NU1015 for version-less PackageReference |
| 10.0.300 | duplicate effective TFMs via aliases; NU1019 for `/` `\` (error) and non-ASCII (warning) in TargetFramework |
| 11.0.100 | NU1703 (MonoAndroid assets); NU1019 non-ASCII becomes error; NU5052 (restricted package ID chars); NU1512 (locked-mode + force-evaluate) |

```xml
<SdkAnalysisLevel>10.0.100</SdkAnalysisLevel>
```

Source: <https://learn.microsoft.com/dotnet/core/project-sdk/msbuild-props#sdkanalysislevel>

## NuGet minimum publish age (.NET 11)

**Version/status:** .NET 11 GA. `minPublishAgeHours` source setting in nuget.config, settable from CLI. `dotnet package add/update` skip too-new versions when choosing automatically; explicit versions bypass. Restore doesn't enforce for fixed or transitive versions; floating references fail with NU1020 when a source has a nonzero minimum age. Supply-chain hardening; does not replace auditing.

```bash
dotnet nuget add source https://api.nuget.org/v3/index.json --name public --min-publish-age-hours 24 --configfile nuget.config
dotnet nuget update source public --min-publish-age-hours 48 --configfile nuget.config
```

Source: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk#configure-minimum-package-publication-age-from-the-cli>

## Security-oriented SDK/NuGet settings (checklist)

| Setting | Status | Snippet / note |
| --- | --- | --- |
| NuGetAudit (transitive) | default on (net10.0+ = `all`) | see NuGet Audit above |
| Package pruning | default on (net10.0+) | reduces scanner false positives |
| deps.json trims libs without runtime assets | .NET 10 default | `TrimDepsJsonLibrariesWithoutAssets=false` to revert |
| Lock files + locked mode | opt-in | `<RestorePackagesWithLockFile>true</RestorePackagesWithLockFile>`; CI `dotnet restore --locked-mode`; pin SDK with `rollForward: disable` (implicit refs vary by SDK). .NET 11: NU1512 if `--locked-mode` + `--force-evaluate`. |
| Package Source Mapping | opt-in | `packageSourceMapping` in nuget.config; resolves NU1507 under CPM. Doesn't apply to metadata queries (`dotnet package add`, `list --outdated`). |
| HTTPS-only sources | 9.0.100+: NU1302 error; .NET 10: `package list/search` HTTP warnings -> errors; 10.0.400: audit sources | `allowInsecureConnections="true"` per source to override |
| Signed package verification | Windows always; Linux default since .NET 8; macOS opt-in | `DOTNET_NUGET_SIGNATURE_VERIFICATION`; template installs verify signatures (11.0.100, 10.0.404/10.0.115, 9.0.321/9.0.124, 8.0.428/8.0.134) |
| `dotnet nuget sign` SHA-1 fingerprint | .NET 10: NU3043 error | use SHA-256 |
| Package ID validation | .NET 10 error on invalid IDs used in URLs; .NET 11 NU5052 on pack | `NUGET_DISABLE_PACKAGEID_VALIDATION=true` (escape hatch) |
| Minimum publish age | .NET 11 | see NuGet minimum publish age above |
| Source Link | built into SDK since .NET 8 | commit hash appended to `InformationalVersion` (`IncludeSourceRevisionInInformationalVersion=false` to disable) |
| Deterministic / CI paths | `Deterministic` default true **[default not re-verified in this pass]** | `<ContinuousIntegrationBuild Condition="'$(GITHUB_ACTIONS)'=='true'">true</ContinuousIntegrationBuild>` (also `TF_BUILD`) normalizes paths |
| Private VSTest session dir | SDK 11.0.100 and servicing bands | containers need `VSTEST_ARTIFACTS_BASE_DIRECTORY` (see [breaking-changes.md](breaking-changes.md)) |
| NuGet locks dir in `~/.nuget/locks` on Linux | **future band SDK 11.0.200** | mix of SDK versions restoring concurrently must share `NUGET_SCRATCH` |

## Performance-oriented settings (checklist)

- MSBuild server and AOT CLI host default in .NET 11 (see [cli.md](cli.md)).
- Package pruning: fewer packages restored.
- Artifacts output layout: `<UseArtifactsOutput>true</UseArtifactsOutput>` (since .NET 8); in .NET 11 also drives file-based app outputs and MTP test result paths **[property name from .NET 8 docs, not re-fetched]**.
- `dotnet test --no-dependencies`, `--test-modules` against prebuilt DLLs, `--maximum-failed-tests` (.NET 11).
- Lock files enable restore no-op checks and CI caching keyed on `packages.lock.json`.
- Evaluate properties without building: `dotnet msbuild -getProperty:X` (MSBuild 17.8+).
