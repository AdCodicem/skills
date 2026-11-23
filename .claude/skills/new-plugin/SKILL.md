---
name: new-plugin
description: Create a new plugin in this marketplace repository and register it (marketplace.json, release-please). Use when the user wants to add a plugin, start a new theme of skills, or package agents, hooks or MCP servers that do not fit an existing plugin.
---

# New plugin

Plugins in this repository are **thematic**: one plugin per domain (for example
`dotnet`, `github`), each grouping several related skills, agents, hooks or MCP
servers. Before creating a plugin, check `.claude-plugin/marketplace.json`: if an
existing plugin covers the domain, add a skill to it instead (`/new-skill`).

## Workflow

1. Agree on the details with the user:
   - **name**: short, lowercase, hyphenated, the domain rather than one task
     (`dotnet`, not `dotnet-repo-init`). Skills are invoked as
     `/<plugin>:<skill>` and packaged for claude.ai as `<plugin>-<skill>`, so
     keep it short and never use `claude` or `anthropic`.
   - **description**: one sentence on what the plugin is for.
   - **category** and a few **tags** for the marketplace listing.
2. Scaffold and register it:

   ```bash
   python scripts/new_plugin.py <name> --description "<sentence>" --category <category> --tag <tag>
   ```

   This creates `plugins/<name>/` from `templates/plugin/`, adds the
   marketplace entry and registers a release-please package starting at 0.1.0.
3. Add the first component. For a skill, follow `/new-skill`. For agents, hooks
   and MCP servers, follow `docs/conventions.md` and copy from
   `examples/hello-world/`.
4. Fill in `plugins/<name>/README.md`: components table, usage, requirements.
5. Run `/validate`.
6. Commit with a Conventional Commit scoped to the plugin, for example
   `feat(<name>): add <name> plugin`. Never edit `version` by hand:
   release-please owns it.
