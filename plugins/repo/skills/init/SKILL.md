---
name: init
description: 'Scaffold a new GitHub repository, or audit and upgrade an existing one, to a current and secure standard in any language. A fixed core (ruleset on main, squash merges with Conventional Commit titles, CI behind one gate check, semantic-release with approved and attested stable releases, trusted publishing, Renovate merging updates past human-only gates, pinned actions, security policy) plus modules picked from what the repository holds: .NET, Node/TypeScript libraries, React applications, Python, Bicep or Pulumi infrastructure, Cloudflare Wrangler, deployments to GitHub Pages, GHCR or Azure. Adapts to the profile (personal or company, open source or private), a maturity tier and the GitHub plan, and resolves the latest versions. Use when asked to initialize, set up, standardize, audit or upgrade a repository, its CI, release pipeline, dependency updates or settings. Examples: "set up this repo", "new TypeScript library", "audit this repo against my standards", "initialise ce repo", "mets ce repo à niveau".'
metadata:
  surfaces: claude-code, claude-ai
---

# Repository init and audit

Brings a GitHub repository to one standard, whatever its language: a **fixed
core** every repository gets, plus **modules** chosen from what the repository
contains and from the answers of the user. The same skill scaffolds an empty
folder and audits an existing repository; in both cases it proposes a plan
before writing anything.

The standard and its sources are in the reference files. Read the file of an
area before generating or changing the files it covers; never write a version,
an action reference or a setting from memory.

## Conventions of this skill

- **Dotfiles are stored with a `dot-` prefix** (`templates/core/dot-github/`
  becomes `.github/`, `dot-editorconfig` becomes `.editorconfig`), because
  dotfiles are dropped when a skill is synced from claude.ai. Strip the prefix
  when copying, and never create a `dot-*` file in the target repository.
- **Placeholders** are written `{{name}}`, lowercase with hyphens: the core
  uses `{{owner}}`, `{{repo}}`, `{{project}}`, `{{package}}`, `{{year}}`,
  `{{copyright-holder}}`, `{{codeowner}}` and `{{renovate-bot}}`; each module
  lists its own (`{{nuget-user}}`, `{{python-min}}`, `{{node-oldest-lts}}`,
  `{{infra-dir}}`, `{{domain}}`, ...). Fill every one: a placeholder left in a
  generated file is a bug. A placeholder in prose (`{{One sentence: what this
  is}}`) is an instruction: replace it with that text. `${{ ... }}` in
  workflows and Renovate's templates (`{{depName}}`, `{{{newValue}}}`) are not
  placeholders.
- **Fragments** (`ci-jobs.yml`, `release-pack.yml`, `renovate-rules.json`,
  `gitignore`, ...) are pieces of a module that are merged into a core file, not
  copied: [references/areas/ci.md](references/areas/ci.md) and
  [references/areas/release.md](references/areas/release.md) say where each one
  goes.
- **Generators over templates for project code.** Create projects with the
  ecosystem's own generator at its latest version (`dotnet new`,
  `pnpm create vite`, `uv init`, `npx create-docusaurus@latest`,
  `pulumi new`), then apply the module's configuration files. Templates hold
  only what generators do not write.
- **Templates name actions by tag** (`actions/checkout@v7`); step 3 rewrites
  every reference to the latest release, pinned by full SHA with the version
  in a comment.
- Everything generated is in **American English**, unless the user says
  otherwise.

## Workflow

### 1. Detect

Run, from this skill's folder:

```bash
python3 scripts/detect.py --root <repository>
```

It prints JSON: the ecosystems and project kinds found (by marker files), the
standard files already present, the CI, release and dependency-bot
configuration in place, the GitHub remote, and, when `gh` is installed and
authenticated, the visibility, the owner type and the plan. Read it before
asking anything. Without a shell (claude.ai), inspect the files the user shares
and ask for the rest.

### 2. Settle the context

Ask only what detection did not settle, with the recommended option first and
the reason it is recommended. Batch the questions (an `AskUserQuestion` call
where it exists, four questions at most per call).

1. **Profile**: personal open source, personal private, company private,
   company open source. Detection suggests one from the visibility and owner
   type. See [references/profiles-and-tiers.md](references/profiles-and-tiers.md).
2. **Tier**: minimal, standard or complete. Recommend from the project's size
   and audience (same file).
3. **Project kinds and ecosystems**: library (published to a registry),
   application (deployed), CLI tool, infrastructure; one or several ecosystems
   in one repository, always with **one version** for the repository.
4. **Infrastructure**, when the project deploys to the cloud: **always ask
   Bicep or Pulumi**, with the recommendation and its reason from
   [references/iac/choosing.md](references/iac/choosing.md). For an open-source
   project, infrastructure lives in a separate **private operations
   repository**, never in the public one
   ([references/iac/ops-repo.md](references/iac/ops-repo.md)).
5. **Deployment target** for an application: GitHub Pages, a container image on
   GHCR, Azure, or an external platform
   ([references/deploy/model.md](references/deploy/model.md)).
6. **Names**: package or namespace root, copyright holder and year, code
   owner. Never guess them.

Then check what the **GitHub plan** allows for this visibility
([references/github-plans.md](references/github-plans.md)) and say upfront
what will be left out and why (for example: no ruleset on a private repository
of a personal Free account, no approval gate on a private repository below
Enterprise Cloud, no attestations on private repositories).

### 3. Resolve the latest versions

```bash
python3 scripts/latest_versions.py --root <repository>
```

It reports the current .NET, Node.js and Python releases, the latest release of
every action, tool and module the repository references, and flags what is
outdated. After the files are written (step 5), run it again with `--write`: it
pins every action to the full SHA of its latest release (`# vX.Y.Z` comment),
and updates the SDK, runtime, tool and module versions in place. Packages stay
on their major unless `--allow-major` is given: pass it for a new repository,
whose files were all just generated, never for an existing one (Renovate
proposes majors one by one there). If the script cannot reach the network,
web-search the same information and say so.

Version policy: the toolchain (SDK, Node.js, Python, tools, actions) is the
latest stable; the **target** of a library is the oldest version still
supported (widest reach), the target of an application is the latest stable.
Each ecosystem file states its exact rule.

### 4. Plan

Produce a gap list grouped by area, each item tagged **add**, **change** or
**ok**, with the module or profile rule it comes from. For an existing
repository, read the current files first and show what would change in each:
never overwrite a workflow, `.editorconfig`, `LICENSE` or release
configuration silently. Ask which areas to apply now and which to skip; a
wholesale rewrite of someone's CI is a hard-to-reverse change.

### 5. Apply

Apply area by area, in this order, one commit per area with a Conventional
Commit message (`chore: add repository hygiene files`, `ci: add the gate
workflow`, `build: add semantic-release`):

1. hygiene: [references/areas/hygiene.md](references/areas/hygiene.md)
2. governance: [references/areas/governance.md](references/areas/governance.md)
3. ecosystems: [references/ecosystems/](references/ecosystems/dotnet.md), one
   file per ecosystem present
4. quality and CI: [references/areas/quality.md](references/areas/quality.md),
   [references/areas/ci.md](references/areas/ci.md)
5. branching and commits: [references/areas/branching-and-commits.md](references/areas/branching-and-commits.md)
6. release: [references/areas/release.md](references/areas/release.md)
7. dependencies: [references/areas/dependencies.md](references/areas/dependencies.md),
   [references/renovate.md](references/renovate.md)
8. security: [references/areas/security.md](references/areas/security.md)
9. infrastructure and deployment, when chosen: [references/iac/](references/iac/choosing.md),
   [references/deploy/](references/deploy/model.md)
10. documentation: [references/areas/docs.md](references/areas/docs.md)
11. agent instructions: [references/areas/agents.md](references/areas/agents.md)

Then run `scripts/latest_versions.py --root <repository> --write` (with
`--allow-major` for a new repository), and generate the workflow lockfile
(`gh actions-lock`, see [references/areas/ci.md](references/areas/ci.md)).

### 6. Repository settings

Settings cannot be written as files. With `gh` installed and authenticated:

```bash
python3 scripts/github_settings.py --repo <owner>/<name> --profile <profile> [options]
```

It reads the current settings, prints what it would change (the `main` and
`main-human-gates` rulesets, merge options, private vulnerability reporting,
secret scanning and push protection, immutable releases, CodeQL default setup
off, workflow token permissions, SHA pinning policy, environments), skips what
the plan does not allow and says why. Show the plan to the user; run it again with `--apply` only
after they agree. Options and what each setting does:
[references/settings.md](references/settings.md). Without `gh`, give the user
the same list as manual steps.

### 7. Verify

Run what the repository can run locally, and report each item as passed,
failed with its output, or skipped with the reason:

- `actionlint` and `zizmor .github/workflows` (both are in the lint
  workflow; run them locally when installed);
- `pre-commit run --all-files` (or `prek run --all-files`);
- the build, test and format commands of each ecosystem file;
- `python3 scripts/latest_versions.py --root <repository>` exits 0;
- no placeholder and no `dot-` file left:
  `grep -rnE '(^|[^${])\{\{[^{}]+\}\}' --exclude='renovate.json*' --exclude-dir=node_modules .`
  and `find . -name 'dot-*' -not -path './node_modules/*'`.

### 8. Hand over the manual steps

List, in one place, every step only the user can do, with the setting's path
and what breaks without it: creating the release GitHub App and adding it to
the ruleset bypass, registering trusted publishers on the registries, the
Renovate runner's App, federated credentials in Azure, a Cloudflare API token,
enabling Sponsors. Each reference file ends with its manual steps.

## The fixed core

Every repository gets these, at every tier, unless the GitHub plan forbids it
(then say so):

| Area | In short | Reference |
| --- | --- | --- |
| Hygiene | `.editorconfig`, `.gitattributes`, `.gitignore`, pre-commit hooks, pinned toolchain | [hygiene](references/areas/hygiene.md) |
| Governance | LICENSE, README, CONTRIBUTING, SECURITY, CODEOWNERS | [governance](references/areas/governance.md) |
| Branching | GitHub Flow, two layered rulesets (`main` for everyone; `main-human-gates`, with up-to-date branches, the `CodeQL` check and team approvals, that the bots' App is exempt from), squash merges, Conventional Commit PR titles | [branching-and-commits](references/areas/branching-and-commits.md) |
| CI | One `gate` check over every job, least-privilege tokens, actions pinned by SHA and locked, actionlint and zizmor | [ci](references/areas/ci.md) |
| Quality | Warnings as errors, format check, tests on every pull request | [quality](references/areas/quality.md) |
| Release | Merging publishes nothing; stable releases on an approved dispatch, drafted, attested, then immutable; trusted publishing; 0.x until stable | [release](references/areas/release.md) |
| Dependencies | Renovate for every ecosystem, actions included, merging non-majors itself; Dependabot alerts only; release age; `fix(deps)` only for what ships | [dependencies](references/areas/dependencies.md) |
| Security | Security policy, private vulnerability reporting, secret scanning and push protection; CodeQL advanced setup with a required check, or Semgrep on private code without Code Security | [security](references/areas/security.md) |
| Agents | A `CLAUDE.md` with the repository's rules | [agents](references/areas/agents.md) |

The profile and the tier add the optional components (community files,
Scorecard, Codecov, documentation site, ADRs, previews, benchmarks): the
matrix is in [references/profiles-and-tiers.md](references/profiles-and-tiers.md).

## Modules

| Module | When | Reference | Templates |
| --- | --- | --- | --- |
| .NET | `*.sln`, `*.slnx`, `*.csproj` or a .NET request | [dotnet](references/ecosystems/dotnet.md) | `templates/ecosystems/dotnet/` |
| Node library | `package.json` of a published package, or a TypeScript/npm library request | [node](references/ecosystems/node.md) | `templates/ecosystems/node/` |
| React application | `react` in a private `package.json`, or a React app request | [react](references/ecosystems/react.md) | `templates/ecosystems/react/` |
| Python | `pyproject.toml`, `setup.py` or a Python request | [python](references/ecosystems/python.md) | `templates/ecosystems/python/` |
| Bicep | `*.bicep`, or chosen in step 2 | [bicep](references/iac/bicep.md) | `templates/iac/bicep/` |
| Pulumi | `Pulumi.yaml`, or chosen in step 2 | [pulumi](references/iac/pulumi.md) | `templates/iac/pulumi/` |
| Cloudflare | `wrangler.toml` or `wrangler.jsonc`, or a Cloudflare target | [cloudflare](references/iac/cloudflare.md) | `templates/iac/cloudflare/` |
| Deployment | An application with a target | [deploy](references/deploy/model.md) | `templates/deploy/` |
| Renovate runner | Once per account: the central repository that runs Renovate | [renovate](references/renovate.md) | `templates/renovate/` |

Terraform or OpenTofu found in a repository is kept and audited against the
generic rules (pinning, OIDC, plan on pull requests), never replaced
unprompted.

## Rules

- Inspect before proposing, propose before writing, and keep every change
  revertible (one commit per area).
- Never store a long-lived secret when OIDC exists: registries use trusted
  publishing, clouds use federated credentials. The exceptions (Cloudflare API
  token, the GitHub Apps' private keys) live in environment secrets, never in
  repository secrets.
- Never add a tool for an ecosystem the repository does not have.
- A setting the plan does not allow is reported, not worked around.
- Keep what works: an existing choice that meets the standard differently (a
  different test framework, Biome instead of ESLint) is reported as **ok**
  with a note, not replaced.

## Files in this skill

```text
scripts/
  detect.py                 Ecosystems, project kinds, files in place, GitHub context (JSON)
  latest_versions.py        Latest runtimes, actions, tools and modules; --write pins them
  github_settings.py        Plans and applies repository settings through gh api
references/
  profiles-and-tiers.md     Profiles, tiers, and what each adds
  github-plans.md           What each GitHub plan allows, and how the skill adapts
  settings.md               github_settings.py options, settings and manual steps
  renovate.md               Self-hosted Renovate: why, the runner, the shared preset
  areas/                    The fixed core, one file per area
  ecosystems/               dotnet.md, node.md, react.md, python.md
  iac/                      choosing.md, bicep.md, pulumi.md, cloudflare.md, ops-repo.md
  deploy/                   model.md, github-pages.md, ghcr.md, azure.md, external.md
templates/
  core/                     Files every repository gets (dot-github/, dot-editorconfig, ...)
  release/                  semantic-release configuration, release and preview workflows
  renovate/                 Per-repository config, shared preset, central runner
  ecosystems/<name>/        Configuration files and fragments of each ecosystem
  iac/<tool>/               Bicep, Pulumi and Wrangler files and workflows
  deploy/                   Deployment workflows per target
```
