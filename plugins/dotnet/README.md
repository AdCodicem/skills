# dotnet

Skills for .NET development: make Claude write, review, modernize and upgrade
code with what C# 14 and 15, .NET 10 and 11, ASP.NET Core, EF Core and the SDK
added: new syntax where it reads better, safer defaults, faster APIs, and the
obsolete APIs and breaking changes to avoid. Every skill first detects the
project's target framework and C# version, and only uses what it supports.

Repository scaffolding (CI, releases, NuGet publishing, documentation) moved to
the language-agnostic [`repo`](../repo) plugin: `/repo:init`.

## Install

```text
/plugin marketplace add AdCodicem/skills
/plugin install dotnet@adcodicem
```

## Components

| Type | Name | Surfaces | Description |
| --- | --- | --- | --- |
| Skill | `/dotnet:csharp` | Claude Code | C# 14/15 features (and the C# 12/13 baseline) for the project's target; owns the target detection script |
| Skill | `/dotnet:runtime-libraries` | Claude Code | .NET 10/11 BCL and runtime: JSON, LINQ, collections, IO, processes, cryptography, performance guidance |
| Skill | `/dotnet:aspnetcore` | Claude Code | ASP.NET Core 10/11: Minimal APIs, validation, OpenAPI, auth, CSRF, observability (Blazor excluded) |
| Skill | `/dotnet:efcore` | Claude Code | EF Core 10/11: joins, named filters, complex types and JSON, ExecuteUpdate, vector and full-text search |
| Skill | `/dotnet:tooling` | Claude Code | SDK 10/11: file-based apps, `.slnx`, Microsoft.Testing.Platform, NuGet audit and pruning, CPM |
| Skill | `/dotnet:migrate` | Claude Code | Upgrade a solution to .NET 10 or 11 and work through the breaking changes |
| Agent | `modernization-auditor` | Claude Code | Read-only audit of a codebase: modernization, obsolete APIs, upgrade risks |
| Hook | `UserPromptSubmit` | Claude Code, Cowork | For .NET requests, reminds Claude which of the skills above to load, even for short snippets |

## Usage

### Modern C# and .NET

The skills trigger on their own while Claude writes or reviews C# code, and on
explicit requests:

- "Add a POST endpoint with validation to this API" (`aspnetcore`, `csharp`)
- "Review this class" or "Modernise ce code C#" (`csharp`)
- "Left join orders and customers in EF" (`efcore`)
- "Parse this untrusted JSON" or "Hash this password" (`runtime-libraries`)
- "Write a quick C# script to rename files" or "Migrate to slnx" (`tooling`)
- "Upgrade this solution to .NET 10" or "Migre la solution vers .NET 11" (`migrate`)
- "Audit this repository for modernization opportunities" (`modernization-auditor`)

How they behave:

- **Reliable triggering**: skill descriptions alone are often skipped for short
  "code only" requests, so a `UserPromptSubmit` hook adds a one-paragraph
  reminder naming the matching skills when the prompt mentions .NET or the
  session runs in a .NET repository. It adds nothing to other prompts.
- **Target first**: `skills/csharp/scripts/detect_target.py` reports each
  project's target frameworks, effective C# version, preview opt-ins, SDK pin,
  and ASP.NET Core, EF Core and test stacks (`--evaluate` asks MSBuild for the
  exact values). Features newer than the target are proposed as an upgrade,
  never used silently.
- **Minimal diffs**: modern constructs go in the code Claude writes; for
  surrounding code it only points out opportunities, unless you ask for a
  modernization.
- **Readability over novelty**: each "use this, not that" entry says when the
  new form helps and when to keep the old one.
- **No preview or experimental features** unless you ask (C# 15 memory safety,
  experimental crypto, EF Core 11 vector search).
- **Verification**: when the Microsoft Learn MCP server is connected, the skills
  check uncertain details there.

## Requirements

- Python 3 (standard library only) for `detect_target.py` and the hook. On
  Windows, `python3` may be the Microsoft Store stub: the skills fall back to
  `python`, and the hook command tries `python3`, `python` then `py` through
  `sh` (Git Bash). Without Git Bash the hook does nothing and the skills
  rely on their descriptions alone.
- The .NET SDK for `detect_target.py --evaluate` and to build and test the code.
- Optional: the [Microsoft Learn MCP server](https://github.com/MicrosoftDocs/mcp)
  to verify details that the bundled references do not cover.
