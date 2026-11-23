# hello-world

Reference plugin that shows every convention of this repository in one place.
It is validated and tested in CI but is **not** listed in the marketplace.
Copy what you need from it when you build a real plugin.

## Components

| Type | Name | Surfaces | What it shows |
| --- | --- | --- | --- |
| Skill | `/hello-world:greet` | Claude Code, claude.ai, API | Portable skill calling a standard-library Python script |
| Subagent | `summarizer` | Claude Code, Cowork | Read-only agent restricted to `Read`, `Grep`, `Glob` |
| Hook | `PreToolUse` on `Bash` | Claude Code, Cowork | Python hook that blocks `git push --force` to main/master |

It also includes unit tests for the script and the hook (`tests/`) and an eval
suite (`evals/`) for `claude plugin eval`.

## Try it locally

```bash
claude --plugin-dir examples/hello-world
```

Then ask "Say hello to Ada in French", or ask Claude to force push to main.

## Requirements

The hook runs `python3`. On Windows, make sure `python3` resolves to a real
Python install (for example through the `py` launcher), otherwise the hook
fails without blocking anything.
