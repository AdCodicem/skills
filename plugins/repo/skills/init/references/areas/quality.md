# Quality

What every pull request proves before it can merge. The commands come from the
ecosystem files; this file says what must hold for all of them.

## The rules

- **Warnings are errors** in the build and the linters
  (`TreatWarningsAsErrors`, ESLint `--max-warnings 0`, ruff and mypy strict).
  A rule that is wrong for this codebase is disabled where it fires, with a
  written reason, never in a global list.
- **Formatting is checked, not discussed**: one formatter per language
  (`dotnet format`, Prettier, ruff format), run in CI in check mode and by the
  pre-commit hooks.
- **Tests run on every pull request**: unit tests always; integration tests
  that need Docker run in CI (GitHub-hosted Ubuntu runners have it) and skip,
  rather than fail, on a machine without it.
- **A library is tested on every runtime it supports** (the oldest supported
  through the latest), an application on the one it deploys.
- **Coverage is a signal, not a goal**: measured on every pull request, shown
  in the job summary, and sent to Codecov for public profiles at the standard
  tier (tokenless, `use_oidc: true`). Aim at full coverage of what each pull
  request changes; never test a private member through reflection; never
  delete code only because no test reaches it; a defensive branch stays.
- **Type checking is on** where the language has it: nullable reference types
  in .NET, `strict` TypeScript, mypy strict for Python.
- **Every optimization ships with its benchmark** (complete tier): benchmarks
  run on demand, never on shared runners for every pull request, where timings
  are noise.

## Codecov (standard tier, public profiles)

`codecov.yml` at the root:

```yaml
coverage:
  status:
    patch:
      default:
        target: 95%
    project:
      default:
        threshold: 0.5%
ignore:
  - "tests/**"
  - "samples/**"
  - "benchmarks/**"
```

The patch target is a floor; the aim stays full coverage of the patch. Link
the repository on codecov.io (manual step); no token is stored.

## Audit checklist

- The build fails on a warning.
- CI checks formatting.
- Tests run on every pull request, on every supported runtime for a library.
- No global suppression list.
