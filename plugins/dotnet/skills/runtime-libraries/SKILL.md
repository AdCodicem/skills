---
name: runtime-libraries
description: 'Use before writing, reviewing or optimizing any .NET code that calls the base class libraries, even a one-line snippet: System.Text.Json, LINQ and async LINQ over IAsyncEnumerable, collections, files, streams and ZIP, processes, cryptography and password hashing, threading, logging, performance. Applies what .NET 10 and 11 changed, for the project''s target framework: strict JSON options and JSON Lines, in-box System.Linq.AsyncEnumerable, LeftJoin and FullJoin, EqualityComparer.Create, Process.RunAndCaptureTextAsync, async ZIP and Zstandard, post-quantum crypto and PBKDF2, JIT escape analysis guidance, runtime async, NativeAOT, SYSLIB obsoletions and runtime breaking changes. Example requests: "parse this untrusted JSON", "map this IAsyncEnumerable with an async call", "hash this password", "run git and capture the output", "optimise cette boucle", "remplace System.Linq.Async". Not for UI frameworks.'
metadata:
  surfaces: claude-code
---

# .NET 10 and 11 runtime and libraries

Make general .NET code use the safest and fastest APIs the target framework
offers, and stop hand-optimizing what the runtime now does by itself. .NET 10 is
LTS; .NET 11 is STS (GA 2026-11-10). .NET 8 and 9 are out of support.

## Before writing code

1. **Detect the target** (use `python` if `python3` is missing):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/csharp/scripts/detect_target.py" <path>
   ```

   .NET 11 APIs need `net11.0`, or multi-targeting with
   `#if NET11_0_OR_GREATER`. Note `PublishAot` / `IsAotCompatible` (no
   reflection-based serialization, trimming-safe APIs only) and
   `InvariantGlobalization`.
2. **Load the reference you need**:
   - [references/libraries.md](references/libraries.md): System.Text.Json, collections, LINQ, strings, numerics, cryptography, diagnostics, process, IO, compression, networking.
   - [references/runtime.md](references/runtime.md): JIT, GC, escape analysis, bounds checks, runtime async, SIMD, NativeAOT.
   - [references/breaking-changes.md](references/breaking-changes.md): SYSLIB obsoletions, experimental IDs, and upgrade breaking changes for 10 and 11.
3. **When a detail is not covered or looks uncertain**, check Microsoft Learn
   with the `microsoft_docs_search` / `microsoft_docs_fetch` tools if they are
   available.

## Rules

- **Change only what the task needs.** New code uses current APIs; in existing
  code you touch, *mention* better APIs or obsolete calls, do not rewrite them
  unless asked.
- **Modern only when it improves the code**: safer, faster, or clearly shorter.
- **Never generate obsolete APIs** (SYSLIB0058-0066, listed in
  [references/breaking-changes.md](references/breaking-changes.md)) or the
  community `System.Linq.Async` package on `net10.0+`.
- **Experimental APIs** fail to compile until their SYSLIB5xxx diagnostic is
  suppressed: `SlhDsa`, `CompositeMLDsa`, `CompositeMLKem` (SYSLIB5006),
  caller-driven TLS sessions (SYSLIB5007), `Hpke` (SYSLIB5009), `Sve`
  (SYSLIB5003). Explain them; never introduce them or suppress the diagnostic
  unasked. `MLKem` and `MLDsa` are usable (check `IsSupported`).
- **Opt-in runtime features** (runtime async on .NET 11) are measured
  experiments, not defaults: propose them, do not enable them silently.

## Use this, not that

| Instead of | Prefer | Needs |
| --- | --- | --- |
| Lenient `JsonSerializer.Deserialize` of untrusted input | `JsonSerializerOptions.Strict`, or `AllowDuplicateProperties = false` | .NET 10 |
| Reflection-based JSON in AOT or hot paths | Source-generated `JsonSerializerContext` | any |
| `JsonDocument.Parse(json).RootElement` without disposing | `JsonElement.Parse(json)` | .NET 10 |
| JSON array for streamed records | `JsonSerializer.SerializeAsyncEnumerable(stream, items, topLevelValues: true)` (JSON Lines) | .NET 11 |
| `System.Linq.Async` package, `SelectAwait` | In-box `System.Linq.AsyncEnumerable`: `Select(async (T x, CancellationToken ct) => ...)` with explicit parameter types | .NET 10 |
| `GroupJoin` + `SelectMany` + `DefaultIfEmpty` | `LeftJoin` / `RightJoin`; `FullJoin` and tuple overloads | .NET 10 / 11 |
| Hand-written `IEqualityComparer<T>` class | `EqualityComparer<T>.Create(x => x?.Key, StringComparer.OrdinalIgnoreCase)` (the selector gets `T?`) | .NET 11 |
| Natural-sort comparer | `StringComparer.Create(culture, CompareOptions.NumericOrdering)` | .NET 10 |
| `new Rfc2898DeriveBytes(...)` + `GetBytes` | `Rfc2898DeriveBytes.Pbkdf2(password, salt, iterations, HashAlgorithmName.SHA256, 32)` | .NET 10 (SYSLIB0060) |
| `Find(X509FindType.FindByThumbprint, ...)` (SHA-1) | `FindByThumbprint(HashAlgorithmName.SHA256, thumbprint)` | .NET 10 |
| PFX export with 3DES/SHA-1 | `ExportPkcs12(Pkcs12ExportPbeParameters.Pbes2Aes256Sha256, password)` | .NET 10 |
| `RSACryptoServiceProvider.Encrypt(data, bool)` | `RSA.Create()` + `Encrypt(data, RSAEncryptionPadding.OaepSHA256)` | .NET 11 (SYSLIB0064) |
| Custom X25519 or key-wrap code | `X25519DiffieHellman`; `Aes.EncryptKeyWrapPadded` (10) / `EncryptKeyWrap` (11) | .NET 10 / 11 |
| `Process.Start` + `ReadToEnd` + `WaitForExit` | `await Process.RunAndCaptureTextAsync("git", ["status"])` | .NET 11 |
| `new MemoryStream(Encoding.UTF8.GetBytes(text))` | `new StringStream(text, Encoding.UTF8)`, `ReadOnlyMemoryStream` | .NET 11 |
| Sync `ZipFile` APIs in async code | `ZipFile.OpenReadAsync`, `ZipArchiveEntry.OpenAsync`, `ExtractToDirectoryAsync` | .NET 10 |
| Third-party Zstandard package | `ZstandardStream` in `System.IO.Compression` | .NET 11 |
| `Task.WhenAny(task, Task.Delay(t))` | `await task.WaitAsync(t, ct)` (CA2027) | any |
| `StreamReader.EndOfStream` in async loops | `while (await reader.ReadLineAsync(ct) is { } line)` (CA2024) | any |
| `lock (object)` | `System.Threading.Lock` | .NET 9 |
| String interpolation in log calls | `[LoggerMessage]` source generator (CA1873); generic methods allowed in 11 | any / .NET 11 |
| Manual `ActivityListener` to enable tracing | `AddTracing(t => t.EnableTracing(...))` | .NET 11 |
| `Regex` constructed per call | `[GeneratedRegex]` on a `partial` method; `IsMatch`, `Regex.Count` | any |

## Performance

- **Write idiomatic, safe code first and measure** (BenchmarkDotNet). .NET 10
  and 11 stack-allocate small non-escaping arrays, delegates and enumerators,
  devirtualize interface and generic calls, and remove more bounds checks.
  Do not add `stackalloc`, `ArrayPool`, struct enumerators, `Unsafe.Add`,
  pointers or `volatile` for small or unproven cases.
- Keep abstractions (`IEnumerable<T>`, `IReadOnlyList<T>`, interfaces); mark
  classes `sealed` when they are not designed for inheritance.
- Spans and `SearchValues<T>` remain the right tool for parsing and searching;
  C# 14 converts arrays and strings to spans implicitly.
- Portable `Vector128/256/512<T>` before platform intrinsics.
- `Task` by default; `ValueTask` only where completions are mostly synchronous
  and the result is awaited once.

## Security

- Untrusted JSON: `Strict` options or `AllowDuplicateProperties = false`, a
  source-generated contract, and `MaxDepth` left at its default or lower.
- Passwords: PBKDF2 through `Rfc2898DeriveBytes.Pbkdf2` with a random salt
  (`RandomNumberGenerator.GetBytes(16)`) and a high iteration count (OWASP
  suggests 600,000 for SHA-256), or a dedicated password hasher (ASP.NET Core
  Identity `PasswordHasher<T>`).
- Secrets and tokens: `RandomNumberGenerator.GetString/GetHexString`, never
  `Random`. Compare MACs with `CryptographicOperations.FixedTimeEquals`.
- Post-quantum: `MLKem` / `MLDsa` via static factories after `IsSupported`
  (needs OpenSSL 3.5+ or a Windows build with PQC); hybrid composites are
  experimental.
- SIGTERM: since .NET 10 the runtime installs no default handler; plain console
  apps use the Generic Host or `PosixSignalRegistration`.

## Modes

- **Writing code**: apply the rules and tables above.
- **Review**: report security issues first (obsolete crypto, lenient parsing of
  untrusted input, `Random` for secrets), then obsolete APIs, then performance
  (only with a reason or a measurement), then modernization.
- **Optimize on request**: measure first, change one thing at a time, keep the
  safe version when the gain is not measurable.
- **Upgrade**: follow [references/breaking-changes.md](references/breaking-changes.md)
  and the `migrate` skill. Pay attention to .NET 11 numeric behavior changes
  (correctly rounded `decimal` conversions and `Math.Round`, saturating
  float-to-small-integer casts) and the x86-64-v2 hardware baseline.

## Verify

- `dotnet build` with no new SYSLIB warnings; run the tests.
- For performance claims, a BenchmarkDotNet comparison of before and after.
- For AOT projects, `dotnet publish -c Release` with no trimming or AOT warnings.
