# Python

For a repository with `pyproject.toml`, `setup.py` or `setup.cfg`, or a
request for a Python library, CLI or application. Templates:
`templates/ecosystems/python/`.

| Concern | Choice |
| --- | --- |
| Project, environments, lock, build | [uv](https://docs.astral.sh/uv/), backend `uv_build` (pure Python) |
| Lint and format | [ruff](https://docs.astral.sh/ruff/), configured in `pyproject.toml` |
| Type check | mypy, `strict = true` |
| Tests | pytest with pytest-cov |
| API reference | griffe2md, Markdown for Docusaurus |
| Publishing | PyPI trusted publishing with PEP 740 attestations, `pypa/gh-action-pypi-publish` |

An existing project on other tools (Poetry, Hatch, Black, pyright) that meets
the standard is reported **ok** with a note, not migrated unprompted.

## Versions

- **Development and tooling**: the latest stable CPython, written in
  `.python-version` (`dot-python-version`).
- **A library** sets `requires-python = ">=<oldest supported>"` and tests every
  supported version in CI. **An application** requires and tests the version
  of `.python-version` only.
- The supported versions are those with status `bugfix` or `security` in
  CPython's release cycle,
  [peps.python.org/api/release-cycle.json](https://peps.python.org/api/release-cycle.json).
  On 2026-11-25: 3.11 to 3.15, latest 3.15; 3.10 reached its end of life on
  2026-10-01. Fill `{{python-min}}` and `{{python-latest}}` from it, and the
  `python-test` matrix with every version in between.
- Raising `requires-python` is a breaking change for users on the dropped
  version: a `feat!` while it is a person's decision, never a bot's (the
  Renovate rules disable that update).

## Create the project

Generate it with uv at its latest version, then apply the fragments:

```bash
uv init --lib --python {{python-latest}} {{project}}   # a library or a CLI tool
uv init --app --package --python {{python-latest}} {{project}}  # an application
```

`--lib` writes a `src/` layout, `py.typed` and the `uv_build` backend.

Then, from `templates/ecosystems/python/`:

1. Merge `pyproject.toml` into the generated one:
   - `version = "0.0.0"`: the version lives in tags; `release-pack.yml` stamps
     it at build time with `uv version "$VERSION" --frozen`, which writes the
     value without relocking;
   - `requires-python`, the license as an SPDX expression with
     `license-files` (PEP 639), and the URLs;
   - the `dev` and `docs` dependency groups (PEP 735, locked in `uv.lock`;
     `uv sync` installs `dev` by default);
   - the ruff, mypy, pytest, coverage and griffe2md settings.
2. Copy `dot-python-version` to `.python-version`.
3. Append `gitignore` to the repository's `.gitignore`.
4. Run `uv lock`, then `uv sync`, and commit `uv.lock`.

A CLI tool declares its commands in `[project.scripts]`
(`{{project}} = "{{package}}.cli:main"`); the commented table in the fragment
shows it. A project in a subfolder of a multi-ecosystem repository keeps its
own `pyproject.toml` and `uv.lock`, and each fragment's jobs get a
`working-directory`.

## Quality

- **ruff** checks and formats (`ruff format --check`, `ruff check`). The rule
  set in the fragment (pycodestyle, Pyflakes, isort, bugbear, pyupgrade,
  simplify, pathlib, comprehensions, pytest style, Ruff's own) catches bugs
  without arguing about taste; `target-version` follows `requires-python`.
- **mypy in strict mode**, over `src` and `tests`, with `python_version` set
  to the oldest supported version. Why mypy:
  - Astral's [ty](https://docs.astral.sh/ty/) is still in beta: its 0.0.x
    versions promise no stable diagnostics between releases
    ([ty on PyPI](https://pypi.org/project/ty/),
    [announcement](https://astral.sh/blog/ty)). Revisit when ty 1.0 ships.
  - pyright needs a Node.js runtime (its PyPI wrapper downloads one); mypy is
    pure Python and installs from the locked `dev` group.
- **pytest** with `--strict-markers`, `--strict-config`, `xfail_strict` and
  warnings as errors; coverage with branches, reported in the terminal and as
  XML. No coverage threshold: coverage is a signal, read on each pull request.
- `twine check --strict` on the built distributions catches missing or broken
  metadata and a README PyPI cannot render.

## CI

Paste `ci-jobs.yml` into `ci.yml` and add its four job ids to `gate.needs`:

| Job | Does |
| --- | --- |
| `python-lint` | `uv sync --locked`, `ruff format --check`, `ruff check` |
| `python-typecheck` | `mypy` |
| `python-test` | pytest with coverage, one job per supported version; the Codecov upload (OIDC, no token) runs on the latest version only |
| `python-build` | `uv build --no-sources`, `twine check --strict` |

`--locked` fails when `uv.lock` is out of date with `pyproject.toml`, so a
dependency change without its lock never merges. `--no-sources` builds the
package as PyPI users will install it, without local path sources.
`astral-sh/setup-uv` publishes no floating major tag: templates name its full
latest version, which `latest_versions.py --write` pins by SHA.

Delete the Codecov step for profiles without Codecov
([profiles and tiers](../profiles-and-tiers.md)).

## Release

- `release-pack.yml` stamps the version and builds the wheel and sdist into
  `dist/pypi/`, with no credentials and no cache.
- **Previews need PEP 440.** PyPI normalizes the SemVer preview form
  `1.2.0-preview.7` to the release candidate `1.2.0rc7`, which sorts above
  alphas and betas and misstates what it is. The fragment maps it to the
  development release `1.2.0.dev7`
  ([PEP 440](https://peps.python.org/pep-0440/)). Users get previews with
  `pip install --pre`. A stable version is identical in both schemes, so
  semantic-release's version check holds.
- `release-publish.yml` runs `pypa/gh-action-pypi-publish` with
  `skip-existing: true`, so a rerun after a partial failure republishes nothing.
  It generates and uploads [PEP 740 attestations](https://docs.pypi.org/attestations/producing-attestations/)
  by default, through trusted publishing. Attestations are recorded in the
  public Sigstore log, which names the repository: from a private repository,
  set `attestations: false` if that name must stay private.
- `uv publish` also supports trusted publishing and uploads attestation files
  it finds, but does not generate them; the action stays the documented path.
- `preview-inputs` lists what ships: `src/`, `pyproject.toml`, `uv.lock`,
  `README.md`, `LICENSE`. Changing the README is a `docs(readme)` commit: it
  is the PyPI page, and releases a patch.

## Dependencies

Renovate's `pep621` manager reads `pyproject.toml` and updates `uv.lock`
([pep621 manager](https://docs.renovatebot.com/modules/manager/pep621/)).
Merge `renovate-rules.json` into the repository's `renovate.json`:

- `project.dependencies` and `project.optional-dependencies` (extras ship
  too) take `fix(deps)`;
- `requires-python` updates are disabled;
- dependency groups and `build-system.requires` keep the preset's
  `build(deps)`.

## Documentation (complete tier)

`docs-api.yml` runs before the Docusaurus build: griffe2md reads the source
statically, without importing it, and writes one Markdown page to
`docs/website/docs/reference/api/{{package}}.md`
([griffe2md](https://mkdocstrings.github.io/griffe2md/)). Its output contains
HTML and braces, which MDX rejects: set `markdown: { format: "detect" }` in
`docusaurus.config.ts`, so `.md` files are parsed as CommonMark. Write
docstrings in the Google style (`[tool.griffe2md] docstring_style`).

## Manual steps

- On PyPI, add a trusted publisher for each workflow: repository
  `{{owner}}/{{repo}}`, workflow `release.yml`, environment `release`; at the
  complete tier also `preview.yml` with environment `preview`
  ([adding a publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)).
- For a project not yet on PyPI, add a **pending publisher** from the account's
  Publishing page, with the project name: the first publish creates the
  project. A pending publisher reserves nothing; publish soon, or someone else
  may take the name
  ([creating a project through OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)).
- On the project's PyPI settings, require two-factor authentication for every
  maintainer and remove any API token.

## Audit checklist

- `uv.lock` committed; CI installs with `--locked`.
- `.python-version` holds the latest stable CPython; a library's
  `requires-python` is the oldest supported version and CI tests every
  supported version.
- ruff format and lint, mypy strict, pytest with coverage, and a build with
  `twine check --strict` run on every pull request.
- The committed version is `0.0.0`; the release stamps the real one.
- Previews are `.devN`, never `-preview.N` or `rcN`.
- Publishing uses trusted publishing with attestations; no `PYPI_TOKEN` or
  `TWINE_PASSWORD` secret exists.
- Shipped dependencies and extras take `fix(deps)` in Renovate.
