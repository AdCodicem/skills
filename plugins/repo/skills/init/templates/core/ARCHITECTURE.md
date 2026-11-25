# Architecture

The map of the code: where to start reading and how the parts fit together.
The API reference is generated ({{docs-url}}); the reasons behind the current shape
are in the [decision records](docs/adr/).

## Overview

{{One paragraph: what the system does and its main moving parts.}}

## Layout

```text
{{The top-level folders and what each holds, for example:
src/          source, one folder per package or service
tests/        unit and integration tests, mirroring src/
docs/         decision records and the documentation site
samples/      runnable examples, built in CI
benchmarks/   benchmarks, run on demand}}
```

## Where to start

{{The entry points a newcomer should read first, in order.}}

## Key decisions

Significant, hard-to-reverse decisions are recorded in [`docs/adr/`](docs/adr/).
This file describes the current shape; the records explain how it got here.
