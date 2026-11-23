# Samples

Minimal, runnable examples — not a tutorial, just working code someone can
clone and run to see the library used for real, without reading the whole
README first.

## Convention

- One console app or minimal API per scenario: `samples/BasicUsage/`,
  `samples/WithDependencyInjection/`, etc.
- Each sample project references the `src/` project directly (not the
  published NuGet package), so samples stay correct against the current
  code without needing a release first.
- Keep each sample small enough to read top to bottom in under a minute.
  If it needs more than that, it's a guide for the docs site, not a sample.
- Samples are excluded from the solution's Pack/Publish targets — they're
  for humans to read and run, not to ship.
