# renovate-config

The shared [Renovate](https://docs.renovatebot.com/) preset of {{owner}}'s
repositories. A repository opts in with a `renovate.json` of its own:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "github>{{owner}}/renovate-config",
    "github>{{owner}}/renovate-config:groups-ecosystem"
  ]
}
```

The second line picks how updates are grouped, so they do not arrive as one
pull request per package:

| Preset | Groups |
| --- | --- |
| `groups-ecosystem` | non-major tooling updates, one pull request per ecosystem (GitHub Actions, pre-commit hooks, npm and Python dev dependencies, .NET packages) |
| `groups-weekly` | every non-major tooling update in one pull request, Monday morning |
| (none) | monorepo groups only, one pull request per package otherwise |

Majors, vulnerability fixes and shipped dependencies (`fix(deps)`) always keep
one pull request each.

What it sets, and why, is in the repo-init skill (`references/renovate.md` and
`references/areas/dependencies.md`): Renovate updates every ecosystem, GitHub
Actions included, and merges non-major updates itself after a three-day
release age, as an App the `main-human-gates` ruleset exempts; Dependabot keeps
the alerts only. Runtime dependencies take `fix(deps)`, everything else
`build(deps)`.

Change it with care: every repository follows it at its next run. A change
that could surprise them goes out as a new tag (`#v2`).
