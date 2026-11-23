# Runtime, JIT, GC and NativeAOT in .NET 10 and 11

What changed in how code should be written for performance. Sources:
[.NET 10 runtime](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/runtime),
[.NET 11 runtime](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/runtime),
[Performance Improvements in .NET 10](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-10/),
[Performance Improvements in .NET 11](https://devblogs.microsoft.com/dotnet/performance-improvements-in-net-11/).

## Escape analysis / stack allocation (.NET 10, extended in .NET 11) - GA, automatic

- **What**: JIT stack-allocates objects that provably do not escape: small fixed-size arrays of value types and of reference types, delegates (the `Func` object; closure still heap-allocated in .NET 10), objects referenced from non-escaping local struct fields, and enumerators of arrays seen through `IEnumerable<T>` (conditional escape analysis + PGO). .NET 11 adds: nullable boxing passed to formatting, `foreach` over an `IEnumerable<int>` collection expression held in a field, `EqualityComparer<T>.Default.Equals` receivers, `ArgumentNullException.ThrowIfNull` on value-type generics without boxing, short-lived objects of exactly known type cast to interfaces. Delegates are 8 bytes smaller on CoreCLR in .NET 11.
- **Guidance**: Do not contort code (manual `stackalloc`, `ArrayPool` for 3-element arrays, hand-written struct enumerators, `ValueStopwatch`) solely to avoid small temporary allocations; write idiomatic code and measure. Keep `stackalloc`/pooling for large or variable-size buffers and hot paths proven by profiling. Escape analysis needs inlining; it is not guaranteed.
- **Old vs new**:

  ```csharp
  // Old habit: avoid the array "allocation"
  Span<int> numbers = stackalloc int[] { 1, 2, 3 };
  // .NET 10+: this local array is stack-allocated by the JIT when it does not escape
  int[] numbers = { 1, 2, 3 };
  ```

- **Source**: .NET 10 runtime page (Stack allocation, Escape analysis); Toub .NET 10 (Object Stack Allocation); Toub .NET 11 (Escape Analysis and Stack Allocation). `Stopwatch` now inlines so the instance can be stack-allocated (Toub .NET 10, Diagnostics).

## Devirtualization / de-abstraction - GA, automatic

- **.NET 10**: array interface methods (`IEnumerable<T>`, `IList<T>` over `T[]`) devirtualize and inline; late devirtualization after inlining; return-type refinement; methods with `try/finally` can inline; profile-guided inlining relaxes size limits; `EqualityComparer<T>.Default.Equals` guarded devirtualization in shared generic code.
- **.NET 11**: generic virtual methods (shared and non-shared) devirtualize, default interface methods on generic interfaces devirtualize, `Activator.CreateInstance<T>()` result treated as exact type, `Enum.Equals` on generic `T : Enum` becomes integer compare (no boxing), `string.Equals`/`SequenceEqual` on two constants fold. ReadyToRun now precompiles `Comparer<T>.Default`/`EqualityComparer<T>.Default` (up to 20x on collection ops). NativeAOT and R2R also benefit.
- **Guidance**: Keep abstractions (`IEnumerable<T>`, `IReadOnlyList<T>`, interfaces, small helpers, `try/finally`). Do not hand-flatten or convert to arrays for speed without measurement. Prefer `sealed` classes where appropriate (still helps devirtualization).
- **Source**: .NET 10 runtime page; .NET 11 runtime page (Devirtualization improvements, ReadyToRun improvements).

## Bounds-check elimination - GA, automatic

- **.NET 10**: `static readonly` array indexing, `ids[0]` then `ids[^1]`, span index after length check in any order, `switch (span.Length)` cases, loops over spans cloned like arrays.
- **.NET 11**: `i + cns < len`, `values[^1]`, `if (!span.IsEmpty && span[0] == x)`, `(uint)i < (uint)span.Length`, `span.Slice(span.Length - 4)` after a `>= 4` guard, multiple constant-index reads in one block (no need to read the largest index first), redundant `checked` context removal, `!=`-stride loops cloned.
- **Guidance**: Prefer safe, idiomatic span/array indexing over `Unsafe.Add`/pointers/`MemoryMarshal.GetReference` tricks. Toub (.NET 11) explicitly recommends rewriting hand-written unsafe loops with safe C# and re-measuring.
- **Source**: .NET 11 runtime page (JIT improvements); Toub .NET 10/11 (Bounds Checking).

## Runtime Async (.NET 11) - shipped, **opt-in per project** (not preview-gated for `net11.0`)

- **What**: The runtime (JIT) implements async suspension/resumption instead of compiler-generated state machines. The .NET 11 BCL itself is compiled with `runtime-async=on`. Benefits: real call stacks in live stack traces/profilers/debugger (5 frames vs 13 in docs sample), fewer allocations for synchronously completing chains (Toub: 21 ns/144 B to 6 ns/0 B in a two-layer benchmark), much cheaper exceptions crossing many async frames, async-aware profiler events. Continuations skip `ExecutionContext` capture/restore when no `AsyncLocal<T>` state is present (applies to `Task`/`ValueTask` generally, not only runtime-async).
- **Enable**:

  ```xml
  <PropertyGroup>
    <Features>$(Features);runtime-async=on</Features>
  </PropertyGroup>
  ```

  `<EnablePreviewFeatures>` is no longer required for `net11.0`. Opt out per project with `<UseRuntimeAsync>false</UseRuntimeAsync>`. The `DOTNET_RuntimeAsync` / `UNSUPPORTED_RuntimeAsync` env vars were removed.
- **Limits** (Toub .NET 11): supported return types `Task`, `Task<T>`, `ValueTask`, `ValueTask<T>`. Not yet: `async void`, async iterators (`IAsyncEnumerable<T>` producers), custom async method builders. Supports NativeAOT and ReadyToRun.
- **Guidance for skills**: No new C# syntax; write normal `async`/`await`. Do not rewrite clean `await` code to avoid intermediate `Task`s. Keep "`Task` by default, `ValueTask` only where its tradeoffs fit" (Toub quote paraphrased). Treat enabling as an opt-in performance/diagnostics switch to measure, not a default recommendation; Microsoft hopes to make it default in .NET 12. Exception stack traces (`ex.StackTrace`) look the same either way.
- **Source**: .NET 11 runtime page (Runtime Async); Toub .NET 11 (Runtime Async).

## Hardware baseline (.NET 11) - breaking

- x86/x64 minimum raised from `x86-64-v1` to `x86-64-v2` (SSE4.2, POPCNT, CX16) on all OSes; Windows Arm64 requires LSE. R2R targets: `x86-64-v3` (AVX2/BMI/FMA) on Windows/Linux; `armv8.0-a + LSE` Linux Arm64; `armv8.2-a + RCPC` Windows Arm64. Old CPUs fail with "The current CPU is missing one or more of the baseline instruction sets."
- **Source**: <https://learn.microsoft.com/en-us/dotnet/core/compatibility/jit/11/minimum-hardware-requirements>

## Floating-point to small-integer conversions saturate (.NET 11) - breaking

- Unchecked `float`/`double` to `sbyte`/`byte`/`short`/`ushort`/`char` now saturate at type bounds; NaN gives 0 (CoreCLR and NativeAOT, not Mono). Previously `(short)65578.0` gave 42.
- **Mitigation**: `double.ConvertToIntegerNative<T>(x)` for platform-native behavior, or `unchecked((ushort)(int)x)` to reproduce the .NET 9/10 sequence.
- **Source**: <https://learn.microsoft.com/en-us/dotnet/core/compatibility/jit/11/fp-to-small-integer>

## SIMD / intrinsics

| Item | Version | Status | Notes |
| --- | --- | --- | --- |
| `Avx10v2` intrinsics | 10 | GA API, JIT support **disabled by default** (no hardware at release) | <https://learn.microsoft.com/en-us/dotnet/core/whats-new/dotnet-10/runtime#avx102-support> . .NET 11 docs only mention an AVX10 detection fix and AVX10.1 used for `Half`; enablement of AVX10.2 by default in .NET 11 not confirmed. |
| Arm64 write-barrier improvements | 10 | GA, automatic | GC pause improvements 8-20%+. |
| Arm64 SVE nonfaulting loads need a mask parameter | 10 | Breaking (binary/source) | `Sve` is still `[Experimental]` SYSLIB5003. |
| Lane construction: `CreateGeometricSequence`, `CreateAlternatingSequence`, `CreateHarmonicSequence`, `Zip`/`ZipLower`/`ZipUpper`, `Unzip`/`UnzipEven`/`UnzipOdd`, `Concat*`, `Reverse` on `Vector64/128/256/512<T>` and `Vector<T>` | 11 | GA | Prefer over hand-written `Shuffle`/platform-specific intrinsics. |
| Hardware FP16 for `Half` (AVX10.1 / F16C on x64, FP16 on Arm64) | 11 | GA, automatic | No code change. |
| `AvxVnni.V512`, SVE2 narrowing-saturate, `CreateWhile` signed/float variants, `Sve2*` detection for AES/SHA3/SM4 | 11 | GA (SVE still experimental) | Niche. |

- **Guidance**: Write portable `Vector128/256/512` code first; drop to `Avx2`/`AdvSimd` only when the portable API cannot express the operation (Toub .NET 11).

## Other runtime items (.NET 11)

- `Guid.NewGuid()` on Linux uses `getrandom()` (about 12% faster). Machines with >1024 CPUs can initialize. In-process crash report: `DOTNET_EnableCrashReport=1` / `DOTNET_EnableCrashReportOnly=1` on Linux/macOS. iOS/tvOS disable advisory file locking by default (`System.IO.DisableFileLocking` runtimeconfig / `DOTNET_SYSTEM_IO_DISABLEFILELOCKING=0` to restore). Mobile moved from Mono to CoreCLR (MAUI breaking changes; out of scope).
- Threading (Toub .NET 11): `Monitor` Wait/Pulse bookkeeping moved onto the lock; many BCL fields dropped `volatile`; do not add `volatile` reflexively where `lock`/`Interlocked`/lazy init already give correctness. Thread pool overhead for small work items reduced.
- Threading (Toub .NET 10): new `Volatile.ReadBarrier()` / `Volatile.WriteBarrier()` for low-lock code only. `Task.WhenAll` with one task returns it directly. Thread pool moves a blocking worker's local queue to the global queue before blocking on a `Task`; sync-over-async is still wrong.

## NativeAOT

| Item | Version | Status | Notes / Source |
| --- | --- | --- | --- |
| Type preinitializer supports all `conv.*`/`neg` opcodes; more static ctors preinitialized | 10 | GA | .NET 10 runtime page. Keep static initialization simple. |
| Generic instantiation folding (smaller binaries) | 10 | GA | Toub .NET 10. |
| `<UseSizeOptimizedLinq>false</UseSizeOptimizedLinq>` restores speed-optimized LINQ | 10 | GA feature switch | Toub .NET 10. |
| HTTP/3 trimmed when `PublishTrimmed`/`PublishAot`; `<Http3Support>true</Http3Support>` restores | 10 | Breaking | compat page networking/10.0/http3-disabled-with-publishtrimmed |
| Single-file/NativeAOT no longer probe the app directory for native libs unless `DllImportSearchPath.AssemblyDirectory` | 10 | Breaking | interop/10.0/native-library-search |
| Faster interface dispatch via shared dispatch helper; GVM dispatch cells | 11 | GA | .NET 11 runtime page. |
| `Assembly.GetCallingAssembly()` works on NativeAOT when `StackTraceSupport` is on; throws `NotSupportedException` when it is off (both runtimes) | 11 | Behavior change | core-libraries/11/assembly-getcallingassembly-stacktracesupport-disabled |
| Unix native library outputs get `lib` prefix (`libmylib.so`); opt out `<UseNativeLibPrefix>false</UseNativeLibPrefix>` | 11 | Breaking | interop/11/nativeaot-lib-prefix |
| Non-blittable `[UnmanagedCallersOnly]` signatures rejected (fail fast); use `[assembly: DisableRuntimeMarshalling]` or blittable types (`byte`/`int` for bool, `ushort` for char) | 11 | Breaking | interop/11/unmanagedcallersonly-non-blittable |
| `Process` local-only APIs no longer pull remote-machine code (smaller AOT output) | 11 | GA | Toub .NET 11. |
