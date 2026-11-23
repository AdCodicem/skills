# Testing

Four layers. The first three are deterministic, free and run in CI. The fourth
is behavioral, recommended before a release, and runs locally on a Claude
subscription so that nothing is billed to an API account.

| Layer | Tool | What it catches | Where |
| --- | --- | --- | --- |
| 1. Structure | `claude plugin validate --strict` | Invalid manifests, names, paths, frontmatter, `.mcp.json` | CI, `check.py` |
| 2. Conventions | `scripts/lint_skills.py` | Portability, stdlib-only Python, registration, size, broken links | CI, `check.py` |
| 3. Unit tests | `pytest` | Bugs in skill scripts, hooks and repository tooling | CI (Linux + Windows), `check.py` |
| 4. Evals | `claude plugin eval` | A skill that does not fire, fires when it should not, or gives a wrong result | Local, optional |

Run layers 1 to 3, plus ruff, markdownlint and a packaging dry run, with:

```bash
python scripts/check.py
```

## Unit tests

- Skill script tests live in the plugin's `tests/` folder; repository tooling
  tests live in `tests/`.
- Run scripts with `sys.executable` in a subprocess, so the tests also check the
  command-line interface and run on Windows.
- Test hooks by piping hook events (JSON) into the script and asserting the exit
  code and stderr.
- CI uses Python 3.11, the version of the Claude API sandbox.

## Evals

`claude plugin eval` runs each case in a fresh Claude Code session, with and
without the plugin, and scores the result with graders. Cases live in
`plugins/<plugin>/evals/<case>/`.

**Cost**: evals use the credentials of the local Claude Code session. Logged in
with a Claude subscription and with `ANTHROPIC_API_KEY` unset, they are covered
by the subscription and count toward its usage limits. With `ANTHROPIC_API_KEY`
set, every run and every LLM judge is billed to the API account. That is why
evals do not run in CI.

```bash
env -u ANTHROPIC_API_KEY claude plugin eval plugins/<plugin>
```

On Windows PowerShell, run `Remove-Item Env:ANTHROPIC_API_KEY` first.

Each skill should have at least one case that must trigger it and one that must
not. Prefer `tool_used` and `regex` graders: they are computed from the
transcript and cost nothing. See the `/run-evals` skill and
`examples/hello-world/evals/`.
