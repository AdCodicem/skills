# Branching and commits

[GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow)
on a protected `main`, as [trunk-based development](https://dora.dev/capabilities/trunk-based-development/)
recommends: short-lived branches, one pull request per change, `main` always
releasable.

## The rules

- **Two layered rulesets on the default branch**, applied by
  `scripts/github_settings.py`. GitHub combines every ruleset that targets a
  branch and applies the most restrictive version of each rule
  ([rule layering](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets#about-rule-layering)),
  so an actor exempt from one still meets the other:

  | Ruleset | Applies to | Rules |
  | --- | --- | --- |
  | `main` | everyone; the release App may bypass (`always`) to push the changelog commit and the tag | no deletion, no force push, linear history, changes only through pull requests, squash only, review threads resolved, the required checks of [ci](ci.md) (`gate`, `pr-title`, `workflows`, `pre-commit`) **not strict** |
  | `main-human-gates` | people; the bots' App (Renovate's) and the release App are **exempt** (`bypass_mode: exempt`: the rules are not evaluated for them) | the same checks **strict** (branch up to date with `main`), the `CodeQL` check where CodeQL is available ([security](security.md)), and for team profiles one approval from a code owner |

  People get the full bar; Renovate's updates merge as soon as the `main`
  checks pass, without being rebased and without anyone's review. Who may
  bypass when GitHub's auto-merge merges is not documented, which is why
  Renovate merges its pull requests itself
  ([dependencies](dependencies.md)). Organization-owned public repositories
  could use a merge queue instead of the "up to date" rule (it tests the merged
  result for everyone, bots included); personal repositories cannot.
- **Squash merges, with the pull request title and body as the commit**: the
  title must be a [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/),
  checked by `lint.yml`'s `pr-title` job, because it decides the next version
  ([release](release.md)). Commits inside a branch can be anything.
- **Branches are deleted after merge**, and the "Update branch" button is on.
- **Scopes**: free, but consistent; a monorepo uses the component's name
  (`feat(api): ...`).
- **Issues are referenced in the footer or body** (`Closes #12`), not in the
  subject, so changelog lines stay readable.

Why squash: the title is the one commit message a maintainer reviews, history
stays one line per change, and GitHub signs squash commits, so a "require
signed commits" rule stays possible (rebase merges are not signed).
Conventional Commits' own FAQ recommends it, and so does release-please.

## Signed commits

Optional: when the profile or the company asks for it, add the
`required_signatures` rule. Squash merges made in GitHub are signed by
GitHub; contributors sign their own commits with SSH keys (Git 2.34 or later)
only if they push directly, which the ruleset forbids anyway.

## Audit checklist

- The ruleset is active on the default branch, with the rules above.
- Merge commits and rebase merges are disabled; the squash commit uses the
  pull request title.
- The last 20 commits of `main` are Conventional Commits
  (`git log --format=%s -20`).
- No long-lived branch other than `main` (release branches only for
  maintained old majors).
