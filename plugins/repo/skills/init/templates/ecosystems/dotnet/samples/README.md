# Samples

Small programs that use the library for real: clone, run, read top to bottom
in a minute.

## Conventions

- One project per scenario: `samples/BasicUsage/`,
  `samples/WithDependencyInjection/`.
- A sample references the projects under `src/` (not the published package),
  so it is always correct against the current code.
- Samples are in the solution, so CI builds them on every pull request, and
  they are never packed (`IsPackable` stays false).
- A tutorial of the documentation site takes its code from a sample, so the
  tutorial never shows code that does not compile.
- A sample that needs more than a minute to read is a guide for the
  documentation site, not a sample.
