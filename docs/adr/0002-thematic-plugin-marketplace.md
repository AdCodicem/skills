# 2. A marketplace of thematic plugins

Date: 2026-11-22

## Status

Accepted

## Context

The repository will hold skills, subagents, hooks and MCP servers for Claude
Code. Claude Code distributes them as plugins listed in a marketplace. Options
were standalone skill folders, one plugin with everything, one plugin per skill,
or one plugin per theme.

## Decision

The repository is a single marketplace, `adcodicem`
(`.claude-plugin/marketplace.json`), listing **thematic** plugins under
`plugins/<theme>/`. A plugin groups related components of one domain, for
example `dotnet`. Skills are invoked as `/<plugin>:<skill>`.

A reference plugin, `examples/hello-world`, shows every component type. It is
tested in CI but not listed in the marketplace.

## Consequences

- Users install only the themes they want, and each theme can grow without
  adding entries to the marketplace.
- Plugin names prefix every skill, so they must stay short.
- Outside Claude Code skills are not namespaced, so packaged skills are renamed
  `<plugin>-<skill>` (see ADR 4).
