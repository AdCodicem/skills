# AdCodicem skills

[![CI](https://github.com/AdCodicem/skills/actions/workflows/ci.yml/badge.svg)](https://github.com/AdCodicem/skills/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/AdCodicem/skills/badge)](https://scorecard.dev/viewer/?uri=github.com/AdCodicem/skills)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

My personal [Claude Code](https://code.claude.com) plugin marketplace: skills,
subagents, hooks and MCP servers, grouped into thematic plugins. Skills marked
as portable also work on claude.ai and through the Claude API.

## Install in Claude Code

```text
/plugin marketplace add AdCodicem/skills
/plugin install dotnet@adcodicem
```

On Claude Code 2.1.275 or later, one line does both:
`/plugin install dotnet --marketplace AdCodicem/skills`.

Third-party marketplaces do not auto-update by default. Turn it on under
`/plugin` > Marketplaces, or run `/plugin marketplace update adcodicem`.

## Plugins

| Plugin | Skills | Surfaces | Description |
| --- | --- | --- | --- |
| [repo](plugins/repo) | `/repo:init` | Claude Code, claude.ai | Scaffold or audit a GitHub repository in any language: CI, releases, dependency updates, security, documentation, infrastructure |
| [dotnet](plugins/dotnet) | `/dotnet:csharp`, `/dotnet:runtime-libraries`, `/dotnet:aspnetcore`, `/dotnet:efcore`, `/dotnet:tooling`, `/dotnet:migrate` | Claude Code | Write, review, modernize and upgrade code with C# 14/15 and .NET 10/11 |

Versions and changelogs: see each plugin's `CHANGELOG.md` and the
[releases](https://github.com/AdCodicem/skills/releases) (tags `<plugin>-v<version>`).

## Use on claude.ai or the Claude API

Outside Claude Code, skills are not namespaced, so a skill is named
`<plugin>-<skill>` (for example `repo-init`).

- **claude.ai**: download `<plugin>-<skill>.zip` from the plugin's latest
  release and upload it under Customize > Skills.
- **Claude API**: skills that target the API are uploaded to the workspace
  automatically on release. They also come as zips in the release, for
  `POST /v1/skills`.

## Repository layout

```text
.claude-plugin/marketplace.json   Marketplace catalog ("adcodicem")
plugins/<plugin>/                 Published plugins (skills/, agents/, hooks/, .mcp.json, evals/, tests/)
examples/hello-world/             Reference plugin, tested in CI but not published
templates/                        Scaffolding used by scripts/new_plugin.py and scripts/new_skill.py
scripts/                          Repository tooling: linting, packaging, API upload, checks
.claude/skills/                   Authoring skills available when working in this repository
docs/                             Conventions, testing, releasing, decision records
```

## Develop

```bash
pip install -r requirements-dev.txt
python scripts/check.py                  # everything CI runs
claude --plugin-dir plugins/dotnet       # try a plugin without installing it
```

When working in this repository with Claude Code, the authoring skills do the
heavy lifting: `/new-plugin`, `/new-skill`, `/validate` and `/run-evals`.

- [Conventions](docs/conventions.md): structure, naming, portability, scripts, hooks, MCP servers
- [Testing](docs/testing.md): the four test layers, none of them billed
- [Releasing](docs/releasing.md): release-please, packaging, one-time setup
- [Decision records](docs/adr)

## License

[MIT](LICENSE)
