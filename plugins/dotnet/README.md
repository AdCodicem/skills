# dotnet

Skills for .NET development. The first one scaffolds a new personal open-source
.NET repository, or audits and upgrades an existing one, to a standard toolchain:
latest LTS SDK, analyzers and code style, xUnit and Testcontainers tests,
Conventional Commits with semantic-release, NuGet trusted publishing, Docusaurus
docs with a generated API reference, CodeQL, Scorecard and Dependabot.

## Install

```text
/plugin marketplace add AdCodicem/skills
/plugin install dotnet@adcodicem
```

## Components

| Type | Name | Surfaces | Description |
| --- | --- | --- | --- |
| Skill | `/dotnet:repo-init` | Claude Code, claude.ai | Scaffold or upgrade a personal open-source .NET repository |

On claude.ai the skill is named `dotnet-repo-init`: download
`dotnet-repo-init.zip` from the latest `dotnet-v*` GitHub release and upload it
under Customize > Skills.

## Usage

- "Set up a new .NET library repository with my standards" or "Initialise ce repo .NET"
- "Upgrade this C# repository to my standard toolchain"

It only triggers for .NET repositories: a generic "initialize this repo" in a
Node.js or Python project leaves it alone.

The skill lists what it will create or change and asks for confirmation before
writing files. It ends with the manual steps it cannot do for you (NuGet trusted
publisher, Codecov token, repository settings).

Before generating files, the skill runs `scripts/latest_versions.py`. It reports
the current .NET and Node.js LTS releases and flags every outdated pin in the
templates (SDK, target framework, `node-version`, GitHub Actions), so generated
files never start out of date. During an upgrade, `--root <repository>` checks
an existing repository the same way.

## Requirements

- Python 3 for `scripts/latest_versions.py` (standard library only). It needs
  network access to builds.dotnet.microsoft.com, nodejs.org and github.com;
  without it, the skill falls back to a web search.
- The generated repository needs the .NET SDK, Node.js (for semantic-release
  and Docusaurus) and Docker (for Testcontainers).

Templates whose real name starts with a dot are stored with a `dot-` prefix
(`templates/dot-github/` for `.github/`), because claude.ai drops dotfiles.
