# Obsoletions, experimental APIs and breaking changes (runtime and libraries)

## Obsoletions (SYSLIB0xxx) and experimental IDs Claude must respect

| ID | Version | API | Use instead |
| --- | --- | --- | --- |
| SYSLIB0058 | 10 | `SslStream.KeyExchangeAlgorithm/KeyExchangeStrength/CipherAlgorithm/CipherStrength/HashAlgorithm/HashStrength`, `ExchangeAlgorithmType`, `CipherAlgorithmType`, `HashAlgorithmType` | `SslStream.NegotiatedCipherSuite` |
| SYSLIB0059 | 10 | `SystemEvents.EventsThreadShutdown` | `AppDomain.ProcessExit` |
| SYSLIB0060 | 10 | `Rfc2898DeriveBytes` constructors | `Rfc2898DeriveBytes.Pbkdf2(...)` static |
| SYSLIB0061 | 10 | `Queryable.MaxBy/MinBy` with `IComparer<TSource>` | overloads with `IComparer<TKey>` |
| SYSLIB0062 | 10 | `XsltSettings.EnableScript` | none (do not enable XSLT script) |
| SYSLIB0063 | 11 | `NamedPipeClientStream(PipeDirection, bool, bool, SafePipeHandle)` | ctor without `isConnected` |
| SYSLIB0064 | 11 | `RSACryptoServiceProvider.Encrypt/Decrypt(byte[], bool)` | `Encrypt/Decrypt(byte[], RSAEncryptionPadding)` (prefer `RSA.Create()` + `RSAEncryptionPadding.OaepSHA256`) |
| SYSLIB0065 | 11 | `AsnEncodedData.RawData` setter | constructor of the specific type, or `AsnEncodedData.CopyFrom` |
| SYSLIB0066 | 11 | `IStartupValidator` | `IAsyncStartupValidator` (do not register under both) |

Experimental (compile error unless suppressed): SYSLIB5001 was `Tensor<T>` in .NET 9 (**no longer experimental in .NET 10**); SYSLIB5003 `Sve`; SYSLIB5006 PQC (`SlhDsa`, `CompositeMLDsa`, some `MLKem` members, `CompositeMLKem`; `MLDsa` is GA: no SYSLIB5006 when compiled against SDK 10.0.404); SYSLIB5007 caller-driven TLS sessions (.NET 11); SYSLIB5009 `Hpke` (.NET 11). The experimental-overview page currently lists only through SYSLIB5006, so 5007/5009 come from the .NET 11 libraries page.

Sources: <https://learn.microsoft.com/en-us/dotnet/core/compatibility/core-libraries/10.0/obsolete-apis> , <https://learn.microsoft.com/en-us/dotnet/core/compatibility/core-libraries/11/obsolete-apis> , <https://learn.microsoft.com/en-us/dotnet/core/compatibility/cryptography/11/obsolete-apis> , <https://learn.microsoft.com/en-us/dotnet/fundamentals/syslib-diagnostics/experimental-overview>

---

## Breaking changes when upgrading (runtime/libraries only)

URL prefix: `https://learn.microsoft.com/en-us/dotnet/core/compatibility/`

## Breaking changes when upgrading: To .NET 10

| Change | Type | Mitigation | Page |
| --- | --- | --- | --- |
| `System.Linq.AsyncEnumerable` in BCL conflicts with `System.Linq.Async` | Source | Remove package or upgrade to 7.0.0; `<ExcludeAssets>compile</ExcludeAssets>` for transitive; `SelectAwait` -> `Select` | core-libraries/10.0/asyncenumerable |
| No default SIGTERM/CTRL_CLOSE/CTRL_SHUTDOWN handlers; `ProcessExit` not raised on SIGTERM | Behavioral | Use Generic Host (`UseConsoleLifetime`) or `PosixSignalRegistration.Create` | core-libraries/10.0/sigterm-signal-handler |
| C# 14 span overload resolution in expression trees | Behavioral | Force `Enumerable.*` overloads in expressions | core-libraries/10.0/csharp-overload-resolution |
| `BufferedStream.WriteByte` no implicit flush | Behavioral | Explicit `Flush()` | core-libraries/10.0/bufferedstream-writebyte-flush |
| Generic-math shift amount always masked | Behavioral | Fix code relying on overshift | core-libraries/10.0/generic-math |
| Default propagator W3C (`baggage`) | Behavioral | `CreatePreW3CPropagator()` | core-libraries/10.0/default-trace-context-propagator |
| `PropagationData` activities not `Recorded` | Behavioral | Set `ActivityTraceFlags` manually in custom samplers | core-libraries/10.0/activity-sampling |
| `DriveInfo.DriveFormat` returns kernel FS names on Linux | Behavioral | Update comparisons | core-libraries/10.0/driveinfo-driveformat-linux |
| Explicit `Size` with `[InlineArray]` -> `TypeLoadException` | Binary | Wrap in another struct | core-libraries/10.0/inlinearray-explicit-size-disallowed |
| Tar atime/ctime not set by default | Behavioral | Set explicitly if needed | core-libraries/10.0/tar-atime-ctime-default |
| Arm64 SVE nonfaulting loads require mask | Binary/source | Pass mask | core-libraries/10.0/sve-nonfaulting-loads-mask-parameter |
| `*OpenSsl` crypto types throw on macOS | Behavioral | `RSA.Create()` etc.; `AesGcm` instead of `AesCcm` | cryptography/10.0/openssl-macos-unsupported |
| OpenSSL 1.1.1+ required on Unix; env var renamed `DOTNET_OPENSSL_VERSION_OVERRIDE` | Behavioral | Upgrade OpenSSL / rename var | cryptography/10.0/openssl-version-requirement |
| Stricter `X500DistinguishedName` | Behavioral | `X500DistinguishedNameBuilder` | cryptography/10.0/x500distinguishedname-validation |
| PQC `SecretKey` -> `PrivateKey` | Source | Rename | cryptography/10.0/mldsa-slhdsa-secretkey-to-privatekey |
| X509 key algorithm parameters can be `null` | Behavioral/source | Handle null | cryptography/10.0/x509-publickey-null |
| `CoseSigner.Key` nullable; CompositeMLDsa draft-08 | Behavioral | Handle null; re-test interop | cryptography/10.0/cosesigner-key-null |
| Single-file apps do not probe app dir for native libs | Behavioral | `DllImportSearchPath.AssemblyDirectory`; AOT rpath | interop/10.0/native-library-search |
| `DllImportSearchPath.AssemblyDirectory` alone = no OS fallback | Behavioral | Omit explicit search path | interop/10.0/search-assembly-directory |
| `Uri` length limit removed | Behavioral | Validate length yourself | networking/10.0/uri-length-limits-removed |
| `MailAddress` rejects consecutive dots | Behavioral | Handle `FormatException` | networking/10.0/mailaddress-consecutive-dots |
| HTTP/3 off with trimming/AOT | Source | `<Http3Support>true</Http3Support>` | networking/10.0/http3-disabled-with-publishtrimmed |
| STJ property-name conflict with metadata names | Behavioral | Rename / `[JsonIgnore]` | serialization/10/property-name-validation |
| `XmlSerializer` serializes `[Obsolete]` properties | Behavioral | `AppContext.SetSwitch("Switch.System.Xml.IgnoreObsoleteMembers", true)` | serialization/10/xmlserializer-obsolete-properties |
| `BackgroundService.ExecuteAsync` fully on background thread | Behavioral | Startup work in `StartAsync`/`IHostedLifecycleService` | extensions/10.0/backgroundservice-executeasync-task |
| Config `null` preserved (not `""`) | Behavioral | Nullable properties / use `""` | extensions/10.0/configuration-null-values-preserved |
| Named mutexes user-scoped on Unix (also serviced into 10.0.13) | Behavioral | `NamedWaitHandleOptions.None` or runtimeconfig `System.Threading.Mutex.UnsafeDefaultMutexScopeGlobal=true` | core-libraries/11/named-mutexes-unix-default-scope |

## Breaking changes when upgrading: To .NET 11

| Change | Type | Mitigation | Page |
| --- | --- | --- | --- |
| CPU baseline x86-64-v2 / Windows Arm64 LSE | Behavioral | Upgrade hardware | jit/11/minimum-hardware-requirements |
| FP -> small int saturating | Behavioral | `ConvertToIntegerNative<T>` or `unchecked((T)(int)x)` | jit/11/fp-to-small-integer |
| `decimal`/`BigInteger` <-> binary FP correctly rounded (constants change on rebuild, even for older TFMs built with .NET 11 SDK; no switch) | Behavioral | Use `m` literals; `G15` format+parse to mimic old | core-libraries/11/decimal-biginteger-floating-point-conversions |
| `Math.Round`/`MathF.Round(x, digits)` correctly rounded; any non-negative digits | Behavioral | `Math.Round(v * p, mode) / p` for old results; use `decimal` for base-10 | core-libraries/11/math-round-digits |
| `Complex` special values per C23 Annex G | Behavioral | Update tests | core-libraries/11/complex-annex-g-special-values |
| `DateOnly`/`TimeOnly.TryParse*` throw `ArgumentException` for invalid styles/formats | Behavioral | Pass valid args | core-libraries/11/dateonly-timeonly-tryparse-argumentexception |
| ZIP CRC32 validation; `ZipArchive.CreateAsync` eager load | Behavioral | Handle `InvalidDataException` | core-libraries/11/ziparchive-entry-crc32-validation, .../ziparchive-createasync-eager-load |
| Deflate/GZip empty payload writes header/footer | Behavioral | Special-case empty input | core-libraries/11/deflatestream-gzipstream-empty-payload |
| TAR checksum validation; hard links as `HardLink` entries | Behavioral | `TarHardLinkMode.CopyContents` | core-libraries/11/tar-checksum-validation, .../tarwriter-hardlink-entries |
| CBOR max depth (reader 64, writer 1000) | Behavioral | `CborReaderOptions/CborWriterOptions.MaxDepth` | core-libraries/11/cbor-max-depth |
| `Environment.GetCommandLineArgs()[0]` = invocation name | Behavioral | `Environment.ProcessPath` | core-libraries/11/environment-getcommandlineargs-apphost-invocation-name |
| `Environment.TickCount` on Windows excludes sleep | Behavioral | `DateTime.UtcNow` if sleep time matters | core-libraries/11/environment-tickcount-windows-behavior |
| `NamedPipeServerStream` + `CurrentUserOnly` chmod 0600 on Unix | Behavioral | Drop `CurrentUserOnly` for cross-user | core-libraries/11/namedpipeserverstream-unix-permissions |
| `Nullable.GetUnderlyingType` throws for custom `Type` subclasses | Behavioral | Override `GetNullableUnderlyingType()` | core-libraries/11/nullable-getunderlyingtype-throws |
| `SafeFileHandle.IsAsync`/`FileStream.IsAsync` on Unix = `O_NONBLOCK` | Behavioral | Review checks | core-libraries/11/safefilehandle-isasync-unix |
| `Assembly.GetCallingAssembly` + `StackTraceSupport=false` throws | Behavioral | Enable switch or remove calls | core-libraries/11/assembly-getcallingassembly-stacktracesupport-disabled |
| Tensor shape alignment / storage validation | Behavioral | Separate destination storage | core-libraries/11/tensor-shape-alignment |
| Obsoletions SYSLIB0063-0066 | Source | Table at the top of this file | core-libraries/11/obsolete-apis, cryptography/11/obsolete-apis |
| Composite ML-DSA on Windows native-only (4 ECDSA sets) | Behavioral | `IsAlgorithmSupported` | cryptography/11/compositemldsa-windows-native |
| DSA removed on macOS | Behavioral | ECDSA | cryptography/11/dsa-removed-macos |
| HKDF on Windows: IKM/PRK > 2048 bytes throws | Behavioral | Smaller inputs | cryptography/11/hkdf-windows-cng |
| Linux AIA fetch limit 2 per chain | Behavioral | `ChainPolicy.ExtraStore` | cryptography/11/aia-fetch-limit-linux |
| `SslStream` server-side AIA downloads disabled | Behavioral | Clients send full chain / `ExtraStore` | networking/11/sslstream-aia-downloads-disabled |
| `Uri`/`UriBuilder` stricter parsing | Behavioral | Fix inputs; set `Path`/`UserName` separately | networking/11/uri-parsing-validation |
| HTTP metrics observable | Behavioral | `RecordObservableInstruments()` | networking/11/http-metrics-observable-counters |
| `.runtimeconfig.dev.json` `configProperties` override `.runtimeconfig.json` | Behavioral | Remove duplicates from dev file | deployment/11/runtimeconfigdev-configproperties-precedence |
| 9 `Microsoft.Extensions.*` packages in shared framework | Behavioral | Remove `PackageReference` (NU1510) | extensions/11/extensions-in-shared-framework |
| `IHost.RunAsync/StopAsync` throw when a `BackgroundService` fails (non-zero exit) | Behavioral | try/catch around `RunAsync` if old behavior wanted | extensions/11/ihost-runasync-stopasync-throw-backgroundservice-failure |
| DI scope disposal aggregates exceptions | Behavioral | Non-throwing `Dispose`; catch `AggregateException` | extensions/11/dependency-injection-disposal-exceptions |
| Chained config `""` overrides earlier providers | Behavioral | Use `null`/remove key | extensions/11/chained-configuration-empty-string |
| NativeAOT `lib` prefix; non-blittable `UnmanagedCallersOnly` rejected | Behavioral | `UseNativeLibPrefix=false`; `DisableRuntimeMarshalling` | interop/11/nativeaot-lib-prefix, interop/11/unmanagedcallersonly-non-blittable |
| iOS/tvOS file locking disabled by default | Behavioral | `System.IO.DisableFileLocking=false` | .NET 11 runtime page |
