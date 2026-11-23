# Baseline: C# 12 (.NET 8) and C# 13 (.NET 9)

The idioms available on `net8.0` / `net9.0`, still the modern way on later
targets. Both runtimes reached end of support on 2026-11-10.

## C# 12 (net8.0 default)

- **Collection expressions:** one syntax for arrays, lists, spans; `..` spreads. `int[] a = [1, 2, ..rest];` `List<string> l = [];`
- **Primary constructors (classes/structs):** parameters in scope in the whole type; they're captured mutable state, not readonly fields or properties (assign to a `readonly` field if needed). `class Svc(ILogger<Svc> log) { void Run() => log.LogInformation("x"); }`
- **Inline arrays:** fixed-size struct buffers for perf code. `[InlineArray(8)] struct Buf { int _e; }`
- **Alias any type:** `using Point = (int X, int Y);`
- **`ref readonly` parameters:** `void M(ref readonly Large v)` (pass by ref, no mutation, warns on rvalues).
- **Default lambda parameters:** `var inc = (int x, int by = 1) => x + by;`
- **`nameof` on instance members from static contexts:** `nameof(Name.Length)` in a static method/attribute.
- (Also: `[Experimental]` attribute; interceptors were preview only.)

## C# 13 (net9.0 default)

- **`params` collections:** `params` on any collection type, including spans. `void Log(params ReadOnlySpan<string> parts)`
- **`System.Threading.Lock`:** `lock` on a `Lock` instance uses the new, faster API. `private readonly Lock _gate = new(); lock (_gate) { ... }`
- **`\e` escape:** `"\e[1m"` for ESC (U+001B).
- **Implicit index `^` in object initializers:** `new Buffer { Data = { [^1] = 0 } }`
- **`ref`/`unsafe` in iterators and async methods:** `ref` locals and `Span<T>` allowed in `async` methods if not used across `await`.
- **`ref struct` interfaces and `allows ref struct`:** `void M<T>(T x) where T : allows ref struct`
- **Partial properties and indexers:** `public partial string Name { get; set; }` (source generators).
- **`OverloadResolutionPriorityAttribute`:** library authors steer overload choice. `[OverloadResolutionPriority(1)] void M(ReadOnlySpan<int> s)`
- **Method group natural type improvements, better conversion from collection expression element:** fewer ambiguities; no code change needed.
- (`field` keyword was preview in C# 13; GA in C# 14.)
