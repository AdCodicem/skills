# Releasing

Each plugin is versioned on its own (semver) by
[release-please](https://github.com/googleapis/release-please) in manifest mode.
There is nothing to run by hand.

## Flow

1. PRs merge into `main` with Conventional Commit titles (squash merge).
2. On every push to `main`, the Release workflow opens or updates one release PR
   per plugin with changes, for example `chore(main): release dotnet 1.1.0`. It
   bumps `version` in `plugins/<plugin>/.claude-plugin/plugin.json` and updates
   `plugins/<plugin>/CHANGELOG.md`.
3. Merging a release PR tags `<plugin>-v<version>` (for example `dotnet-v1.1.0`)
   and creates the GitHub release.
4. The same workflow then:
   - packages the plugin's portable skills and attaches `<plugin>-<skill>.zip`
     files to the release, for claude.ai uploads;
   - uploads skills that target `api` to the Claude API (`/v1/skills`): a new
     version when a custom skill with the same name exists, a new skill
     otherwise. Skipped when the `ANTHROPIC_API_KEY` secret is not set.
     Uploading runs no model and consumes no tokens.

Claude Code users get the new version when their marketplace refreshes: the
version in `plugin.json` is what Claude Code compares.

Evals are recommended before merging a release PR that changes skills, but not
required: see [testing](testing.md).

## Bumps

| Commit | 0.x plugin | 1.x+ plugin |
| --- | --- | --- |
| `fix:` | patch | patch |
| `feat:` | minor | minor |
| `feat!:` or `BREAKING CHANGE:` | minor | major |

New plugins start at 0.1.0; `dotnet` starts at 1.0.0. To force a version, add
`"release-as": "x.y.z"` to the package in `release-please-config.json`, then
remove it after the release.

## One-time GitHub setup

These settings cannot be committed. Apply them once in the repository settings:

- **General > Pull Requests**: allow squash merging only, with "Pull request
  title" as the default commit message; allow auto-merge; automatically delete
  head branches.
- **Rules > Rulesets** (or branch protection) on `main`: require a pull request
  and these status checks: `Validate plugins`, `Lint`, `Test (ubuntu-latest)`,
  `Test (windows-latest)`, `Package skills`, `Conventional Commit title`.
- **Actions > General**: allow GitHub Actions to create and approve pull
  requests (release-please opens PRs).
- **Secrets > Actions** (optional):
  - `RELEASE_PLEASE_TOKEN`: a fine-grained token with contents and pull
    requests write access. Without it, release PRs are opened with
    `GITHUB_TOKEN` and GitHub does not run CI on them, so required checks never
    report: merge them as an administrator or add the token.
  - `ANTHROPIC_API_KEY`: enables the automatic upload of `api` skills.
- **Security**: enable private vulnerability reporting, Dependabot alerts and
  Dependabot security updates.
