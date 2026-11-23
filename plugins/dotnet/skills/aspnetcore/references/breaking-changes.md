# Breaking changes when upgrading ASP.NET Core

## Breaking changes when upgrading to ASP.NET Core 10 (from 9)

Source: <https://learn.microsoft.com/aspnet/core/breaking-changes/10/overview>

| Change | Type | Mitigation |
| --- | --- | --- |
| Cookie login redirects disabled for known API endpoints (401/403 instead of 302) | Behavioral | `.AllowCookieRedirect()`, `[AllowCookieRedirect]`, or the app-wide switch `Microsoft.AspNetCore.Authentication.Cookies.IgnoreRedirectMetadata=true` |
| `WithOpenApi` deprecated (ASPDEPR002) | Source | `AddOpenApiOperationTransformer` |
| Exception diagnostics suppressed when `TryHandleAsync` returns true | Behavioral | `SuppressDiagnosticsCallback = _ => false` |
| `IActionContextAccessor` obsolete (ASPDEPR006) | Source/behavioral | `IHttpContextAccessor` + `GetEndpoint()` |
| `IncludeOpenAPIAnalyzers` and MVC API analyzers deprecated (ASPDEPR007) | Source | Remove the property; use `TypedResults` |
| `IPNetwork` / `KnownNetworks` obsolete (ASPDEPR005) | Source | `System.Net.IPNetwork` + `KnownIPNetworks` |
| `Microsoft.Extensions.ApiDescription.Client` deprecated | Source | NSwag, Kiota, or openapi-generator |
| Razor runtime compilation obsolete (ASPDEPR003) | Source | Hot Reload |
| `WebHostBuilder` / `IWebHost` / `WebHost` obsolete (ASPDEPR004/008) | Source | `WebApplicationBuilder` / `HostBuilder` |
| OpenAPI 3.1 default and Microsoft.OpenApi 2.0 transformer API changes | Source/behavioral | Port transformers to `JsonNode`, `IOpenApiSchema`, and `JsonSchemaType.Null`; pin `OpenApi3_0` if tooling needs it |
| Json+PipeReader deserialization | Behavioral | Fix custom converters for `HasValueSequence`; temporary switch `Microsoft.AspNetCore.UseStreamBasedJsonParsing` |

Related .NET 10 runtime and extensions breaks that affect web apps (<https://learn.microsoft.com/dotnet/core/compatibility/10>):

- `BackgroundService` runs all of `ExecuteAsync` as a Task.
- Null values are preserved in configuration.
- Default trace context propagator is W3C.
- The .NET runtime no longer installs default SIGTERM handlers.
- HTTP/3 is disabled with `PublishTrimmed`.
- STJ checks for property name conflicts.
- Default container images use Ubuntu.
- `dotnet new sln` creates SLNX by default.
- `dotnet restore` audits transitive packages.

## Breaking changes when upgrading to ASP.NET Core 11 (from 10)

Sources: <https://learn.microsoft.com/aspnet/core/breaking-changes/11/overview> and <https://learn.microsoft.com/aspnet/core/migration/100-to-110?view=aspnetcore-11.0>

Mechanics: set the TFM to `net11.0`, set `global.json` to SDK `11.0.100`, and update `Microsoft.AspNetCore.*`, `Microsoft.Extensions.*`, and `Microsoft.EntityFrameworkCore.*` packages to 11.0.0.

| Change | Type | Mitigation |
| --- | --- | --- |
| Automatic CSRF middleware (header-based) auto-injected | Behavioral (not listed as a breaking change, but it can produce 400s on cross-origin form posts) | Allow the origin in CORS with `.AllowCredentials()`, or `.DisableAntiforgery()` / `[IgnoreAntiforgeryToken]` for non-cookie endpoints; `DisableCsrfProtection=true` as a last resort |
| `ConcurrencyLimiter` middleware removed (`UseConcurrencyLimiter`, `AddQueuePolicy`, `AddStackPolicy`) | Binary/source | `AddRateLimiter(o => o.AddConcurrencyLimiter("p", l => { l.PermitLimit = 2; l.QueueLimit = 25; }))` + `UseRateLimiter()` + `.RequireRateLimiting("p")`; or keep the 10.x package temporarily |
| MVC compatibility options removed (`SetCompatibilityVersion`, `CompatibilityVersion`, `MvcCompatibilityOptions`) | Binary/source | Delete the calls (they were no-ops since 3.0) |
| Hosting emits OTel HTTP semantic-convention tags by default; `http.route` resolved for conventional routes; no `StatusDescription`; `error.type` on 5xx | Behavioral | Update the instrumentation package; review metric cardinality; revert tags with `Microsoft.AspNetCore.Hosting.SuppressActivityOpenTelemetryData=true` |
| Kestrel tightens HTTP compliance: HTTP/2 and HTTP/3 reject `Connection`, `Proxy-Connection`, `Keep-Alive`, `TE` (other than trailers), `Transfer-Encoding`, `Upgrade`; HTTP/1.1 closes the connection when both CL and TE are present (anti-smuggling) | Behavioral | Fix proxies or clients to strip connection-specific headers and send only one framing header |
| Microsoft.OpenApi upgraded to 3.x | Source (and binary for libraries built against 2.x) | Port transformers following upgrade-guide-3 |
| `OpenApiVersion` defaults to `OpenApi3_2` | Behavioral | Set `OpenApi3_1` or `OpenApi3_0` for older tooling |
| OpenAPI includes all `ProducesResponseType` entries per status code | Behavioral | Review generated clients and snapshot tests |
| OpenAPI server URL has no trailing slash when `PathBase` is empty | Behavioral | Update fixtures, or add it back with a document transformer |
| OIDC `max_age` now validates `auth_time` (missing or stale fails authentication) | Behavioral | Make sure the IdP returns `auth_time`; move PAR `max_age` customization to `OnRedirectToIdentityProvider`; temporary switch `Microsoft.AspNetCore.Authentication.OpenIdConnect.DisableMaxAgeValidation=true` |
| Passkey sign-in enforces confirmation and lockout (`PasskeySignInAsync` returns `LockedOut` or `NotAllowed`) | Behavioral (security fix) | Handle those results in the UI; fix the user records rather than weakening `PreSignInCheck` |
| Identity external login keys use ordinal equality (EF stores) | Behavioral | Store and send exact `LoginProvider` and `ProviderKey`; never normalize them |
| HTTP.sys exposes the TLS channel binding token by default (`Medium`); about 40 bytes per request | Behavioral | `options.HttpAuthenticationHardeningLevel = HttpAuthenticationHardeningLevel.Legacy` to opt out |
| Response compression always emits `Vary: Accept-Encoding` | Behavioral | Usually none; check CDN cache keys |
| SqlClient 7.x: Entra ID auth moved to `Microsoft.Data.SqlClient.Extensions.Azure` | Behavioral (runtime error) | Add that package if your connection string uses `Authentication=Active Directory *` |
| Obsolete `ImageTagHelper` members and `ModelMetadataIdentity.ForProperty(Type, string, Type)` removed | Binary/source | Use the `PropertyInfo` overload |
| `TlsClientHelloBytesCallback` obsolete | Source (warning) | `ListenOptions.UseTlsClientHelloListener` |
| `Microsoft.AspNetCore.Grpc.Swagger` deprecated | Package | Use built-in OpenAPI or other tooling |
| Blazor (out of scope): QuickGrid renders links, SSR defers antiforgery to middleware, enhanced nav no longer preloads, custom event name collision throws, obsolete Blazor APIs removed, WASM env vars loaded into `IConfiguration` | Various | Blazor is not covered by this plugin: read the ASP.NET Core 11 breaking changes page |

Related .NET 11 runtime and extensions breaks that affect web apps (<https://learn.microsoft.com/dotnet/core/compatibility/11>):

- Nine `Microsoft.Extensions.*` abstraction packages moved into the shared framework: Caching, Configuration, DI, Diagnostics, FileProviders, and Hosting abstractions, plus `Logging.Abstractions`, `Options`, and `Primitives`. Explicit `PackageReference`s produce NU1510; remove them when targeting only `net11.0`.
- `IHost.RunAsync` and `StopAsync` now throw (non-zero exit code) when a `BackgroundService` fails with `StopHost`.
- DI scope disposal aggregates exceptions.
- Empty strings in chained configuration override earlier providers.
- `IStartupValidator` obsolete (SYSLIB0066); use `IAsyncStartupValidator`.
- `SslStream` server-side AIA downloads are disabled by default.
- `HttpClient` high-cardinality metrics use observable counters.
- `DateOnly` and `TimeOnly` `TryParse` throw `ArgumentException` for invalid input.
- Minimum hardware requirements were raised.
