# C# 14 (.NET 10, November 2025)

All features are GA and available by default on `net10.0` and later.
Sources: [What's new in C# 14](https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-14),
[.NET 10 compiler breaking changes](https://learn.microsoft.com/dotnet/csharp/whats-new/breaking-changes/compiler%20breaking%20changes%20-%20dotnet%2010).

Official list (Learn "What's new in C# 14"): extension members, null-conditional assignment,
`nameof` with unbound generics, implicit span conversions, modifiers on simple lambda parameters,
`field`-backed properties, partial events and constructors, user-defined compound assignment,
new preprocessor directives for file-based apps. csharplang version history additionally lists
extension operators, optional/named arguments in expression trees, and an async `Main` codegen
update.

## Extension members (extension blocks)

- **Version / status:** C# 14, GA. Language-only (compiler synthesizes `ExtensionMarkerNameAttribute`); no runtime requirement beyond TFM default rules.
- **What:** New `extension(<receiver>) { ... }` block inside a top-level, non-generic `static class`. Supports instance extension methods and **properties**, **static** extension methods/properties (called as if static members of the extended type), and **user-defined operators**. C# 15 adds indexers (see [csharp-15.md](csharp-15.md#extension-indexers)).
- **Before:**

  ```csharp
  public static class SeqExt
  {
      public static bool IsEmpty<T>(this IEnumerable<T> source) => !source.Any();
  }
  // call: if (items.IsEmpty()) ...
  ```

- **After:**

  ```csharp
  public static class SeqExt
  {
      extension<T>(IEnumerable<T> source)            // instance members: receiver named
      {
          public bool IsEmpty => !source.Any();        // extension property
          public IEnumerable<T> WhereNotNull() => source.Where(x => x is not null);
      }

      extension<T>(IEnumerable<T>)                   // static members only: receiver unnamed
      {
          public static IEnumerable<T> Empty => [];    // IEnumerable<int>.Empty
          public static IEnumerable<T> operator +(IEnumerable<T> l, IEnumerable<T> r) => l.Concat(r);
      }
  }
  // if (items.IsEmpty) ...;  var all = a + b;  var none = IEnumerable<int>.Empty;
  ```

- **Rules / gotchas:**
  - Instance extension methods compile to the **same IL** as classic `this` extension methods: converting is binary- and source-compatible. You can mix both forms.
  - Type parameter goes on the `extension<T>` when the receiver uses it; extra type parameters go on the member. Never both places.
  - Receiver can be `ref`, `ref readonly`, or `in` only when the receiver type is known to be a value type (`extension(ref Point p)` lets members mutate structs).
  - No fields, no auto-properties (no state), no `init` accessors, no `abstract/virtual/override/new/sealed/partial/protected/readonly` members. Extension members can't access private members of the receiver.
  - A block does **not** introduce a scope: all members in the containing static class need unique signatures.
  - Instance members require a named receiver; static members can't reference the receiver (except in `nameof`).
  - Ambiguities between two static classes are resolved by calling the implementation statically: `E1.M2(obj)`, property accessors as `E1.get_P(obj)`.
  - Extension properties participate in object initializers, `with` expressions, and property patterns (`x is { IsEmpty: false }`), but **not** in `foreach` `Current`, `await` `IsCompleted`, or list-pattern / implicit-index `Count`/`Length` (C# 15 extends implicit index/range support to extension members; see [csharp-15.md](csharp-15.md#extension-indexers)).
  - Expression trees can't contain extension property (or indexer) access.
  - `extension` is a contextual keyword: types, aliases, and type parameters can't be named `extension` (escape with `@extension`).
  - XML docs: put `<param>`/`<typeparam>` for the receiver on the `extension` block, not on members.
- **When to use:** Computed "property-like" helpers (`IsEmpty`, `Median`), static factory helpers on types you don't own (`IEnumerable<T>.Empty`), operators on interfaces/third-party types. Prefer new syntax for new code; migrate classic extension methods only when you also add properties/static members to the same group.
- **When not:** Don't hide expensive work behind an extension property (`source.Any()` enumerates; a property implies cheap). Don't add operators to types where the semantics are surprising. Don't use for anything needing state.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/keywords/extension> ; spec <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/extensions>

## `field` keyword (field-backed properties)

- **Version / status:** C# 14, GA (was preview in C# 13). Language-only.
- **What:** Inside a property accessor, `field` refers to a compiler-synthesized backing field, so you can add logic to one accessor and keep the other auto-implemented.
- **Before:**

  ```csharp
  private string _name = "";
  public string Name
  {
      get => _name;
      set => _name = value ?? throw new ArgumentNullException(nameof(value));
  }
  ```

- **After:**

  ```csharp
  public string Name
  {
      get;
      set => field = value ?? throw new ArgumentNullException(nameof(value));
  } = "";

  public string DisplayName
  {
      get;
      set { if (field == value) return; field = value; OnPropertyChanged(); }
  }

  public Connection Conn => field ??= CreateConnection();   // lazy (not thread-safe)
  ```

- **Gotchas / breaking changes:**
  - If the type already has a member named `field`, inside accessors `field` now binds to the backing field: warning **CS9258**. Use `this.field` or `@field`, or rename the member. Declaring a local/parameter named `field` inside an accessor is error **CS9272**.
  - Keyword only in property `get`/`set`/`init` accessors (and nested lambdas/local functions there), **not** in indexers or event accessors. `nameof(field)` doesn't compile.
  - A property initializer writes the backing field directly (does **not** run the setter); assign in the constructor if you want the setter logic.
  - Field-targeted attributes work: `[field: JsonIgnore]`. Nullability of lazy patterns: use `[field: MaybeNull, AllowNull]` if the compiler complains (CS9264). Don't mix `field` in one accessor with an explicit field in the other (CS9266).
  - Not available on ref-returning properties. In structs, accessor usage counts as reading `this` before assignment (CS9020) in some constructors.
  - `field ??= new X()` lazy init is not thread-safe; use `Lazy<T>`/`LazyInitializer` when needed.
- **When to use:** Validation, normalization (trim/lowercase), `INotifyPropertyChanged`, simple lazy init. Replace hand-written `_backing` fields used by exactly one property.
- **When not:** When other members must access the backing storage directly (the synthesized field is only reachable from the property's accessors).
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/keywords/field> ; spec <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/field-keyword> ; breaking changes <https://learn.microsoft.com/dotnet/csharp/whats-new/breaking-changes/compiler%20breaking%20changes%20-%20dotnet%2010>

## Null-conditional assignment (`a?.b = c`, `a?[i] = c`)

- **Version / status:** C# 14, GA.
- **What:** `?.` and `?[]` can appear on the left of `=` and of compound assignments (`+=`, `-=`, `??=`, ...). The right side is evaluated **only** when the receiver is non-null.
- **Before:**

  ```csharp
  if (customer is not null) customer.Order = GetCurrentOrder();
  if (button is not null) button.Click += OnClick;
  ```

- **After:**

  ```csharp
  customer?.Order = GetCurrentOrder();   // GetCurrentOrder() not called when customer is null
  button?.Click += OnClick;
  cache?[key] = value;
  settings?.Timeout ??= TimeSpan.FromSeconds(30);
  ```

- **Gotchas:** `++`/`--` are not allowed (`a?.b++` is an error). Not an lvalue: no `ref a?.b`, no deconstruction `(a?.b, c?.d) = ...`. Doesn't work with non-nullable struct receivers or `Nullable<T>` receivers. If the result is used, its type becomes nullable (`T?`), which fails for unconstrained generic `T`. Side-effect skipping of the RHS can surprise readers: don't put required side effects on the right.
- **When to use:** Optional dependencies, event wiring on maybe-null objects, UI code.
- **When not:** When null is a bug: silently skipping the assignment hides it; throw or use `ArgumentNullException.ThrowIfNull` instead.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/null-conditional-assignment>

## First-class `Span<T>` / `ReadOnlySpan<T>` (implicit span conversions)

- **Version / status:** C# 14, GA. Uses existing BCL helpers (`op_Implicit`, `ReadOnlySpan<T>.CastUp`, `MemoryExtensions.AsSpan(string)`); if a helper is missing, compile error.
- **What:** New built-in implicit conversions: `T[]` → `Span<T>`; `T[]` → `ReadOnlySpan<U>` (covariant); `Span<T>` → `ReadOnlySpan<U>`; `ReadOnlySpan<T>` → `ReadOnlySpan<U>` (covariant); `string` → `ReadOnlySpan<char>`. They are *standard* conversions, so they apply to **extension receivers**, generic type inference, and overload resolution (span overloads now win over `IEnumerable<T>`; `ReadOnlySpan<T>` preferred over `Span<T>`). Not considered for method group conversions.
- **Before / After:**

  ```csharp
  static class SpanExt { public static int CountZeros(this ReadOnlySpan<int> s) { /*...*/ return 0; } }

  int[] data = [1, 0, 2, 0];
  int n13 = data.AsSpan().CountZeros();  // C# 13: needed AsSpan()
  int n14 = data.CountZeros();           // C# 14: array -> ReadOnlySpan<int> receiver conversion
  ReadOnlySpan<object> objs = new string[] { "a" };   // covariant conversion
  ```

- **Breaking changes / pitfalls (important for upgrades):**
  - **Different overload chosen or new ambiguities**, e.g. xUnit `Assert.Equal([2], x)` became ambiguous; fix with `.AsSpan()` or API-side `OverloadResolutionPriorityAttribute`.
  - **Covariant arrays:** a `Span<T>` overload may now be picked over `IEnumerable<T>` and throw `ArrayTypeMismatchException` at runtime (`object[] o = new string[1]`). Workaround `.AsEnumerable()`.
  - **Expression trees:** `array.Contains(x)` inside `Expression<...>` now binds to `MemoryExtensions.Contains` (ref struct). `Compile(preferInterpretation: true)` fails at runtime, and LINQ providers that expect `Enumerable.Contains` must handle it (EF Core issue 35100). Workaround: `Enumerable.Contains(array, x)`.
  - `x.Reverse()` on an array resolved to in-place `MemoryExtensions.Reverse` (returns `void`) when targeting below `net10.0` with C# 14 (unsupported config). `net10.0` adds `Enumerable.Reverse(this T[])` to avoid it.
  - API authors: adding `ReadOnlySpan<T>` overloads next to `IEnumerable<T>` is now safe for C# 14 callers but can break C# 13 callers.
- **Performance:** Positive: more calls hit allocation-free span overloads (e.g., `MemoryExtensions`) without explicit `AsSpan()`. Safety unchanged (spans remain ref structs).
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/builtin-types/built-in-types> ; spec <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/first-class-span-types> ; <https://learn.microsoft.com/dotnet/core/compatibility/core-libraries/10.0/csharp-overload-resolution>

## `nameof` with unbound generic types

- **Version / status:** C# 14, GA.
- **What:** `nameof(List<>)` → `"List"`, `nameof(Dictionary<,>)` → `"Dictionary"`; member chains work: `nameof(List<>.Count)` → `"Count"`.
- **Before / After:** `nameof(List<int>)` → `nameof(List<>)`.
- **Limits:** No nesting (`A<B<>>`) and no partially unbound (`Dictionary<int,>`). Style rule **IDE0340** suggests the unbound form.
- **When to use:** Logging, exception messages, attribute arguments where type args are irrelevant (also avoids needing a dummy type to satisfy constraints).
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/unbound-generic-types-in-nameof>

## Modifiers on simple (implicitly typed) lambda parameters

- **Version / status:** C# 14, GA.
- **What:** `ref`, `out`, `in`, `ref readonly`, `scoped` allowed without writing parameter types. `params` still requires explicit types.
- **Before / After:**

  ```csharp
  delegate bool TryParse<T>(string text, out T result);
  TryParse<int> p13 = (string text, out int result) => int.TryParse(text, out result);
  TryParse<int> p14 = (text, out result) => int.TryParse(text, out result);
  ```

- **Breaking change:** `scoped` in a lambda parameter list is always a modifier now (`(scoped scoped s) => ...` breaks; use `@scoped`).
- **Source:** <https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-14#simple-lambda-parameters-with-modifiers>

## Partial constructors and partial events

- **Version / status:** C# 14, GA.
- **What:** Instance constructors and events can be `partial`: exactly one defining declaration and one implementing declaration. Primarily for source generators (interop bindings, weak events, DI/registration generators).
- **Example:**

  ```csharp
  public partial class Widget
  {
      public partial Widget(int id);                 // defining (user code)
      public partial event EventHandler? Changed;    // defining: field-like syntax
  }
  public partial class Widget                        // implementing (generated)
  {
      public partial Widget(int id) { Id = id; }   // only the implementation may have a : this(...)/: base(...) initializer
      public partial event EventHandler? Changed { add { /*...*/ } remove { /*...*/ } }
      public int Id { get; }
  }
  ```

- **Rules:** Partial event is not field-like (no backing storage; only `+=`/`-=`). Implementing event must have `add`/`remove`. Only one partial type declaration can have the primary constructor. Default parameter values on the implementing ctor are ignored (warning). Doc comments on the implementation win.
- **Breaking change:** `partial` can't be a method return type without `@partial`. Related: partial interface properties/events are now implicitly `public virtual`.
- **When not:** Hand-written code with no generator; plain constructors are clearer.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/partial-events-and-constructors>

## User-defined compound assignment and instance `++`/`--`

- **Version / status:** C# 14, GA.
- **What:** Types can declare **instance**, `void`-returning `operator +=(T)` (and `-=`, `*=`, `/=`, `%=`, `&=`, `|=`, `^=`, `<<=`, `>>=`, `>>>=`, plus `checked` variants) and parameterless instance `operator ++()` / `operator --()`, which mutate in place instead of allocating a new result.
- **Before / After:**

  ```csharp
  public sealed class Accumulator
  {
      public double[] Values { get; }
      public Accumulator(int n) => Values = new double[n];

      public static Accumulator operator +(Accumulator a, Accumulator b) { /* allocates new */ return a; }

      public void operator +=(Accumulator other)        // C# 14: in-place
      {
          for (int i = 0; i < Values.Length; i++) Values[i] += other.Values[i];
      }
      public void operator ++() { for (int i = 0; i < Values.Length; i++) Values[i]++; }
  }
  // acc += other;  -> calls op_AdditionAssignment, no allocation
  ```

- **Semantics:** For `x op= y` where `x` is a variable, the compiler tries the compound operator first, then falls back to the binary operator. If the target is a property, the binary operator + setter is used (no setter → error). Postfix `x++` uses the instance operator only when the result is unused. For reference types, null `x` throws `NullReferenceException`. `checked` variant requires the regular one. Can be `virtual`/`override`; `readonly` allowed on structs.
- **Gotchas:** No consistency check between `+` and `+=`: keep them semantically identical. Aliasing: in-place mutation of a reference type is visible through every reference to it (`var b = a; a += x;` also changes `b`), unlike the old "allocate new" semantics. Not CLS-compliant.
- **Performance:** Avoids allocations/copies for large mutable types (buffers, tensors, big integers, builders).
- **When not:** Immutable value types and types where users expect value semantics; keep only the static binary operator.
- **Source:** <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/user-defined-compound-assignment>

## Smaller C# 14 items

- **Ignored directives for file-based apps** (`#:package`, `#:sdk`, `#:property`, `#!` shebang) used by `dotnet run app.cs`; the compiler ignores them in project builds. Source: <https://learn.microsoft.com/dotnet/csharp/language-reference/preprocessor-directives#file-based-apps>
- **Optional and named arguments in expression trees**: C# 14 removes the error for calls in `Expression<...>` that omit optional arguments or use named ones. Listed for C# 14 in csharplang version history and in the C# 14 spec folder; the Learn "Expression trees: limitations" page still lists it as a limitation (stale). Source: <https://learn.microsoft.com/dotnet/csharp/language-reference/proposals/csharp-14.0/optional-and-named-parameters-in-expression-trees>
- **Async `Main` codegen update**: compiler-internal; no code changes needed (csharplang version history).
- Other .NET 10 compiler breaks worth knowing: warning on redundant `or` pattern (`is not null or 42`), enumerator state set to "after" on dispose, `extension`/`partial`/`scoped` keyword escapes. Source: Roslyn breaking changes .NET 10 page above.
