# 4. Portable skills: declared surfaces, Python standard library

Date: 2026-11-22

## Status

Accepted

## Context

Skills should work in Claude Code and, where it makes sense, on claude.ai and
through the Claude API. The runtimes differ: the API sandbox runs Python 3.11 and
Bash with no network access and no package installation; claude.ai's network
access depends on settings; Claude Code runs on the user's machine, where
Node.js, .NET and even `python3` are not guaranteed. claude.ai and the API only
document the `name` and `description` frontmatter fields, and do not namespace
skills.

## Decision

- A skill declares its surfaces in `metadata.surfaces` (`claude-code`,
  `claude-ai`, `api`). The default is `claude-code`.
- Skill and hook scripts use Python 3.11 with the standard library only. Bash is
  allowed for trivial one-liners. Other runtimes are allowed only in
  `templates/` and `assets/` (data, never executed), and in MCP server code under
  `servers/`, chosen per server.
- `scripts/package_skills.py` builds `<plugin>-<skill>.zip` for each portable
  skill, keeping only `name` and `description` in the frontmatter. Releases
  attach these zips and upload `api` skills to `/v1/skills`.
- `scripts/lint_skills.py` enforces the rules that make portability hold.

## Consequences

- No third-party Python packages in skills; some tasks need more code.
- The same skill source serves every surface, with no copy to keep in sync.
- claude.ai has no upload API: claude.ai skills are uploaded by hand from the
  release zips.
