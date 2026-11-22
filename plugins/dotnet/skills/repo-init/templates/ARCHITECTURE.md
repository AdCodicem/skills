# Architecture

High-level map of how this project is put together — for the "where do I
even start reading" question, not exhaustive API docs (that's the
[generated reference](https://{{owner}}.github.io/{{repo}}/docs/api/)).

## Overview

{{One paragraph: what the system/library does and its main moving parts.}}

## Project layout

```
src/            source projects, one per publishable package
tests/          unit + integration tests, mirrors src/ 1:1
benchmarks/     BenchmarkDotNet projects (see benchmarks/README.md)
samples/        minimal runnable examples (see samples/README.md)
docs/           Docusaurus site (guides + generated API reference)
```

## Key decisions

Significant, hard-to-reverse decisions are recorded as Architecture
Decision Records in [`docs/adr/`](docs/adr/), not here — this file gives
the current shape, the ADRs give the history and the trade-offs that led
to it. Start with [`0001-record-architecture-decisions.md`](docs/adr/0001-record-architecture-decisions.md).
