# Contributing

Thank you for considering a contribution. This project follows GitHub Flow:
`main` is always releasable, work happens on short-lived branches, and every
change lands through a pull request that is squash-merged.

## Set up

```bash
git clone https://github.com/{{owner}}/{{repo}}.git
cd {{repo}}
{{setup commands of the ecosystem: restore, install, build}}
pre-commit install   # or: prek install
```

{{Prerequisites: the SDK or runtime version pinned in the repository, Docker
for the integration tests, ...}}

## Build and test

```bash
{{build, test and format commands, as CI runs them}}
```

## Pull request titles: Conventional Commits

Pull requests are squash-merged, and the title becomes the commit on `main`.
Releases and version numbers are computed from those commits, so the title
must follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>[optional scope]: <description>
```

| Type | Use for | Releases |
| --- | --- | --- |
| `feat` | a new feature | a minor version |
| `fix` | a bug fix | a patch |
| `perf` | a performance improvement | a patch |
| `build(pack)`, `docs(readme)` | package metadata, the package README | a patch |
| `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `style` | everything else | nothing |

A breaking change adds `!` after the type (`feat!: drop the synchronous API`)
or a `BREAKING CHANGE:` footer. While the version is 0.x it releases a minor
version, afterwards a major one. CI checks every pull request title.

## Pull requests

1. Branch from `main`.
2. Keep each pull request to one logical change.
3. Add or update tests for every behavior change.
4. Run the format and lint commands before pushing; CI runs them too.
5. Fill in the pull request template.

## Code style

`.editorconfig` and the ecosystem's analyzers or linters define the style;
the format commands above apply most of it.
