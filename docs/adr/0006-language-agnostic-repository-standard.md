# 6. A language-agnostic repository standard in its own plugin

Date: 2026-11-25

## Status

Accepted

## Context

`dotnet:repo-init` scaffolded .NET repositories only, and mixed what every
repository needs (branch protection, release model, dependency updates,
security) with what .NET needs (SDK pin, analyzers, NuGet). Repositories in
other languages (Node, React, Python) and infrastructure code (Bicep, Pulumi,
Cloudflare) needed the same core. The two mature repositories of the account,
AdCodicem.ValueObjects and AdCodicem.Pdf, had meanwhile refined practices worth
keeping (hybrid releases, credential isolation, drafted and attested releases)
and shown failures worth avoiding (dependency pull requests blocked by required
approvals, a trigger GitHub blocks by default from 2026-12-02).

## Decision

- A new thematic plugin, `repo`, holds one skill, `init` (`/repo:init`,
  packaged as `repo-init`), portable to claude.ai.
- The skill is a **fixed core** plus **modules**: one folder of references and
  templates per ecosystem (`dotnet`, `node`, `react`, `python`), per
  infrastructure tool (`bicep`, `pulumi`, `cloudflare`) and per deployment
  target. Modules plug into the core through fragments with fixed contracts
  (CI jobs behind a `gate` check, release `pack` and `publish` steps, Renovate
  rules, API reference steps). Adding an ecosystem is adding a folder.
- It adapts to a **profile** (personal or company, open source or private), a
  **tier** (minimal, standard, complete) and what the **GitHub plan** allows,
  and asks only what detection cannot settle.
- No version is written from memory: `scripts/latest_versions.py` resolves the
  latest runtimes, actions (pinned by SHA), tools and modules at run time and
  rewrites the pins.
- Repository settings are applied by `scripts/github_settings.py` through
  `gh api`, after the user approves the printed plan.
- `dotnet:repo-init` is removed, a breaking change of the `dotnet` plugin.

### Rejected alternatives

- **A core skill plus one skill per ecosystem plugin**: the core would depend
  on plugins that may not be installed, and claude.ai would need several zips.
- **Keeping the skill in the `dotnet` plugin**: a React repository would go
  through a .NET plugin.
- **GitLab support now**: doubles the templates for no current repository.

## Consequences

- One skill covers every repository of the account, and the standard evolves
  in one place.
- The skill is large (references and templates for every module); SKILL.md
  stays the workflow, and each reference is read only when its area applies.
- Templates name actions by tag and are pinned at generation time, so the
  templates themselves never need SHA updates; `latest_versions.py` run on the
  templates (its default root) reports any tool or module that fell behind.
