# Contributing

Thanks for considering a contribution. This project follows a simple
GitHub Flow: `main` is always releasable, work happens on short-lived
branches, and changes land through pull requests.

## Setup

```bash
git clone https://github.com/{{owner}}/{{repo}}.git
cd {{repo}}
dotnet restore
dotnet build
dotnet test
```

Integration tests spin up a real SQL Server via [Testcontainers](https://dotnet.testcontainers.org/) —
Docker must be running locally, no other setup required.

## Commit messages — Conventional Commits

Releases and version numbers are generated automatically from commit
history, so commit messages must follow
[Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Common types: `feat` (new feature, bumps minor), `fix` (bug fix, bumps
patch), `docs`, `refactor`, `test`, `chore` (no release triggered). A
breaking change is marked with `!` after the type/scope, or a
`BREAKING CHANGE:` footer, and bumps the major version.

Examples:

```
feat(client): add retry policy to HttpClient factory
fix: correct null check in connection string parser
feat!: drop support for the synchronous API surface
```

A CI check validates this on every pull request — a malformed commit
message will block the merge.

## Pull requests

1. Branch from `main`.
2. Keep the PR focused — one logical change.
3. Add or update tests for anything behavioral.
4. `dotnet format` before pushing (CI enforces this too).
5. Open the PR; the template will guide you through the rest.

## Code style

Enforced by `.editorconfig` and the .NET analyzers — most of it is applied
automatically by `dotnet format`. See [SKILL.md](SKILL.md) in this repo's
tooling for the full rationale if you're curious.
