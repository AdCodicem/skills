# Base class libraries in .NET 10 and 11

Status: **GA** = supported; **Experimental** = `[Experimental("SYSLIB5xxx")]`, a
compile error until suppressed; **Opt-in** = shipped but off by default. Sources:
[.NET 10 libraries](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-10/libraries),
[.NET 11 libraries](https://learn.microsoft.com/dotnet/core/whats-new/dotnet-11/libraries).
The main .NET 10 APIs below were compiled against SDK 10.0.404, and the main
.NET 11 ones (comparers, joins, streams, Process, JSON Lines, X25519, key wrap,
Zstandard, Base64, regex) against SDK 11.0.100.

## System.Text.Json

| Item | Version | Status | What / guidance |
| --- | --- | --- | --- |
| `JsonSerializerOptions.AllowDuplicateProperties = false` (also `JsonDocumentOptions.AllowDuplicateProperties`) | 10 | GA | Throws `JsonException` on duplicate keys (objects, `JsonObject`, dictionaries, `JsonDocument`). Security hardening for untrusted input. |
| `JsonSerializerOptions.Strict` preset | 10 | GA | = `JsonUnmappedMemberHandling.Disallow` + no duplicates + case-sensitive + `RespectNullableAnnotations` + `RespectRequiredConstructorParameters`. Read-compatible with `Default`. Recommend for untrusted input/APIs where strictness is wanted. |
| `JsonSerializer.DeserializeAsync`/`DeserializeAsyncEnumerable` from `PipeReader` | 10 | GA | Skip `PipeReader.AsStream()`. |
| `ReferenceHandler` in `[JsonSourceGenerationOptions(ReferenceHandler = JsonKnownReferenceHandler.Preserve)]` | 10 | GA | Cycles with source gen. |
| `JsonElement.Parse(...)` | 10 | GA | Standalone element; do not return `JsonDocument.Parse(json).RootElement` without disposing the document. |
| `JsonObject.TryAdd`, `TryGetPropertyValue` with index; `JsonArray.RemoveAll`/`RemoveRange` | 10 | GA | Avoid `RemoveAt(0)` loops (O(N^2)). |
| `Utf8JsonWriter.WriteStringValueSegment` / `WriteBase64StringSegment`; `JsonMarshal.GetRawUtf8PropertyName` | 10 | GA | Stream large values without buffering. |
| Property name conflict check (`$type`, `$id`, `$ref`, custom discriminator) | 10 | Breaking | `InvalidOperationException` at contract creation; rename or `[JsonIgnore]`. |
| C# 15 union serialization (active case written directly; `[JsonUnion(TypeClassifier = typeof(JsonUnionTypeStructuralClassifier))]` for object cases; custom `JsonTypeClassifierFactory`) | 11 | GA | Requires C# 15 unions. F# DU support is reflection-only (no source gen/AOT). |
| JSON Lines: `JsonSerializer.SerializeAsyncEnumerable(stream/pipeWriter, items, topLevelValues: true)` | 11 | GA | One compact value + `\n` per item; streams entries. Default (`false`) writes a JSON array. |
| `InferClosedTypePolymorphism` (options, source-gen options, `[JsonPolymorphic]`) for C# 15 `closed` hierarchies; open-generic `[JsonDerivedType(typeof(Derived<>), "d")]` | 11 | GA | Explicit `[JsonDerivedType]` replaces inferred list. SYSLIB1229 for unresolved registrations. |
| Source gen: non-public `[JsonInclude]` members/fields, inaccessible `[JsonConstructor]`, init-only defaults preserved; ctor params with `in`/`ref`/`ref readonly`/`out` | 11 | GA | Fewer reasons to fall back to reflection. |
| `JsonSerializerOptions.GetTypeInfo<T>()` / `TryGetTypeInfo<T>(out JsonTypeInfo<T>?)` | 11 | GA | No cast from `GetTypeInfo(typeof(T))`. |
| `JsonNamingPolicy.PascalCase`, `[JsonNamingPolicy]` on type/member, type-level `[JsonIgnore(Condition = ...)]` | 11 | GA | Precedence: `[JsonPropertyName]` > member policy > type policy > options policy. `Always` invalid at type level (SYSLIB1226). |
| Built-in converters for `BFloat16`, `Decimal32/64/128`; open generic `[JsonConverter(typeof(OptionConverter<>))]`; `IReadOnlyDictionary` extension data; `IReadOnlySet<T>` support | 11 | GA | No `JsonConverterFactory` needed for open generics. |
| `Utf8JsonWriter.Reset(Stream/IBufferWriter, JsonWriterOptions)` | 11 | GA | Reuse/pool writers with different options. |
| Perf (11): faster default escaping and whitespace skipping | 11 | automatic | Toub .NET 11. |

Old vs new (strict deserialization of untrusted JSON):

```csharp
// Old: lenient defaults, last duplicate wins, unknown members ignored
var order = JsonSerializer.Deserialize<Order>(json);
// .NET 10+
var order = JsonSerializer.Deserialize<Order>(json, JsonSerializerOptions.Strict);
// or targeted: new JsonSerializerOptions { AllowDuplicateProperties = false }
```

Prefer source-generated contexts (`JsonSerializerContext`) for AOT/trimming; set `Strict`-equivalent settings via `[JsonSourceGenerationOptions]` (verify property names per option; `JsonSerializerDefaults` has no `Strict` enum value confirmed in sources).

---

## Collections

| Item | Version | Status | What / guidance |
| --- | --- | --- | --- |
| `OrderedDictionary<TKey,TValue>.TryAdd(key, value, out int index)`, `TryGetValue(key, out value, out int index)` then `GetAt`/`SetAt` | 10 | GA | Add-or-update with one lookup (10-20% faster `JsonObject` updates). |
| `foreach` over `IEnumerable<T>` backed by `T[]`/`List<T>` may avoid enumerator allocation | 10 | automatic | See [runtime.md](runtime.md). |
| `BitArray` byte-backed; `CollectionsMarshal.AsBytes(BitArray)` | 10 | GA | Vectorized bit work. |
| Public `InlineArray2<T>`... types | 10 | GA | |
| `MemoryExtensions` search overloads accepting `IEqualityComparer<T>?`/`IComparer<T>` without `IEquatable<T>` constraint; `CountAny`, `ReplaceAny` | 10 | GA | |
| `EqualityComparer<T>.Create(keySelector, keyComparer?)` | 11 | GA | Replaces hand-written comparer classes. |
| `BitArray(ReadOnlySpan<bool/byte/int>)` ctors, `BitArray.PopCount()` | 11 | GA | |
| `ConcurrentQueue<T>.TryDequeue/TryPeek` spurious-empty fix | 11 | GA fix | |
| Perf (11): `HashSet.UnionWith` into empty set clones, immutable `SetEquals`, `FrozenDictionary` construction, `ImmutableArray.Create(array, start, length)` | 11 | automatic | |

```csharp
// Old: custom IEqualityComparer<Person> class
// .NET 11
// The key selector receives T?: `p => p.Name` warns CS8602 with nullable enabled.
var byName = EqualityComparer<Person>.Create(p => p?.Name, StringComparer.OrdinalIgnoreCase);
var set = new HashSet<Person>(byName);
```

```csharp
// .NET 10: OrderedDictionary add-or-increment with a single hash lookup
if (!counts.TryAdd(key, 1, out int i)) counts.SetAt(i, counts.GetAt(i).Value + 1);
```

---

## LINQ and async LINQ

| Item | Version | Status | What / guidance |
| --- | --- | --- | --- |
| `System.Linq.AsyncEnumerable` in the BCL (full LINQ over `IAsyncEnumerable<T>`); `System.Linq.AsyncEnumerable` NuGet for older TFMs | 10 | GA, **breaking** | Replaces community `System.Linq.Async` (Ix.NET). Remove that package or move to v7.0.0; multitarget via `System.Linq.AsyncEnumerable` package; transitive refs: `<ExcludeAssets>compile</ExcludeAssets>`. Renames: `SelectAwait(async (x, ct) => ...)` becomes `Select(async (x, ct) => ...)` (overloads take async lambdas with `CancellationToken`). **Give the lambda parameters explicit types**: `Select(async (int x, CancellationToken ct) => ...)`; `(x, ct) =>` is ambiguous with the index overload (CS0121). <https://learn.microsoft.com/en-us/dotnet/core/compatibility/core-libraries/10.0/asyncenumerable> |
| `Enumerable/Queryable.LeftJoin`, `RightJoin` (result-selector overloads) | 10 | GA | Replaces `GroupJoin`+`SelectMany`+`DefaultIfEmpty`. EF Core 10 translates them. No query-syntax form. <https://learn.microsoft.com/en-us/dotnet/csharp/linq/standard-query-operators/join-operations> |
| `Enumerable.Shuffle()`, `Enumerable.Sequence<T>(start, endInclusive, step)` (`T : INumber<T>`) | 10 | GA | `Shuffle` uses non-crypto RNG; cheap with `Take(n)`. `AsyncEnumerable.Shuffle` also exists. |
| `FullJoin`; tuple-returning `Join`, `GroupJoin`, `LeftJoin`, `RightJoin`, `FullJoin` overloads (no result selector, optional `IEqualityComparer<TKey>`) on `Enumerable`, `Queryable`, `AsyncEnumerable` | 11 | GA | Deconstruct: `foreach (var (p, c) in products.LeftJoin(categories, p => p.CategoryId, c => c.Id))`. Inner side is `TInner?` (default when no match). Inference: tuple overloads are .NET 11 (docs list them as .NET 11 additions). |
| Perf (11): `AsyncEnumerable.Append` chains linear (was quadratic); `Max/Min` on small ints, `Sum<int>` faster | 11 | automatic | |
| `Queryable.MaxBy/MinBy` taking `IComparer<TSource>` obsolete (SYSLIB0061); use `IComparer<TKey>` overloads | 10 | Obsoletion | |
| C# 14 span overload resolution: `array.Contains(x)` inside `Expression<>` now binds to `MemoryExtensions.Contains` and fails with `Compile(preferInterpretation: true)` | 10 | Breaking (behavioral) | Cast to `IEnumerable<T>`/`AsEnumerable()` or call `Enumerable.Contains(...)` explicitly in expression trees. <https://learn.microsoft.com/en-us/dotnet/core/compatibility/core-libraries/10.0/csharp-overload-resolution> |

```csharp
// Old left outer join
var q = students.GroupJoin(depts, s => s.DeptId, d => d.Id, (s, ds) => new { s, ds })
                .SelectMany(x => x.ds.DefaultIfEmpty(), (x, d) => new { x.s.Name, Dept = d?.Name });
// .NET 10
var q = students.LeftJoin(depts, s => s.DeptId, d => d.Id, (s, d) => new { s.Name, Dept = d?.Name });
// .NET 11 tuple form
foreach (var (s, d) in students.LeftJoin(depts, s => s.DeptId, d => d.Id)) { /* d may be null */ }
```

---

## Strings, spans, text, encoding

| Item | Version | Status | What / guidance |
| --- | --- | --- | --- |
| Span normalization: `GetNormalizedLength`, `IsNormalized`, `TryNormalize` on `ReadOnlySpan<char>` (`StringNormalizationExtensions`) | 10 | GA | Avoid allocating strings to normalize. |
| `CompareOptions.NumericOrdering` (`StringComparer.Create(culture, CompareOptions.NumericOrdering)`) | 10 | GA | "Windows 8" < "Windows 10"; "02" == "2". Not valid for `IndexOf`/`StartsWith`/`EndsWith`/`IsPrefix`/`IsSuffix`. Replace hand-written natural-sort comparers. |
| UTF-8 hex: `Convert.FromHexString(ReadOnlySpan<byte>...)`, `TryToHexString`, `TryToHexStringLower` (UTF-8 destinations) | 10 | GA | |
| `PemEncoding.FindUtf8` | 10 | GA | Parse PEM bytes without transcoding. |
| `Guid`/`Version`/`IPAddress`/`IPNetwork` UTF-8 parsing; `IPAddress.IsValid`/`IsValidUtf8` | 10 | GA | |
| `DefaultInterpolatedStringHandler.Text` | 10 | GA | |
| `Random.GetString(choices, length)`, `Random.GetHexString(...)` | 10 per Toub; API pages confirm existence | GA | For non-security strings; use `RandomNumberGenerator.GetString/GetHexString` (since .NET 8) for secrets. |
| `TimeSpan.FromMilliseconds(long)` single-arg overload; `ISOWeek` `DateOnly` overloads | 10 | GA | |
| `Rune` overloads on `string` (`Contains`, `StartsWith`, `EndsWith`, `IndexOf`, `LastIndexOf`, `Replace`, `Split`, `Trim*`), `TextInfo.ToLower/ToUpper(Rune)`, `char.Equals(char, StringComparison)` | 11 | GA | |
| `StringBuilder.MoveChunks(source)` | 11 | GA | Transfer content without copying. |
| `Base64` (System.Buffers.Text) new `EncodeToChars`, `EncodeToString`, `EncodeToUtf8`, `DecodeFromChars`, `DecodeFromUtf8` | 11 | GA | Allocating + span-based forms. |
| `Utf16.IsValid`, `Utf8.IndexOfInvalidSubsequence`, `Utf16.IndexOfInvalidSubsequence` | 11 | GA | Precise invalid-encoding errors. |
| `RegexOptions.AnyNewLine` | 11 | GA | `^`/`$`/`.` treat `\r\n`, `\u0085`, ` `, ` ` as line terminators. |
| Floating-point hex: `value.ToString("X")`, `double.Parse(s, NumberStyles.HexFloat)` for `double`/`float`/`Half` | 11 | GA | Bit-exact round-trip. |
| `INumberBase<TSelf>.TryParsePartial` | 11 | GA | Delimited parsing without substrings. |
| In-memory streams: `ReadOnlyMemoryStream`, `WritableMemoryStream`, `ReadOnlySequenceStream`, `StringStream` | 11 | GA | Replace `new MemoryStream(array)` copies / `Encoding.GetBytes` + `MemoryStream`. |
| CBOR incremental reading (`isFinalBlock: false`, `CborReaderState.NeedsMoreData`, `SlideData`; requires `CborConformanceMode.Lax`) | 11 | GA | Plus default max depth (breaking, below). |
| Regex guidance (Toub .NET 10/11) | 10/11 | analyzers | Prefer `[GeneratedRegex]`; `IsMatch` over `Match(...).Success` (CA1874); `Regex.Count` over `Matches(...).Count` (CA1875); cache `SearchValues<T>`; `ContainsAny*` over `IndexOfAny*(...) >= 0`. |
| IO guidance (Toub .NET 10) | 10 | analyzer | Do not use `StreamReader.EndOfStream` in async code (CA2024); loop `while (await reader.ReadLineAsync(ct) is string line)`. |

```csharp
// Old
using var ms = new MemoryStream(Encoding.UTF8.GetBytes(yaml));
// .NET 11
using Stream s = new StringStream(yaml, Encoding.UTF8);
```

---

## Numerics and tensors

| Item | Version | Status | Notes |
| --- | --- | --- | --- |
| `System.Numerics.Tensors`: `Tensor<T>`, `TensorSpan<T>`, `ReadOnlyTensorSpan<T>`, `IReadOnlyTensor` | 10 | **GA (no longer experimental)**, NuGet package | Slices no longer copy; operators via C# 14 extension operators when `T` supports generic-math interfaces. New `TensorPrimitives` ops (`StdDev`, `Average`, `Clamp`, `DivRem`, `IsNaN`, `IsPow2`, `HammingBitDistance`), `Half` vectorized. |
| Tensor shape alignment and storage-layout validation | 11 (package update, also affects older TFMs) | Breaking | Overlapping copies rejected; use separate destination. |
| `Matrix4x4.CreateBillboardLeftHanded`, `CreateConstrainedBillboardLeftHanded` | 10 | GA | |
| Consistent masked shifts in generic math for small integer types | 10 | Breaking | |
| `Decimal32`, `Decimal64`, `Decimal128` (IEEE 754-2019 decimal FP) | 11 | GA | Use when IEEE decimal semantics/interop needed; `decimal` remains the default for money. |
| `Complex<T>` generic | 11 | GA | `float`, `Half`, `BFloat16`, decimal FP types. |
| `Random.NextInteger<T>()`, `Random.NextBinaryFloat<T>()` | 11 | GA | Generic math. |
| `BitConverter` `BFloat16` methods | 11 | GA | |
| Correctly rounded `decimal`/`BigInteger` to/from binary FP; correctly rounded `Math.Round(x, digits)`; `Complex` special values follow C23 Annex G | 11 | Breaking (behavioral) | Use `m` literals; see [breaking-changes.md](breaking-changes.md). |
| `Math.BigMul(long,long,out long)` single `MUL` on x64; faster `BigInteger` | 11 | automatic | |

---

## Cryptography and security

| Item | Version | Status | What / guidance |
| --- | --- | --- | --- |
| `MLKem` (FIPS 203) | 10 | GA type; **some methods `[Experimental]`** (SYSLIB5006) | Static factories: `MLKem.GenerateKey(MLKemAlgorithm.MLKem768)`, `ImportFromPem`, `IsSupported`. Needs OpenSSL 3.5+ or Windows CNG with PQC. |
| `MLDsa` (FIPS 204): `SignData`/`VerifyData`, `SignPreHash`/`VerifyPreHash` (OID string), `SignMu`/`VerifyMu` | 10 | **GA**: compiles without SYSLIB5006 on SDK 10.0.404 (the .NET 10 what's-new page still calls it experimental) | `MLDsa.GenerateKey(MLDsaAlgorithm.MLDsa65)` after `MLDsa.IsSupported`. Also downlevel in `Microsoft.Bcl.Cryptography`. |
| `SlhDsa` (FIPS 205) | 10 | **Experimental** SYSLIB5006 (confirmed by compiling) | Do not introduce unless asked. |
| `CompositeMLDsa` / `CompositeMLDsaAlgorithm` (IETF draft; draft-08 at .NET 10 GA) | 10 | **Experimental** SYSLIB5006 | .NET 11 Windows: only native CNG sets `MLDsa44WithECDsaP256`, `MLDsa65WithECDsaP256`, `MLDsa65WithECDsaP384`, `MLDsa87WithECDsaP384`; check `CompositeMLDsa.IsAlgorithmSupported`. |
| PQC member rename `SecretKey` to `PrivateKey` (`ImportMLDsaPrivateKey`, `PrivateKeySizeInBytes`, ...) | 10 | Breaking (source) | Never generate `...SecretKey` names. |
| AES-KWP (RFC 5649): `Aes.EncryptKeyWrapPadded`, `DecryptKeyWrapPadded`, `TryDecryptKeyWrapPadded`, `GetKeyWrapPaddedLength` | 10 | GA | Key wrapping (CMS, JOSE). |
| AES-KW unpadded (RFC 3394): `Aes.EncryptKeyWrap`, `DecryptKeyWrap`, `TryDecryptKeyWrap`, `GetKeyWrapLength` (plaintext multiple of 8 bytes) | 11 | GA | |
| `X509Certificate2Collection.FindByThumbprint(HashAlgorithmName.SHA256, thumbprint)` | 10 | GA | Replaces `Find(X509FindType.FindByThumbprint, ...)` (SHA-1 only). |
| `X509Certificate.ExportPkcs12(Pkcs12ExportPbeParameters.Pbes2Aes256Sha256, password)` (or `PbeParameters` overload) | 10 | GA | Prefer AES-256/SHA-256 PFX over 3DES/SHA-1 unless legacy readers need `Pkcs12TripleDesSha1`. |
| `PemEncoding.FindUtf8`; `SymmetricAlgorithm.SetKey(ReadOnlySpan<byte>)`; `ProtectedData` span overloads | 10 | GA | |
| `X25519DiffieHellman` (`GenerateKey()`, `DeriveRawSecretAgreement`, PKCS#8/SPKI/PEM import/export; `X25519DiffieHellmanCng`/`OpenSsl`) | 11 | GA | Portable X25519 key agreement. |
| `CryptographicOperations.FixedTimeEquals(ReadOnlySpan<byte>, byte)` | 11 | GA | |
| `CompositeMLKem` | 11 | **Experimental** SYSLIB5006 | |
| `Hpke` (RFC 9180; `HpkeSuite`, `HpkeKem`, `HpkeKdf`, `HpkeAead`, `Seal`/`Open`) | 11 | **Experimental** SYSLIB5009 | Managed implementation; check `Hpke.IsSupported(suite)`. |
| `EnvelopedCms` ML-KEM recipients | 11 | GA, non-Windows only, pure ML-KEM | |
| `TlsContext`, `TlsSession`, `TlsBufferSession`, `TlsSocketSession`, `TlsOperationStatus` | 11 | **Experimental** SYSLIB5007 | Caller-driven TLS state machine. |
| TLS 1.3 client on macOS via Network.framework: `AppContext.SetSwitch("System.Net.Security.UseNetworkFramework", true)` or `DOTNET_SYSTEM_NET_SECURITY_USENETWORKFRAMEWORK=1` | 10 | Opt-in | |
| `SslStream` Linux cert-validation failures sent as TLS alerts; Unix channel-binding validation | 11 | GA | |
| Obsoletions: SYSLIB0058 (`SslStream.CipherAlgorithm`/`HashAlgorithm`/`KeyExchangeAlgorithm`... use `NegotiatedCipherSuite`), SYSLIB0060 (`Rfc2898DeriveBytes` ctors, use `Rfc2898DeriveBytes.Pbkdf2`), SYSLIB0064 (`RSACryptoServiceProvider.Encrypt/Decrypt(byte[], bool)`, use `RSAEncryptionPadding` overloads), SYSLIB0065 (`AsnEncodedData.RawData` setter) | 10/11 | Warnings | See [breaking-changes.md](breaking-changes.md). |

```csharp
// Old (SYSLIB0060)
using var kdf = new Rfc2898DeriveBytes(password, salt, 100_000, HashAlgorithmName.SHA256);
byte[] key = kdf.GetBytes(32);
// New
byte[] key = Rfc2898DeriveBytes.Pbkdf2(password, salt, 600_000, HashAlgorithmName.SHA256, 32);
```

```csharp
// PQC pattern: static factory, IsSupported check, no AsymmetricAlgorithm base
if (MLKem.IsSupported)
{
    using MLKem key = MLKem.GenerateKey(MLKemAlgorithm.MLKem768);
    string spki = key.ExportSubjectPublicKeyInfoPem();
}
```

(Iteration count 600,000 above follows OWASP-style guidance; not from the .NET sources.)

---

## Diagnostics, OpenTelemetry, process, IO, compression, networking

### Diagnostics / OTel

| Item | Version | Status | Notes |
| --- | --- | --- | --- |
| `ActivitySourceOptions` (+ `TelemetrySchemaUrl`), `ActivitySource(ActivitySourceOptions)`, `Meter.TelemetrySchemaUrl` | 10 | GA | |
| Out-of-proc serialization of `ActivityEvent`/`ActivityLink`; rate-limiting sampler `[AS]*/-ParentRateLimitingSampler(100)` | 10 | GA | |
| Default propagator is W3C (`baggage` header) | 10 | Breaking | Restore: `DistributedContextPropagator.Current = DistributedContextPropagator.CreatePreW3CPropagator();` |
| `PropagationData` sampling no longer inherits `Recorded` | 10 | Breaking | Only matters for custom `ActivityListener.Sample`. |
| CA1873: avoid expensive argument evaluation at disabled log levels | 10 (analyzer improved in 11) | Analyzer | Use `[LoggerMessage]` source gen. |
| `AddTracing(t => t.EnableTracing(sourceName: ...).DisableTracing(...))` rules in `Microsoft.Extensions.Diagnostics`; `ActivitySourceFactory`; `ActivitySource` unsealed | 11 | GA | Declarative tracing config instead of manual `ActivityListener`. |
| `MemoryCache` built-in OTel metrics (`TrackStatistics = true`; meter `Microsoft.Extensions.Caching.Memory.MemoryCache`; `dotnet.cache.requests` with tag `dotnet.cache.request.result`) | 11 | GA | |
| HTTP `open_connections`/`active_requests` are observable instruments | 11 | Breaking for raw `MeterListener` | Call `RecordObservableInstruments()`. |
| Generic `[LoggerMessage]` methods (avoid boxing) | 11 | GA | `allows ref struct` unsupported (SYSLIB1011). |
| Observable instruments returning single `T`/`Measurement<T>` avoid allocation | 11 | automatic | |

### Process

| Item | Version | Status | Notes |
| --- | --- | --- | --- |
| `ProcessStartInfo.CreateNewProcessGroup` (Windows) | 10 | GA | Signal isolation. |
| .NET runtime no longer installs SIGTERM / `CTRL_CLOSE`/`CTRL_SHUTDOWN` handlers | 10 | Breaking | Generic Host handles it; otherwise `PosixSignalRegistration.Create(PosixSignal.SIGTERM, _ => Environment.Exit(0))`. |
| `Process.RunAsync`, `Process.RunAndCaptureTextAsync(file, args)` returning `ProcessTextOutput`, `ReadAllText/Bytes/Lines(Async)`, `ProcessOutputLine` | 11 | GA | Replaces `OutputDataReceived` event plumbing and deadlock-prone `StandardOutput.ReadToEnd()` + `WaitForExit()` patterns. |
| `Process.StartAndForget`, `ProcessStartInfo.StartDetached`, `KillOnParentExit` (Windows), `InheritedHandles`, `StandardInput/Output/ErrorHandle`, `StartSuspended` + `SafeProcessHandle.Resume()` | 11 | GA | |
| `Process.TryGetProcessById`, `SafeProcessHandle.Open/TryOpen/Start/Kill/Signal/WaitForExitAsync/ProcessId`, `Process.Signal(PosixSignal)`, `WaitForExitStatus(Async)` -> `ProcessExitStatus` | 11 | GA | |
| Windows redirected stdout/stderr use overlapped IO | 11 | automatic | |

```csharp
// Old
var psi = new ProcessStartInfo("git", "status --porcelain") { RedirectStandardOutput = true };
using var p = Process.Start(psi)!;
string output = await p.StandardOutput.ReadToEndAsync();
await p.WaitForExitAsync();
// .NET 11
ProcessTextOutput r = await Process.RunAndCaptureTextAsync("git", ["status", "--porcelain"]);
Console.WriteLine($"{r.ExitStatus.ExitCode}: {r.StandardOutput}");
```

### IO / compression

| Item | Version | Status | Notes |
| --- | --- | --- | --- |
| Async ZIP: `ZipArchive.CreateAsync`, `ZipArchiveEntry.OpenAsync`, `ZipFile.CreateFromDirectoryAsync`, `ExtractToDirectoryAsync`, `OpenAsync`, `OpenReadAsync`, `ZipFileExtensions.CreateEntryFromFileAsync`/`ExtractToDirectoryAsync`/`ExtractToFileAsync` | 10 | GA | Use in async code instead of sync ZIP APIs. Update mode no longer loads all entries. |
| `GZipStream` concatenated streams faster; zlib-ng | 10 | automatic | |
| `BufferedStream.WriteByte` no implicit flush | 10 | Breaking | Call `Flush()`. |
| Tar entries omit atime/ctime by default | 10 | Breaking | |
| `ZipArchiveEntry.Open(FileAccess)`/`OpenAsync(FileAccess, ct)`, `CompressionMethod`; password-protected entries (`Open(ReadOnlySpan<char>)`, `ZipEncryptionMethod`) | 11 | GA | |
| ZIP CRC32 validation (throws `InvalidDataException`) | 11 | Breaking | |
| `ZipArchive.CreateAsync` eagerly reads central directory | 11 | Breaking | Errors surface at `CreateAsync`. |
| Zstandard (`ZstandardStream`, `ZstandardEncoder`, `ZstandardDictionary.Train/Create`) in `System.IO.Compression` | 11 | GA | |
| Streamless `DeflateEncoder/Decoder`, `ZLibEncoder/Decoder`, `GZipEncoder/Decoder` (span-based, `Reset()`) | 11 | GA | |
| `DeflateStream`/`GZipStream` write header/footer for empty payload | 11 | Breaking | |
| `TarFile.CreateFromDirectory(..., format: TarEntryFormat.Gnu)`; GNU sparse 1.0; header checksum validation; hard links as `HardLink` entries | 11 | GA / Breaking | `TarWriterOptions { HardLinkMode = TarHardLinkMode.CopyContents }` to keep old behavior. |
| `SafeFileHandle.Type`, `SafeFileHandle.CreateAnonymousPipe`, `RandomAccess.Read/Write` on pipes | 11 | GA | |
| `IsAsync` on Unix reflects `O_NONBLOCK` | 11 | Breaking | |

### Networking (BCL only)

| Item | Version | Status |
| --- | --- | --- |
| `WebSocketStream.Create`, `CreateReadableMessageStream`, `CreateWritableMessageStream` | 10 | GA |
| `Uri` length limit removed; `MailAddress` rejects consecutive dots | 10 | Breaking |
| `GZipCompressedContent`, `BrotliCompressedContent`, `ZstandardCompressedContent` request bodies; `SocketsHttpHandler.ShouldEvictConnection`, `InitialHttp2MaxConcurrentStreams`; `Dns.ResolveSrv/Mx/Txt/CName/Ptr/Ns(Async)` + `DnsResolver`; HTTP/2 auto-downgrade for NTLM/Negotiate; `QuicStream.Priority`; `MediaTypeNames.Video` | 11 | GA |
| `SslStream` server-side AIA downloads off by default; Linux AIA fetch limit 2; `Uri`/`UriBuilder` stricter | 11 | Breaking |

### Misc .NET 11 platform

- `Microsoft.Extensions.*.Abstractions`, `Options`, `Primitives` (9 packages) are in the base shared framework for `net11.0`; explicit `PackageReference` gives NU1510. Remove or condition them.
- Async DataAnnotations (`AsyncValidationAttribute`, `IAsyncValidatableObject`, `Validator.ValidateObjectAsync`); `IAsyncStartupValidator` replaces obsolete `IStartupValidator` (SYSLIB0066); `OptionsBuilder.Validate<TValidator>()`; `ChangeToken.OnChange(Func<Task>)`; `[ConfigurationIgnore]`.
- `Type.GetNullableUnderlyingType()`; `AssemblyLoadContext.SetAssemblyLocationOverride`; `MetadataLoadContext.GetLoadContext`; `Uri.UriSchemeData`; `StringSyntaxAttribute.CSharp/FSharp/VisualBasic`; `UnionAttribute`/`IUnion` (compiler-facing); `Console` honors `FORCE_COLOR`.
- Reflection guidance (Toub .NET 10): prefer `[UnsafeAccessor]` (and `[UnsafeAccessorType]` in .NET 10) over `FieldInfo.GetValue` for private access; prefer `PinnedGCHandle<T>`/`GCHandle<T>`/`WeakGCHandle<T>` (typed, `IDisposable`) over `GCHandle.Alloc(..., Pinned)`.
- Analyzer CA2027 (Toub .NET 11): flags `Task.WhenAny(task, Task.Delay(timeout))`; use `task.WaitAsync(timeout, ct)`.

### TimeProvider, Channels, IAsyncEnumerable

- **TimeProvider**: no new public API found for .NET 10 or .NET 11 in the what's-new pages (it shipped in .NET 8). Keep recommending `TimeProvider` + `FakeTimeProvider` for testable time. Note `Environment.TickCount(64)` on Windows now excludes sleep/hibernate (.NET 11 breaking).
- **Channels**: .NET 10 fixes accumulation of canceled waiters (no API change). Toub .NET 10 mentions a new "unbuffered" channel implementation (dotnet/runtime#116097) but **its public factory name could not be verified** on Learn; do not generate code for it.
- **IAsyncEnumerable**: LINQ is in-box (see LINQ above). JSON Lines streaming (see System.Text.Json above). Runtime async does not yet cover async iterators.
