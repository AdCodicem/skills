# repo

Brings a GitHub repository to one standard, whatever its language: a fixed
core every repository gets, plus modules chosen from what the repository
contains and from the user's answers. The same skill scaffolds an empty folder
and audits an existing repository; it always proposes a plan before writing.

- **Fixed core**: two layered rulesets (`main` for everyone;
  `main-human-gates`, with up-to-date branches, the `CodeQL` check and team
  approvals, that the bots' App is exempt from), squash merges with
  Conventional Commit titles, CI behind a single `gate` check, actions pinned
  by SHA and locked, actionlint and zizmor, semantic-release with approved,
  drafted, attested and immutable stable releases, trusted publishing,
  self-hosted Renovate merging non-major updates itself (Dependabot keeps the
  alerts), CodeQL advanced setup or Semgrep on private code, security policy
  and settings, `CLAUDE.md`.
- **Modules**: .NET, Node/TypeScript libraries, React applications, Python;
  Bicep or Pulumi infrastructure (always offered with a recommendation),
  Cloudflare through Wrangler; deployments to GitHub Pages, GHCR, Azure or an
  external platform; the self-hosted Renovate runner.
- **Adaptive**: detects the ecosystems, project kinds and what is already in
  place; adapts to the profile (personal or company, open source or private),
  a tier (minimal, standard, complete) and what the GitHub plan allows; resolves
  the latest versions of runtimes, actions, tools and modules at run time.

## Install

```text
/plugin marketplace add AdCodicem/skills
/plugin install repo@adcodicem
```

## Components

| Type | Name | Surfaces | Description |
| --- | --- | --- | --- |
| Skill | `/repo:init` | Claude Code, claude.ai | Scaffold or audit a repository: detection, plan, files, settings, verification |
| Hook | `UserPromptSubmit` | Claude Code, Cowork | For repository setup and audit requests (CI, releases, Renovate, rulesets, infrastructure as code), reminds Claude to load `/repo:init`, even for a request about one part |

On claude.ai the skill is named `repo-init`: download `repo-init.zip` from the
latest [`repo-v*` release](https://github.com/AdCodicem/skills/releases?q=repo-v&expanded=true)
and upload it under Customize > Skills. Without a shell, the skill inspects the
files you share and gives the settings as manual steps.

## Usage

- "Set up this repo" / "Initialise ce repo"
- "New TypeScript library repository, published to npm"
- "Audit this repository against my standards" / "Mets ce repo à niveau"
- "Set up the infrastructure and the deployment of this API on Azure"

What happens:

1. `scripts/detect.py` describes the repository (JSON).
2. The skill asks only what detection did not settle: profile, tier, project
   kinds, Bicep or Pulumi, deployment target, names.
3. `scripts/latest_versions.py` resolves the latest releases.
4. A gap list by area (add, change, ok); nothing is written before you agree.
5. The files, area by area, one commit each; then
   `latest_versions.py --write` pins every action by SHA and every version to
   its latest release.
6. `scripts/github_settings.py` plans the repository settings, then applies
   them with `--apply` once you agree.
7. Verification, and the list of manual steps (GitHub Apps, trusted
   publishers, cloud identities).

## Requirements

- Python 3.11 or later, standard library only, for the three scripts and the
  hook. On Windows, `python3` may be the Microsoft Store stub: the hook command
  tries `python3`, `python` then `py` through `sh` (Git Bash); without Git Bash
  it does nothing and the skill relies on its description alone.
- Network access for `latest_versions.py` (github.com, builds.dotnet.microsoft.com,
  nodejs.org, raw.githubusercontent.com, peps.python.org, registry.npmjs.org,
  api.nuget.org, pypi.org, mcr.microsoft.com); without it, the skill
  web-searches the versions.
- `git`, and `gh` authenticated with admin rights on the repository for
  `github_settings.py` and the workflow lockfile (`gh extension install
  github/gh-actions-lock`).
- Optional, for local verification: `actionlint`, `zizmor`, `pre-commit` or
  `prek`, and the toolchains of the ecosystems present.

Templates whose real name starts with a dot are stored with a `dot-` prefix
(`templates/core/dot-github/` for `.github/`), because claude.ai drops
dotfiles; the skill strips the prefix when copying.
