# Conventions

The rules for everything in `plugins/` and `examples/`. Rules marked **(lint)**
are enforced by `scripts/lint_skills.py`. Claude Code's own rules are checked by
`claude plugin validate --strict`. Both run in CI.

## Repository layout

```text
.claude-plugin/marketplace.json
plugins/<plugin>/
├── .claude-plugin/plugin.json     # manifest (the only file in .claude-plugin/)
├── README.md                      # required (lint)
├── CHANGELOG.md                   # written by release-please
├── skills/<skill>/SKILL.md        # + scripts/, references/, templates/, assets/
├── agents/<agent>.md
├── hooks/hooks.json               # + the hook scripts next to it
├── .mcp.json                      # + servers/<server>/ when the code lives here
├── evals/<case>/                  # claude plugin eval suites (recommended)
└── tests/                         # pytest tests for scripts and hooks
```

`commands/` is the older form of skills: use `skills/` for anything new.

## Plugins

- **Thematic**: one plugin per domain (`dotnet`, `github`...), grouping related
  skills, agents, hooks and MCP servers. Add to an existing plugin before
  creating a new one.
- **Name**: lowercase letters, digits and hyphens, matching the folder name
  **(lint)**. Keep it short: it prefixes every skill (`/dotnet:repo-init`) and
  every packaged skill name (`dotnet-repo-init`).
- **plugin.json**: `name`, `version`, `description` are required **(lint)**;
  also set `author`, `homepage`, `repository`, `license`, `keywords`.
- **Version**: owned by release-please, which bumps `plugin.json`. Never edit it
  by hand, and never set `version` in `marketplace.json` **(lint)**.
- **Registration**: every folder in `plugins/` is listed in `marketplace.json`
  **(lint)** and registered in `release-please-config.json` with the
  `plugin.json` extra-file **(lint)**. `scripts/new_plugin.py` does both.
- **README**: what the plugin does, a components table with surfaces, usage
  examples and requirements (tools the user needs installed).

## Skills

### Naming and frontmatter

- `name` matches the folder name, at most 64 characters, lowercase letters,
  digits and single hyphens **(lint)**.
- `description` is required, at most 1024 characters, without `<` or `>`
  **(lint)**. Write it in the third person, say what the skill does **and** when
  to use it, with the words users type. It is what decides whether the skill
  fires, so test it with evals.
- `metadata.surfaces` declares where the skill must work: a comma-separated
  subset of `claude-code`, `claude-ai`, `api` **(lint)**. Without it the skill is
  `claude-code` only.

```yaml
---
name: repo-init
description: Initialize ... Use when ...
metadata:
  surfaces: claude-code, claude-ai
---
```

Claude Code-only fields (`allowed-tools`, `disable-model-invocation`,
`argument-hint`, `context`, `model`...) are allowed. The packager keeps only
`name` and `description` in claude.ai and API zips, so a portable skill must not
depend on them to behave correctly.

### Body

- Imperative steps, the decisions that need the user, and how to verify the
  result.
- At most 500 lines **(lint)**. Move reference material to `references/*.md` and
  link it with relative links, which must resolve **(lint)**.
- Refer to bundled files with paths relative to the skill folder.

### Bundled files

| Folder | Content | Rules |
| --- | --- | --- |
| `scripts/` | Code the skill runs | Python 3.11, standard library only **(lint)** |
| `references/` | Documentation loaded on demand | Markdown |
| `templates/`, `assets/` | Files the skill copies or reads, never runs | Any format, exempt from runtime rules |

### Portable skills (`claude-ai`, `api`)

Portable skills run outside Claude Code, in a sandbox where only Python 3.11 and
Bash are guaranteed. The API sandbox has **no network access** and cannot install
packages; claude.ai network access depends on the user's settings.

- No `${CLAUDE_*}` variables outside `templates/` and `assets/`: only Claude
  Code substitutes them **(lint)**.
- No C#, JavaScript, TypeScript or PowerShell code outside `templates/` and
  `assets/` **(lint)**.
- The packaged name `<plugin>-<skill>` must stay within 64 characters and must
  not contain `claude` or `anthropic` **(lint)**.
- Total size under 30 MB **(lint)**.
- No dotfiles: they were observed to be dropped when a skill was synced from
  claude.ai (the linter warns). Store them with a `dot-` prefix
  (`templates/dot-github/`) and tell the skill to strip it when copying.
- `api` skills must work without network access.

## Subagents

- One Markdown file per agent in `agents/`, with `name` and `description` in
  frontmatter **(lint)**.
- Grant the fewest tools that do the job (`tools: Read, Grep, Glob` for a
  read-only agent).

## Hooks

- Declared in `hooks/hooks.json` (top-level `hooks` key **(lint)**), with the
  scripts next to it in `hooks/`.
- Scripts are Python 3.11 standard library only **(lint)**, called as
  `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py"`. Referenced files must exist
  **(lint)**. Bash is fine for a trivial one-liner.
- Read the event JSON from stdin. Exit `2` with a message on stderr to block;
  exit `0` otherwise. Never break the session on unexpected input: exit `0`.
- Keep them fast (set `timeout`) and test them by piping JSON events into the
  script (see `examples/hello-world/tests/`).
- On Windows, hooks run in Git Bash, or PowerShell when Git Bash is missing, and
  `python3` may not exist. Say so in the plugin README.
- Use `${CLAUDE_PLUGIN_DATA}` for state that must survive plugin updates;
  `${CLAUDE_PLUGIN_ROOT}` changes with every version.

## MCP servers

- Declared in `.mcp.json` at the plugin root.
- The language is chosen per server. Prefer, in order:
  1. a remote server (`http`), which also works in Cowork;
  2. a published package run with a pinned version (`npx`, `uvx`, `dnx`);
  3. code in `servers/<server>/`, exempt from the standard-library rule, with
     its own build and tests.
- List the runtime the server needs (Node.js, uv, .NET SDK) in the plugin README:
  Claude Code's native installer does not bring Node.js.
- Never commit secrets. Use `userConfig` in `plugin.json` or environment
  variables.

## Where components work

| Component | Claude Code | Cowork | claude.ai (org plugins) | Skill zip (claude.ai, API) |
| --- | --- | --- | --- | --- |
| Skills | Yes | Yes | Yes | Portable skills only |
| Subagents | Yes | Yes | No | No |
| Hooks | Yes | Yes | No | No |
| MCP, remote | Yes | Yes | No | No |
| MCP, local | Yes | Only on the user's computer | No | No |

Source: [plugin platform support](https://claude.com/docs/plugins/platform-support).

## Commits and pull requests

- [Conventional Commits](https://www.conventionalcommits.org), scoped with the
  plugin name: `feat(dotnet): add format skill`. release-please uses them to
  version each plugin: `fix` is a patch, `feat` a minor, `feat!` or
  `BREAKING CHANGE:` a major.
- Pull requests are squash-merged; CI checks that the PR title is a
  Conventional Commit.
- Everything in American English (en-US spelling).
