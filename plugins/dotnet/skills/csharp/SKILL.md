---
name: csharp
description: 'Write, review and modernize C# code with the language features of C# 14 (.NET 10) and C# 15 (.NET 11), limited to what the project''s target framework supports: extension members and extension properties, the field keyword, null-conditional assignment, implicit span conversions, nameof with unbound generics, user-defined compound assignment, collection expression arguments with with(...), union types, closed hierarchies, extension indexers, labeled break and continue, plus the C# 12/13 baseline (primary constructors, collection expressions, params spans, Lock). Detects the target framework and C# version first. Use whenever writing, editing or reviewing C# code, and when asked to modernize C#, use the latest syntax, or check C# upgrade risks. Example requests: "add a property with validation", "refactor this to modern C#", "review this class", "utilise les nouveautés de C# 14", "modernise ce code C#". Not for F#, VB or other languages.'
metadata:
  surfaces: claude-code
---

# Modern C# (C# 14 and C# 15)

Make C# code use the best language construct the project's target framework
supports, where it reads better, runs faster or is safer. This skill also owns
the target detection script used by the other skills of this plugin
(`runtime-libraries`, `aspnetcore`, `efcore`, `tooling`, `migrate`).

## Before writing code

1. **Detect the target** once per project and session (use `python` if
   `python3` is missing):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/csharp/scripts/detect_target.py" <path>
   ```

   `<path>` is a folder, `.csproj`, `.slnx`/`.sln` or a `.cs` file. Add
   `--json` for machine-readable output. It reports, per project, the target
   frameworks and the **effective C# version** per framework, preview opt-ins,
   nullable/AOT settings, and the ASP.NET Core, EF Core and test stacks.
2. **Pick the language level** from the result:

   | Target framework | C# version | What to use |
   | --- | --- | --- |
   | `net11.0` | 15 | Everything below |
   | `net10.0` | 14 | C# 14 and baseline |
   | `net9.0` / `net8.0` | 13 / 12 | [references/baseline.md](references/baseline.md) only; both are out of support since 2026-11-10, suggest moving to .NET 10 (LTS) |
   | `netstandard2.0`, .NET Framework | 7.3 | Classic syntax; do not assume newer features |

   - **Multi-targeting**: write for the *lowest* C# version among the targets,
     unless code is behind `#if NET10_0_OR_GREATER` (or similar).
   - **Explicit `LangVersion`**: respect it. A version higher than the target
     framework's default is unsupported by Microsoft (some features need
     runtime types, such as unions on .NET 11); do not rely on it, and never
     raise `LangVersion` yourself. `latest` depends on the installed SDK: flag it.
   - **`LangVersion` preview / `EnablePreviewFeatures`**: the project opted in,
     but still do not introduce preview features unless the user asks.
3. **Load the reference you need**:
   - [references/csharp-14.md](references/csharp-14.md): every C# 14 feature with rules, pitfalls and breaking changes.
   - [references/csharp-15.md](references/csharp-15.md): every C# 15 feature, including what did *not* ship.
   - [references/baseline.md](references/baseline.md): C# 12 and 13 recap.
4. **When a detail is not covered or looks uncertain**, check Microsoft Learn
   with the `microsoft_docs_search` / `microsoft_docs_fetch` tools if they are
   available.

## Rules

- **Change only what the task needs.** New code uses modern constructs. In
  existing code you touch, *mention* modernization opportunities; do not rewrite
  surrounding code unless asked. Keep diffs minimal.
- **Modern only when it improves the code.** Each row below says when it helps;
  when it does not (the old form is clearer, or the team style differs), keep it.
- **Match the file's conventions** (naming, `var`, braces, file-scoped
  namespaces) and the `.editorconfig`, except where they conflict with a clear
  safety or performance gain; then mention it.
- **Never present unreleased syntax as available.** Dictionary expressions
  (`[k: v]`), closed enums and interfaces, null-conditional `await`, chained
  comparisons and extension constants are **not** in C# 15. The C# 15 memory
  safety model is **preview**: explain it, never introduce it unasked.

## Use this, not that

| Instead of | Prefer | C# | When it helps |
| --- | --- | --- | --- |
| Private field used only by one property | `field` in the accessor: `set => field = value?.Trim() ?? "";` | 14 | Validation, normalization, change notification, simple lazy init |
| `if (x is not null) x.P = v;` / `x.E += h` | `x?.P = v;`, `x?.E += h;` | 14 | Optional receivers. Not when null is a bug: throw instead |
| Static class of `this` extension methods only | `extension(T receiver) { ... }` block with properties, static members, operators | 14 | Adding property-like or static helpers to types you do not own |
| `arr.AsSpan().M()` to reach a span extension | `arr.M()` (implicit span conversion) | 14 | Allocation-free span overloads are picked automatically |
| `nameof(List<int>)` | `nameof(List<>)` | 14 | Logging, messages, attributes |
| `(string s, out int r) => ...` | `(s, out r) => ...` | 14 | Delegates with `ref`/`out`/`in`/`scoped` parameters |
| Binary operator allocating a new big mutable object for `+=` | Instance `void operator +=(T)` and `operator ++()` | 14 | Buffers, tensors, builders. Keep it semantically equal to `+` |
| `new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ... }` | `[with(StringComparer.OrdinalIgnoreCase), "a", "b"]` | 15 | Comparers and capacity. Concrete types only for dictionaries: `IDictionary`/`IReadOnlyDictionary` targets do not compile |
| Marker interface + `_ => throw` arm to emulate "one of" | `union Result(Success, Error);` and an exhaustive `switch` with a `null` arm | 15 | Unrelated or foreign case types, result types |
| `abstract record` base + discard arm | `closed record Shape;` + `sealed` subtypes, exhaustive `switch` without `_` | 15 | Related types you own with shared members |
| Extension `ElementAt`-style method | Extension indexer in an `extension` block | 15 | Cheap (O(1)) indexing only |
| Flag variable or `goto` to leave nested loops | `break outer;` / `continue outer;` | 15 | When extracting a method with `return` is not clearer |
| `new List<T>()`, `new T[] { ... }`, `Array.Empty<T>()` | Collection expressions `[]`, `[a, b, ..rest]` | 12 | Almost always |
| Constructor that only stores injected services | Primary constructor `class Svc(ILogger<Svc> log)` | 12 | DI services. Parameters are mutable captures: copy to a `readonly` field when that matters |
| `lock (object)` | `private readonly Lock _gate = new(); lock (_gate)` | 13 | All new locking code (.NET 9+) |
| `params T[]` on hot paths | `params ReadOnlySpan<T>` | 13 | Avoids the array allocation |

Pattern matching, records, `required` members, raw string literals, file-scoped
namespaces and switch expressions remain the default idioms from earlier
versions.

## Pitfalls to check

- **`field` breaking change**: a type with a member named `field` now binds
  `field` inside accessors to the backing field (warning CS9258). Use
  `this.field` / `@field` or rename.
- **Span conversions change overload resolution**: new ambiguities (for example
  xUnit `Assert.Equal` with collection expressions), `ArrayTypeMismatchException`
  with covariant arrays, and `array.Contains(x)` inside expression trees binding
  to `MemoryExtensions.Contains` (breaks expression interpreters and some LINQ
  providers). Fix with `.AsSpan()`, `.AsEnumerable()` or `Enumerable.Contains`.
- **New contextual keywords**: identifiers named `extension`, `scoped`,
  `partial` (C# 14), `union`, `closed` and methods named `with` inside `[...]`
  (C# 15) need `@`.
- **Unions** are generated as structs: value-type cases are boxed, and
  `default(T)` holds `null`. Switch with an explicit `null` arm rather than `_`,
  so a new case type still produces a warning. Adding a case or making a class
  `closed` in a published library breaks consumers' exhaustive switches.
- **Extension properties** must stay cheap: a property implies O(1).

## Modes

- **Writing code**: apply the rules and the table to the code you write.
- **Review**: for each finding give the current code, the modern alternative,
  the C# version it needs, and the reason (bug risk, safety, performance,
  readability). Separate what is available now from what needs an upgrade.
  Review the risky constructs above with priority.
- **Modernize on request**: list the planned changes first, grouped as
  mechanical (collection expressions, `field`, `nameof`), structural (extension
  blocks, unions, closed hierarchies) and behavior-sensitive (span overloads,
  compound operators). Apply after agreement; keep public API compatible unless
  the user accepts a break. For a large codebase, delegate the inventory to the
  `modernization-auditor` agent of this plugin.
- **Upgrade**: language upgrades come with target framework upgrades; use the
  `migrate` skill.

## Verify

- `dotnet build` with no new warnings (watch CS9258, CS8121, nullable warnings),
  then the tests.
- When a project has an `.editorconfig`, `dotnet format --verify-no-changes`
  shows whether new code follows it. IDE0340 (unbound `nameof`) and IDE0410
  (labeled `break`/`continue`) flag remaining old patterns when enabled.
