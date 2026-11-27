# Hygiene

Files that make every clone behave the same, on every operating system and in
every editor. Templates: `templates/core/dot-editorconfig`,
`dot-gitattributes`, `dot-gitignore`, `dot-pre-commit-config.yaml`, plus each
module's `editorconfig`, `gitattributes` and `gitignore` fragments, appended to
the core files.

## Files

- **`.editorconfig`** ([editorconfig.org](https://editorconfig.org/)): UTF-8,
  LF, final newline, trimmed trailing whitespace, two-space indentation by
  default; each module appends its language's section (C# rules and analyzer
  severities for .NET).
- **`.gitattributes`**: `* text=auto eol=lf`, binaries marked `binary`,
  generated files (`CHANGELOG.md`, lock files, the workflow lockfile) marked
  `linguist-generated` so they collapse in diffs
  ([GitHub docs](https://docs.github.com/en/repositories/working-with-files/managing-files/customizing-how-changed-files-appear-on-github)).
  Windows-only scripts keep CRLF; `.sln` files too (the .NET module).
- **`.gitignore`**: operating system and editor files, `.env*` (with
  `.env.example` kept), keys, `node_modules/` and `dist/` (the release staging
  folder); each module appends its build output.
- **Pre-commit hooks** with [pre-commit](https://pre-commit.com/) or its
  compatible drop-in [prek](https://github.com/j178/prek): file hygiene
  (case conflicts, Windows-illegal names, symlinks, merge markers, large files,
  private keys, JSON, TOML and YAML syntax), gitleaks for secrets, and each
  module's formatters. `pre-commit install` once per clone; CI runs every hook
  on every file (`lint.yml`), so a contributor without the hook is caught.
- **Pinned toolchain**: `global.json` (.NET), `.nvmrc` (Node.js),
  `.python-version` (Python), and the module's tool manifest. CI reads these
  files; nothing in a workflow repeats a version.

## Audit checklist

- The four files exist and the ecosystems' sections are present.
- `git ls-files --eol` shows no CRLF outside the files meant to have it.
- No secret, key or `.env` file is tracked (`git ls-files | grep -E '\.env|\.pem|\.key'`).
- Every hook of `.pre-commit-config.yaml` passes on every file.
