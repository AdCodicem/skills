# renovate-config

The shared [Renovate](https://docs.renovatebot.com/) preset of {{owner}}'s
repositories. A repository opts in with a `renovate.json` of its own:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>{{owner}}/renovate-config"]
}
```

What it sets, and why, is in the repo-init skill (`references/renovate.md` and
`references/areas/dependencies.md`): Renovate updates every ecosystem, GitHub
Actions included, and merges non-major updates itself after a three-day
release age, as an App the `main-human-gates` ruleset exempts; Dependabot keeps
the alerts only. Runtime dependencies take `fix(deps)`, everything else
`build(deps)`.

Change it with care: every repository follows it at its next run. A change
that could surprise them goes out as a new tag (`#v2`).
