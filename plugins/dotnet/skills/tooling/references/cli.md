# .NET CLI, file-based apps, solutions and containers (.NET 10 and 11)

Items are GA unless marked otherwise. Sources:
[SDK and tooling in .NET 10](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk),
[SDK and tooling in .NET 11](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk).

## File-based apps (`dotnet run app.cs`)

**Version/status:** .NET 10 SDK GA (10.0.100); extended in 10.0.300 and 11.0.100 (GA).

**What:** Build, run, publish, and pack a single `.cs` file with no `.csproj`. The SDK generates a virtual project from `#:` directives at the top of the file. Native AOT publishing is on by default; `PackAsTool=true` is on by default.

**Directives:**

| Directive | Version | Purpose |
| --- | --- | --- |
| `#:package Name@Version` | 10.0.100 | NuGet reference. Version may be omitted only with CPM (`Directory.Packages.props`); `@*` = latest. |
| `#:sdk Name[@Version]` | 10.0.100 | Project SDK; default `Microsoft.NET.Sdk`. E.g. `#:sdk Microsoft.NET.Sdk.Web`, `#:sdk Aspire.AppHost.Sdk@13.0.2`. |
| `#:property Name=Value` | 10.0.100 | MSBuild property. Supports property functions, e.g. `$([MSBuild]::ValueOrDefault('$(LOG_LEVEL)', 'Information'))`. Quoted values with spaces only in .NET 11. |
| `#:project path` | 10.0.100 | ProjectReference to a `.csproj` or a directory containing one. |
| `#:include path/glob` | 10.0.300 and .NET 11 | Adds files: `*.cs`->Compile, `*.resx`->EmbeddedResource, `*.json`->None, `*.razor`->Content, `*.dll`->Reference (DLL mapping .NET 11 only). Globs disable build caching. Included `.cs` files cannot contain top-level statements. |
| `#:ref ./lib.cs` | .NET 11 | Builds another file-based app/library separately and adds a project reference to it (`#:property OutputType=Library` in the referenced file). |
| Item metadata `Name=Value` on `#:package`/`#:project`/`#:ref` | .NET 11 | E.g. `#:package System.CommandLine@2.0.1 Aliases=CommandLine`. |
| Shebang `#!/usr/bin/env -S dotnet --` | 10.0.100 | Direct execution on Unix; file must use LF and no BOM. Extensionless files supported. Fallback `#!/usr/bin/env dotnet` if `env -S` unavailable (then `dotnet` may eat `--help`). |

**Commands:**

```bash
dotnet run app.cs            # or: dotnet run --file app.cs ; or: dotnet app.cs
dotnet run app.cs -- arg1    # pass args
echo 'Console.WriteLine("hi");' | dotnet run -   # stdin
dotnet build app.cs          # output: <temp>/dotnet/runfile/<app>-<sha>/bin/<cfg>/
dotnet publish app.cs        # native AOT by default; output ./artifacts/<app>/
dotnet pack app.cs           # .NET tool package
dotnet project convert app.cs   # copies file + generates .csproj in ./<app>/; original untouched
dotnet restore app.cs
dotnet clean app.cs ; dotnet clean file-based-apps [--days 30]
dotnet package add System.CommandLine@2.0.1 --file app.cs   # also list/update/remove
dotnet nuget why app.cs System.CommandLine
dotnet user-secrets set "ApiKey" "v" --file app.cs
# .NET 11:
dotnet reference add --file app.cs ../Lib/Lib.csproj other.cs   # writes #:project / #:ref
dotnet format app.cs
```

**Example:**

```csharp
#!/usr/bin/env -S dotnet --
#:package Spectre.Console@0.49.1
#:property PublishAot=false
using Spectre.Console;
AnsiConsole.MarkupLine("[green]Hello[/]");
```

**Behavior notes:**

- If a project file exists in the CWD, `dotnet run file.cs` (without `--file`) runs the project and passes `file.cs` as an argument (back-compat). Use `--file` to be explicit.
- File-based apps honor `Directory.Build.props/.targets`, `Directory.Packages.props`, `nuget.config`, `global.json` in parent directories. Don't put file-based apps inside a `.csproj` directory cone.
- Launch profiles: flat `<app>.run.json` next to the file; `Properties/launchSettings.json` wins if both exist.
- Build cache keyed on file content, directives, SDK version, implicit build files. Parallel instances can race: `dotnet build app.cs` then `dotnet run app.cs --no-build`.
- Runtime paths available via `AppContext.GetData` (10.0.100).
- .NET 11: cached native-AOT CLI path reuses outputs for unchanged apps; with artifacts layout enabled, outputs go to repo `artifacts/` instead of per-user cache.
- .NET 11: `#:property` names may no longer contain `:`.
- Analyzers: CA2266 (.NET 10, warning) "file-based program entry point should start with `#!`" when the app spans multiple files; CA2267 (.NET 11, warning) "quote whitespace in file-based program directive values".

**Use:** scripts, utilities, repro samples, CI helpers, tools packaged with `dotnet pack`. **Avoid:** multi-project apps, anything needing complex MSBuild customization (convert with `dotnet project convert`), or living inside a project's directory tree.

Sources: <https://learn.microsoft.com/dotnet/core/sdk/file-based-apps> , <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk#file-based-apps-enhancements> , <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk>

## `dotnet tool exec` / `dnx` (one-shot tool execution)

**Version/status:** .NET 10 SDK GA. .NET 11: no extra approval prompt; `-y|--yes` option.

**What:** Downloads a tool package into the NuGet cache and runs it without global/local installation. Honors a nearby local tool manifest (`.config/dotnet-tools.json`) version. `dnx` is a shim script on PATH (`dnx`/`dnx.cmd`); `dotnet dnx` is a hidden alias.

```bash
dnx dotnetsay "Hello"
dotnet tool exec dotnetsay@2.1.0 -- "Hello"
dnx Some.Tool --yes --add-source ./nupkg -- --tool-arg
```

Options: `--allow-roll-forward`, `--add-source`, `--source` (replaces config incl. source mapping), `--configfile`, `--prerelease`, `--interactive`, `-y|--yes` (.NET 11).

**Gotchas:** In 10.0.302+ / 10.0.400+ / .NET 11, the `dnx` script bypasses `global.json` and uses the newest installed SDK; use `dotnet dnx` to honor `global.json`. `dnx.ps1` was removed at .NET 10 GA (use `dnx.cmd`).

**Use:** CI, ephemeral tool runs, MCP servers distributed as tools. **Avoid:** when you need a pinned, reproducible tool version without a manifest (use a local tool manifest + `dotnet tool restore`).

Sources: <https://learn.microsoft.com/dotnet/core/tools/dotnet-tool-exec> , <https://learn.microsoft.com/dotnet/core/compatibility/sdk/11/dnx-scripts-bypass-global-json>

## Platform-specific and `any`-RID .NET tools

**Version/status:** .NET 10 SDK GA.

**What:** A tool package can contain RID-specific variants (framework-dependent, self-contained, trimmed, native AOT). The CLI picks the right one at install/run time. Adding `any` produces a framework-dependent, platform-agnostic fallback package alongside the RID-specific ones and a top-level manifest package.

```xml
<PropertyGroup>
  <PackAsTool>true</PackAsTool>
  <RuntimeIdentifiers>linux-x64;linux-arm64;osx-arm64;win-x64;win-arm64;any</RuntimeIdentifiers>
  <!-- optional subset: <ToolPackageRuntimeIdentifiers>...</ToolPackageRuntimeIdentifiers> -->
</PropertyGroup>
```

Breaking: `dotnet pack` with `PackAsTool` now honors `RuntimeIdentifiers`. To keep old behavior: `<CreateRidSpecificToolPackages>false</CreateRidSpecificToolPackages><UseAppHost>false</UseAppHost>`. .NET 11 adds NETSDK1235 warning when `PackAsTool=true` is combined with a custom `NuspecFile`.

Note: the Learn sample uses `macos-arm64`; the documented RID for macOS is `osx-arm64` **[sample typo suspected, unverified]**.

Sources: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk#net-tools-enhancements> , <https://learn.microsoft.com/dotnet/core/compatibility/sdk/10.0/dotnet-tool-pack-publish>

## `.slnx` solution format, `dotnet sln migrate`, solution filters

**Version/status:** `.slnx` CLI support since SDK 9.0.200; **default for `dotnet new sln` in .NET 10** (GA). `dotnet sln migrate` available (doc'd under `dotnet sln`). `.slnf` creation/editing from CLI: .NET 11 (GA). Removing projects by name: .NET 10.

```bash
dotnet new sln                     # creates .slnx in .NET 10+
dotnet new sln --format sln        # legacy format
dotnet sln MySolution.sln migrate  # writes MySolution.slnx; fails if .slnx already exists
dotnet sln add src/App/App.csproj ; dotnet sln remove App   # by name (.NET 10)
# .NET 11
dotnet new slnf --parent-solution MySolution.slnx --name Tests
dotnet sln Tests.slnf add tests/Tests/Tests.csproj
```

```xml
<Solution>
  <Folder Name="/src/">
    <Project Path="src/App/App.csproj" />
  </Folder>
  <Project Path="test/App.Tests/App.Tests.csproj" />
</Solution>
```

**Use:** new repos; migrate when all tooling (VS 17.13+/VS 2026, Rider, CI) reads `.slnx`. **Avoid:** if a consumer tool still parses `.sln` text. `migrate` does not delete the old `.sln`: remove it yourself to avoid two solution files (which makes `dotnet build` in that dir ambiguous).

Sources: <https://learn.microsoft.com/dotnet/core/tools/dotnet-sln> , <https://learn.microsoft.com/dotnet/core/compatibility/sdk/10.0/dotnet-new-sln-slnx-default> , <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk#solution-filter-cli-support>

## CLI introspection: `--cli-schema`

**Version/status:** .NET 10 GA. .NET 11 serves `dotnet --cli-schema` from the native AOT path.

**What:** Emits JSON describing a command's arguments, options (with `helpName`, arity), and subcommands.

```bash
dotnet clean --cli-schema
dotnet package add --cli-schema
```

**Use:** agents/scripts discovering exact options for the installed SDK instead of guessing. Source: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk#cli-introspection-with---cli-schema>

## Noun-first command aliases

**Version/status:** .NET 10 GA. Verb-first forms still work; noun-first recommended.

| Noun-first | Alias for |
| --- | --- |
| `dotnet package add` | `dotnet add package` |
| `dotnet package list` | `dotnet list package` |
| `dotnet package remove` | `dotnet remove package` |
| `dotnet reference add` | `dotnet add reference` |
| `dotnet reference list` | `dotnet list reference` |
| `dotnet reference remove` | `dotnet remove reference` |

Also: `dotnet package update [--vulnerable]` (.NET 10 / NuGet 7.0), `dotnet package search`. .NET 11: `dotnet reference add/remove` fall back to the CWD project without `--project`; `--file app.cs` for file-based apps; `dotnet package add/update` honor `minPublishAgeHours`.
Note: `dotnet package list` now runs restore first (use `--no-restore`).

Source: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk#more-consistent-command-order>

## Native shell tab completion

**Version/status:** .NET 10 GA; .NET 11 improves fish (static completions).

```powershell
dotnet completions script pwsh | Out-String | Invoke-Expression   # in $PROFILE
```

Shells: `bash`, `fish`, `nushell`, `powershell`/`pwsh`, `zsh`. Source: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk#native-shell-tab-completion-scripts>

## Interactive-by-default and stderr discipline

- .NET 10: `--interactive` defaults to `true` when a user runs commands in an interactive terminal; `false` in CI or when output is redirected. Disable with `--interactive false`.
- .NET 10: first-run messages go to stderr; `dotnet watch` logs to stderr. .NET 11: "Using launch settings from..." goes to stderr. PowerShell users: use 7.2+.
- .NET 11: `Configuration` environment variable supplies default for `-c`.

Sources: <https://learn.microsoft.com/dotnet/core/compatibility/sdk/10.0/dotnet-cli-interactive> , <https://learn.microsoft.com/dotnet/core/compatibility/sdk/10.0/dotnet-cli-stderr-output>

## Container publishing

| Feature | Version | Example |
| --- | --- | --- |
| Console apps publish containers without `EnableSdkContainerSupport` | .NET 10 | `dotnet publish /t:PublishContainer` |
| `ContainerImageFormat` = `Docker` or `OCI` | .NET 10 | `<ContainerImageFormat>OCI</ContainerImageFormat>` |
| Multi-arch builds with Podman | .NET 11 | |
| Platform-native local runtime preferred (`wslc` on Windows, Apple `container` on macOS), Docker/Podman fallback | .NET 11 (breaking) | `-p:LocalRegistry=Docker` (values: `Docker`, `Podman`, `Wslc`, `MacOSContainer`) |
| Reproducible digests via `SOURCE_DATE_EPOCH` | .NET 11 | `-p:SOURCE_DATE_EPOCH="$(git log -1 --pretty=%ct)"` |
| Skip push when manifest already exists in registry (default on) | .NET 11 | `ContainerPushNoCache=true` to bypass |

Default .NET container images use Ubuntu (.NET 10). Sources: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk> , <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk#container-and-tooling-updates> , <https://learn.microsoft.com/dotnet/core/compatibility/sdk/11/native-local-container-runtimes>

## MSBuild: .NET tasks in .NET Framework MSBuild

**Version/status:** .NET 10 / VS 2026 (MSBuild 18). `msbuild.exe` and VS can run tasks built for .NET.

```xml
<UsingTask TaskName="MyTask" AssemblyFile="path\MyTask.dll" Runtime="NET" TaskFactory="TaskHostFactory"
           Condition="$(MSBuildRuntimeType) == 'Full'" />
<UsingTask TaskName="MyTask" AssemblyFile="path\MyTask.dll" Runtime="NET"
           Condition="$(MSBuildRuntimeType) == 'Core'" />
```

Host Objects not supported out-of-proc yet. Source: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/sdk#use-net-msbuild-tasks-with-net-framework-msbuild>

## .NET 11 CLI performance and workflow (GA)

- **Native AOT CLI host on by default** (`--version`, `--info`, `--help`, `<cmd> --help`, `--cli-schema`, `sln list/migrate/remove`, tool/external command launch skip ~600-700 ms managed startup). Opt out: `DOTNET_CLI_ENABLEAOT=false`.
- **MSBuild server on by default** (warm worker between invocations). Opt out: `DOTNET_CLI_USE_MSBUILD_SERVER=false` or `MSBUILDUSESERVER=0`. Relevant for CI/containers that expect build processes to exit; consider `dotnet build-server shutdown` **[command long-standing; interaction with new default not doc'd]**.
- Faster MSBuild wildcard matching (10-13% faster evaluation) in SDK 11.0.100 / VS 18.12.
- SDK installer dedup via symlinks on Linux/macOS (~18-26% smaller).
- `dotnet run -e KEY=VALUE` (also `RuntimeEnvironmentVariable` items); MSBuild properties expanded in launch-profile `commandLineArgs`.
- `dotnet watch`: Aspire integration, crash recovery relaunch, `--device` selection for MAUI.
- `dotnet format`: `--framework`; `.editorconfig` discovery limited to included files; accepts `app.cs`.
- `dotnet new install --prerelease` picks latest prerelease.
- Native AOT `UseOptimizedPublish` opt-in (default `false` in 11, default on in .NET 12 Preview 1).
- CLI telemetry moved to OpenTelemetry; opt-out unchanged (`DOTNET_CLI_TELEMETRY_OPTOUT`).
- Blog-only mentions (not verified in docs): `dotnet new mcpserver` template, preview `dotnetup` toolchain manager, ".NET Skills" for coding agents.

Source: <https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/sdk>
