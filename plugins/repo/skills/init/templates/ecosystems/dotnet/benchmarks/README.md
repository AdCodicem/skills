# Benchmarks

Performance measurements with [BenchmarkDotNet](https://benchmarkdotnet.org/).

## Conventions

- One project per area worth measuring: `benchmarks/{{project}}.Benchmarks/`,
  referencing the projects under `src/` directly.
- `BenchmarkDotNet` is referenced by benchmark projects only, never by `src/`.
  Its version lives in `Directory.Packages.props`.
- One class per scenario (`SerializationBenchmarks`), with a `[MemoryDiagnoser]`
  so allocations are reported next to timings.
- A performance change ships with the benchmark that shows it, and the pull
  request quotes the before and after numbers from the same machine.

## Running

Benchmarks never run on pull requests: shared runners are noisy and a full run
is slow. Run them deliberately:

```bash
dotnet run --configuration Release --project benchmarks/{{project}}.Benchmarks -- --filter '*'
```

or dispatch the `benchmarks` workflow (Actions, benchmarks, Run workflow) and
download the results artifact. Compare runs from the same machine or the same
workflow only.
