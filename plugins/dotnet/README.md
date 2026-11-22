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

- "Initialise ce repo" or "Set up a new .NET library repository with my standards"
- "Upgrade this .NET repository to my standard toolchain"

The skill lists what it will create or change and asks for confirmation before
writing files. It ends with the manual steps it cannot do for you (NuGet trusted
publisher, Codecov token, repository settings).

## Requirements

None: the skill only ships instructions and templates. The generated repository
needs the .NET SDK, Node.js (for semantic-release and Docusaurus) and Docker
(for Testcontainers).
