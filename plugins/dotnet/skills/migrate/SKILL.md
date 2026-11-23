---
name: migrate
description: 'Upgrade a .NET solution to .NET 10 (LTS) or .NET 11 (STS) and C# 14 or 15: inventories target frameworks, SDK pin, packages and risky code, plans the upgrade, bumps TargetFramework, global.json and Microsoft packages, then works through the breaking changes of the runtime, C#, ASP.NET Core, EF Core and the SDK, and verifies with build and tests. Use when the user asks to upgrade, migrate or retarget a .NET project or solution, move off .NET 8 or 9 (out of support since November 2026), adopt .NET 10 or 11, or fix errors that appeared after an SDK or framework upgrade. Example requests: "upgrade this solution to .NET 10", "migrate from net8.0 to net11.0", "what breaks if we move to .NET 11?", "passe ce projet en .NET 10", "migre la solution vers .NET 11". Not for setting up repository tooling or CI standards (the repo-init skill does that) or for non-.NET projects.'
metadata:
  surfaces: claude-code
---

# Migrate to .NET 10 or .NET 11

Move a solution to a newer .NET in small, verifiable steps, without changing
behavior by accident. This skill orchestrates; the domain skills of this plugin
(`csharp`, `runtime-libraries`, `aspnetcore`, `efcore`, `tooling`) hold the
details.

## 1. Inventory

1. Run the detection script on the solution root (use `python` if `python3` is
   missing), with `--evaluate` when the SDK is installed:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/csharp/scripts/detect_target.py" <path> --evaluate
   ```

2. Record: current target frameworks (multi-targeting included), SDK pin and
   roll-forward, explicit `LangVersion`, stacks (ASP.NET Core, EF Core and its
   provider, Aspire, test frameworks), CPM, `TreatWarningsAsErrors`,
   `PublishAot`.
3. Check the installed SDKs (`dotnet --list-sdks`). Building `net10.0` needs SDK
   10+, `net11.0` needs SDK 11+. If missing, tell the user which SDK to install;
   do not install it yourself.
4. Make sure the working tree is clean and the current build and tests pass, so
   new failures are attributable to the upgrade. If they do not pass, report it
   and ask before going on.

## 2. Choose the target with the user

- **.NET 10 (LTS, supported to November 2028)**: the default for production
  apps and libraries.
- **.NET 11 (STS, supported to November 2028)**: when the user wants C# 15
  (unions, closed hierarchies) or a .NET 11 feature.
- **Libraries**: consider multi-targeting (`net10.0;net11.0`, plus
  `netstandard2.0` when consumers need it) rather than dropping older targets.
- Upgrading from .NET 8 to 11 crosses the breaking changes of 9, 10 and 11:
  read them all. For .NET 9 changes, use Microsoft Learn ("Breaking changes in
  .NET 9").

Present the plan before editing: target, files to change, packages to bump,
expected breaking changes found in the code, and what will be verified. Wait
for agreement.

## 3. Mechanical update

1. `global.json`: set `sdk.version` to the target's SDK band (for example
   `10.0.100` or `11.0.100`) with the existing `rollForward` policy, or
   `latestFeature` if none.
2. `TargetFramework(s)`: in the `.csproj` files or `Directory.Build.props`,
   wherever the detection reported them.
3. Remove an explicit `LangVersion` that equals the new default; keep or ask
   about others (`latest` makes builds depend on the installed SDK).
4. Bump `Microsoft.AspNetCore.*`, `Microsoft.Extensions.*`,
   `Microsoft.EntityFrameworkCore.*` and `System.*` packages to the target major
   (in `Directory.Packages.props` when CPM is on). Update third-party providers
   and tools that must match (Npgsql EF provider, `dotnet-ef`, test SDKs).
5. Remove packages that are now in-box: `System.Linq.Async` (use the BCL
   `System.Linq.AsyncEnumerable`), and on `net11.0` the nine
   `Microsoft.Extensions.*` abstractions packages flagged NU1510.
6. Container images and CI: update base image tags and the SDK used by CI.

## 4. Breaking changes

Work through the references for the stacks the project uses, searching the code
for each affected API before deciding it does not apply:

| Area | Reference |
| --- | --- |
| C# 14 (identifiers named `field`, `extension`, `scoped`, `partial`; span overload resolution) | `${CLAUDE_PLUGIN_ROOT}/skills/csharp/references/csharp-14.md` |
| C# 15 (`union`, `closed`, `with` inside collection expressions, span ref-safety) | `${CLAUDE_PLUGIN_ROOT}/skills/csharp/references/csharp-15.md` |
| Runtime and libraries, SYSLIB obsoletions | `${CLAUDE_PLUGIN_ROOT}/skills/runtime-libraries/references/breaking-changes.md` |
| ASP.NET Core | `${CLAUDE_PLUGIN_ROOT}/skills/aspnetcore/references/breaking-changes.md` |
| EF Core and its providers | `${CLAUDE_PLUGIN_ROOT}/skills/efcore/references/breaking-changes.md` |
| SDK, NuGet, MSBuild, tests | `${CLAUDE_PLUGIN_ROOT}/skills/tooling/references/breaking-changes.md` |

The changes that most often bite:

- **To .NET 10**: transitive NuGet audit warnings (NU1901-1904) breaking
  `TreatWarningsAsErrors` builds; NU1510 for pruned packages; `System.Linq.Async`
  conflicts; C# 14 span overload changes (ambiguous calls, expression trees with
  `array.Contains`); cookie-authenticated APIs answering 401/403 instead of
  redirecting; OpenAPI 3.1 and Microsoft.OpenApi 2.0 transformer changes; EF Core
  parameterized collections, complex type column names, `json` columns on SQL
  Server 2025 / Azure SQL; Microsoft.Data.Sqlite date/time handling; no default
  SIGTERM handler.
- **To .NET 11**: x86-64-v2 CPU baseline; numeric results (correctly rounded
  `decimal` conversions and `Math.Round`, saturating float-to-small-integer
  casts); automatic CSRF returning 400 on cross-origin form posts; OpenAPI 3.2
  and Microsoft.OpenApi 3.x; Kestrel HTTP strictness; removed
  `ConcurrencyLimiter` middleware; `IHost.RunAsync` throwing when a background
  service fails; SqlClient 7 Entra ID package split; EF Core vector columns no
  longer loaded; VSTest no longer bringing Newtonsoft.Json; MSBuild server on by
  default.

Fix each one in the way the reference recommends. Prefer a code fix over a
compatibility switch; when only a switch is practical, add it with a comment
naming the breaking change, and list it in the summary as follow-up work.

## 5. Verify

1. `dotnet restore`, `dotnet build` (zero new errors; review new warnings,
   especially SYSLIB, ASPDEPR, CS9258, NU190x, NU1510) and `dotnet test`.
2. EF Core: `dotnet ef migrations add UpgradeCheck` must produce an empty
   migration unless a schema change was intended (owned to complex types,
   `json` columns, named constraints); review and delete it if empty.
3. ASP.NET Core: run the app; check authentication flows (401 versus redirect),
   form posts from other origins, and the OpenAPI document.
4. Summarize: what changed, breaking changes handled and how, compatibility
   switches left in place, and modernization now possible (point to the domain
   skills; do not apply it as part of the upgrade unless asked).

## Large solutions

For many projects, upgrade leaf libraries first, then the projects that
reference them, building after each step. To inventory modernization
opportunities after the upgrade without filling this conversation, use the
`modernization-auditor` agent of this plugin.
