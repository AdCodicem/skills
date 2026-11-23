# C# 15 (.NET 11, November 2026)

Default on `net11.0`. Everything here is GA except memory safety (preview).
Sources: [What's new in C# 15](https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-15),
[.NET 11 compiler breaking changes](https://learn.microsoft.com/dotnet/csharp/whats-new/breaking-changes/compiler%20breaking%20changes%20-%20dotnet%2011).

Official list (Learn "What's new in C# 15", confirmed by the .NET 11 GA blog post and the Roslyn
feature-status page "C# 15.0" section):

| Feature | Status in C# 15 |
| --- | --- |
| Collection expression arguments (`with(...)`) | GA |
| Union types (`union`) | GA (needs `UnionAttribute`/`IUnion` from .NET 11) |
| Closed hierarchies (`closed` classes) | GA |
| Extension indexers | GA |
| Labeled `break` / `continue` | GA |
| Non-virtual static interface members on older runtimes | GA |
| Memory safety / unsafe evolution | **Preview** (`LangVersion=preview` + feature flag) |
| Dictionary expressions (`[k: v]`) | **Not in C# 15** (Roslyn "Working set: In progress"; blog: "upcoming") |
| Closed enums, closed interfaces | Not in C# 15 ("planned"/optional) |
| Null-conditional `await`, chained relational comparison, target-typed static member access, extension constants, compound assignment in initializers, relaxed modifier ordering | Not in C# 15 (Roslyn working set, in progress) |

## Collection expression arguments: `with(...)`

- **Version / status:** C# 15, GA.
- **What:** A `with(args)` element, which must be the **first** element of a collection expression, forwards arguments to the target type's constructor or `[CollectionBuilder]` create method (args go before the `ReadOnlySpan<T>` parameter). Enables capacity, comparers, etc.
- **Before / After:**

  ```csharp
  // Before
  var set = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "a", "A" };
  var list = new List<string>(values.Length * 2); list.AddRange(values);

  // After
  HashSet<string> set = [with(StringComparer.OrdinalIgnoreCase), "a", "A"];   // 1 element
  List<string> list = [with(capacity: values.Length * 2), .. values];
  IDictionary<string, int> map = [with(StringComparer.Ordinal)];               // new Dictionary<,>(comparer)
  ```

- **Rules:** Arrays and spans reject `with(...)` (even empty). Interfaces get a curated set: `IList<T>`/`ICollection<T>` → `List<T>()`/`List<T>(int)`; `IReadOnlyDictionary<K,V>` → `()` or `(IEqualityComparer<K>?)`; `IDictionary<K,V>` → the `Dictionary<K,V>` ctor shapes; `IEnumerable<T>`/`IReadOnlyList<T>` → `()` only. No `dynamic` args. Arguments are ignored for conversion and type inference (can't use `with` to disambiguate overloads). Types whose only constructors require arguments become usable with collection expressions if `with(...)` is present.
- **Breaking change:** In C# 15, `[with(x, y)]` is parsed as arguments, not a call to a method named `with`; use `@with(...)`.
- **When to use:** Comparers for sets/dictionaries (correctness: case-insensitive keys), capacity hints for large spreads.
- **When not:** `with()` with no args adds noise. Wanting dictionary literal syntax (`["a": 1]`) is dictionary expressions, which did **not** ship.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-15.0/collection-expression-arguments> ; <https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-15#collection-expression-arguments>

## Union types

- **Version / status:** C# 15, GA. **Requires** `System.Runtime.CompilerServices.UnionAttribute` and `IUnion` (in the .NET 11 runtime). The compiler does **not** synthesize them; on older TFMs you'd have to declare them yourself (and C# 15 on older TFMs is unsupported anyway).
- **What:** `union Name(Case1, Case2, ...)` declares a value that is exactly one of the listed case types (types need not be related). Implicit conversion from each case type; `switch` over a union is exhaustive when every case type is handled.
- **Before (marker interface / base class, non-exhaustive):**

  ```csharp
  public interface IPet;
  public record Cat(string Name) : IPet;
  public record Dog(string Name) : IPet;
  string Name(IPet p) => p switch { Cat c => c.Name, Dog d => d.Name, _ => throw new UnreachableException() };
  ```

- **After:**

  ```csharp
  public record Cat(string Name);
  public record Dog(string Name);
  public union Pet(Cat, Dog);

  Pet pet = new Dog("Rex");                 // implicit union conversion
  string name = pet switch
  {
      Cat c => c.Name,
      Dog d => d.Name,
      null => "none",                       // handles default(Pet); see gotchas
  };

  public union Result<T>(T, Exception);     // generic unions allowed
  public union IntOrString(int, string);    // value-type cases get boxed
  ```

- **Semantics and gotchas:**
  - The generated union is a **struct** with one public ctor per case type and an `object? Value` property. Value-type cases are **boxed** (allocation). Write a custom union (any class/struct with `[Union]`, single-parameter public ctors, `object? Value`) plus the optional non-boxing pattern (`HasValue`, `TryGetValue(out T)` per case) to avoid boxing.
  - `default(Pet)` (default fields, array elements) has `Value == null`; nullable analysis may not warn, and a switch without a `null` arm throws `SwitchExpressionException`. **Prefer a `null` arm over `_`/`var`**: a discard also swallows future case types and kills the "new case not handled" warning.
  - Type patterns test the **contents**: `pet is Dog`. `pet is Pet` is error CS8121. `{ }` / `var` match the union instance itself; untyped property patterns use the union's own members. Use `pet is not null` for "has a value".
  - Union bodies may add methods/properties but no instance fields, auto-properties, field-like events, or public single-parameter ctors; extra ctors must chain via `this(...)`.
  - A user-defined implicit conversion beats the union conversion; ambiguous case types → error.
  - Union conversions are not allowed in expression trees. No equality/deconstruction is generated (unlike records).
  - `union` is contextual: a field of a type named `union` (`union F;`) now parses as a union declaration; escape `@union`.
- **When to use:** Result-or-error returns, message/command dispatch over a closed set, replacing marker interfaces used only for pattern matching, combining types you don't own.
- **When not:** When cases share behavior/data you want on the base: use a `closed` hierarchy. Hot paths with value-type cases unless you write a non-boxing custom union. Public library APIs where adding a case later is a source-breaking change for every exhaustive `switch` in consumers.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/builtin-types/union> ; spec <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-15.0/unions> ; <https://devblogs.microsoft.com/dotnet/csharp-15-union-types/>

## Closed hierarchies (`closed` classes)

- **Version / status:** C# 15, GA. Emits `[IsClosedType]` (in .NET 11 `System.Runtime`) and `[CompilerFeatureRequired("ClosedClasses")]` on constructors so older compilers/VB can't derive.
- **What:** `closed` on a class means direct subclasses may only be declared in the same assembly (and module). A `switch` that handles every direct subclass is exhaustive (no `_` arm needed).
- **Before / After:**

  ```csharp
  // Before: abstract record + discard arm
  public abstract record Shape;
  // After
  public closed record Shape;
  public sealed record Circle(double R) : Shape;
  public sealed record Square(double Side) : Shape;

  double Area(Shape s) => s switch
  {
      Circle c => Math.PI * c.R * c.R,
      Square q => q.Side * q.Side,
  };                                   // no warning; adding a subtype warns at every switch
  ```

- **Rules / gotchas:** `closed` implies `abstract` (can't add `abstract`, `sealed`, `static`). Not transitive: a non-closed subclass can still be derived from in other assemblies; mark intermediates `closed` (or `sealed`) to keep exhaustiveness. Generic subclasses must use all their type parameters in the base type. A closed class with zero subtypes is not exhausted by an empty switch. Subtypes not accessible at the use site (e.g., `protected` nested) prevent exhaustiveness. Classes only: no closed interfaces or enums in C# 15. Adding a subtype or adding `closed` to a published class is a breaking change for consumers. `closed` as a type/alias name is now error CS9380 (`@closed`).
- **Closed vs union:** closed = inheritance-related types you own, with shared members; union = unrelated or foreign types, no shared base.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-15.0/closed-hierarchies> ; <https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-15#closed-hierarchies>

## Extension indexers

- **Version / status:** C# 15, GA.
- **What:** `this[...]` indexers inside `extension(<named receiver>)` blocks; get/set, expression-bodied, and ref-returning supported. Extension `Count`/`Length` + `int` indexer + `Slice(int,int)` now also enable `^1`, ranges, and list patterns.
- **Example:**

  ```csharp
  public static class ReadingExt
  {
      extension(Readings r)
      {
          public int Count => r.Values.Length;
          public int this[int i] => r.Values[i];
          public Readings Slice(int start, int len) => new(r.Values.AsSpan(start, len).ToArray());
      }
  }
  // r[^1], r[1..3], r is [10, .., 40]
  ```

- **Gotchas:** Lookup order: instance indexer → implicit index/range via instance members → extension indexer → implicit via extension members. Never used for arrays or `string`. Not allowed in expression trees. Extension `Length`/`Count` don't feed collection-expression spread optimizations. Don't put O(n) indexers on `IEnumerable<T>` (the docs example `sequence.ElementAt(i)` makes loops O(n²)).
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/keywords/extension#extension-indexers>

## Labeled `break` and `continue`

- **Version / status:** C# 15, GA.
- **What:** `break label;` / `continue label;` target the loop or `switch` statement directly labeled with `label:`.
- **Before / After:**

  ```csharp
  // Before: flag variable or goto
  bool done = false;
  for (int r = 0; r < h && !done; r++)
      for (int c = 0; c < w; c++)
          if (grid[r, c] == target) { done = true; break; }

  // After
  outer: for (int r = 0; r < h; r++)
  {
      for (int c = 0; c < w; c++)
      {
          if (grid[r, c] == skip) continue outer;
          if (grid[r, c] == target) break outer;
      }
  }
  ```

- **Rules:** Label must be **immediately** on the loop/switch (`a: b: while` only `b` works). `continue` only targets loops. Can't leave a `finally` block. Unlabeled `break`/`continue` unchanged. Style rule **IDE0410** flags flag-variable and `goto` patterns.
- **When not:** Deeply nested loops are often better extracted into a method with `return`.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-15.0/labeled-break-continue>

## Non-virtual static interface members on older runtimes

- **Version / status:** C# 15, GA.
- **What:** Non-virtual `static` interface members (helpers) compile even when the target runtime lacks default-interface-method support (e.g., `netstandard2.0`, .NET Framework). Instance DIMs, `static abstract`/`static virtual`, and `protected` interface members still need runtime support.
- **Example:** `public interface IMeasurement { static double ToMeters(double cm) => cm / 100; }` → `IMeasurement.ToMeters(250)`.
- **Note:** Mostly relevant to multi-targeting libraries; but C# 15 on non-`net11.0` TFMs is officially unsupported, so treat as niche.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-15#non-virtual-static-interface-members-on-older-runtimes>

## Memory safety / unsafe evolution (PREVIEW)

- **Version / status:** Preview in the .NET 11 SDK. Requires `<LangVersion>preview</LangVersion>` for syntax and pointer relaxations, plus `<Features>$(Features);updated-memory-safety-rules</Features>` for the new rules. Roslyn breaking-change docs already describe these behaviors as "C# 16". Model and syntax "might change for .NET 12 and C# 16" (.NET Blog).
- **What:** Pointer *types*, `&`, `fixed`, `stackalloc`-to-pointer, and `sizeof` no longer require `unsafe`; dereference, `->`, `p[i]`, and function-pointer calls still do. With the rules flag, `unsafe` on a member makes it *requires-unsafe* (callers must be in `unsafe`), and the modifier no longer opens an unsafe context for the body (use an inner `unsafe { }` block). New `unsafe(expr)` expression and `safe` contextual keyword (required on `extern`/`LibraryImport` members and explicit-layout fields under the new rules).
- **Example:**

  ```csharp
  public static unsafe int ReadInt32(byte* p) { unsafe { return *(int*)p; } }   // preview
  static readonly int Sig = unsafe(ReadSignature());
  [LibraryImport("libc")] internal static safe partial int getpid();
  ```

- **Guidance:** Do not adopt in production code; mention only for experiments. Breaking risks under preview: new lambda overload ambiguities (pointer delegates become candidates), `safe` as a keyword, more members requiring `unsafe`.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/unsafe-code#the-updated-memory-safety-model-preview> ; <https://learn.microsoft.com/dotnet/csharp/language-reference/compiler-options/language#enable-the-updated-memory-safety-rules>

## Other .NET 11 compiler breaking changes (any LangVersion)

- `Span`/`ReadOnlySpan` collection expressions now have *declaration-block* safe-context (was function-member): assigning a `Span<int> s = [x];` created inside a loop body to an outer `scoped` span now errors; use an array or hoist it.
- `ref readonly`-returning synthesized delegates/local functions require `System.Runtime.InteropServices.InAttribute`.
- `dynamic` `&&`/`||` with an interface-typed left operand is a compile error (CS7083).
- `nameof(this.P)` inside attributes is disallowed.
- `(X.Y) when` in a switch-expression arm now parses as constant pattern + `when` clause.
- Source: <https://learn.microsoft.com/dotnet/csharp/whats-new/breaking-changes/compiler%20breaking%20changes%20-%20dotnet%2011>
