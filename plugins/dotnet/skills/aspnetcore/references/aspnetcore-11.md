# ASP.NET Core 11 (November 2026, STS)

GA on 2026-11-10; items are GA unless marked **experimental**. The validation,
`[ShortCircuit]`, union, `QUERY`, SignalR, Zstandard and rate limiting examples
were compiled against SDK 11.0.100; automatic CSRF was checked at runtime
(cross-site form post: 400; same-origin or no browser headers: 200). The Learn page may
still mention previews: that wording is stale. Main sources:
[What's new in ASP.NET Core 11](https://learn.microsoft.com/aspnet/core/release-notes/aspnetcore-11?view=aspnetcore-11.0),
[migrating from 10 to 11](https://learn.microsoft.com/aspnet/core/migration/100-to-110?view=aspnetcore-11.0).

## Automatic CSRF protection (header-based)

- **Status:** GA (11). Auto-injected by `WebApplication.CreateBuilder` when the app has endpoints.
- **What:** Middleware checks `Sec-Fetch-Site`, falling back to `Origin` versus `Host`, and records a verdict on `IAntiforgeryValidationFeature`. **Form consumers enforce it.** It applies to endpoints whose `IAntiforgeryMetadata.RequiresValidation` is true: Minimal APIs that bind forms, MVC actions with `[ValidateAntiForgeryToken]` or `[AutoValidateAntiforgeryToken]`, and Blazor SSR. **Endpoints that bind JSON see no behavioral change.** Rules:
  - Safe methods (GET, HEAD, OPTIONS, TRACE) are allowed.
  - `same-origin` and `none` are allowed.
  - An origin allowed by the resolved CORS policy is allowed only when that policy also has `.AllowCredentials()`. `AllowAnyOrigin` is never trusted.
  - Non-browser clients that send neither header are allowed.
  - Everything else gets 400.
  - The token-based antiforgery system can coexist with it; Microsoft now recommends the automatic protection as the default defense.

```csharp
// Old (10): token-based
builder.Services.AddAntiforgery();
app.UseAntiforgery();
app.MapPost("/widgets", ([FromForm] Widget w) => ...);

// New (11): nothing to add; cross-origin browser form posts get 400 automatically.
// Trust a cross-origin caller through CORS (must AllowCredentials):
builder.Services.AddCors(o => o.AddDefaultPolicy(p => p.WithOrigins("https://app.contoso.com").AllowAnyHeader().AllowAnyMethod().AllowCredentials()));
app.UseCors();
// Opt out (only non-cookie or non-browser endpoints):
app.MapPost("/api/webhook", (WebhookPayload p) => Results.Accepted()).DisableAntiforgery();   // MVC: [IgnoreAntiforgeryToken]
```

- Global kill switch (escape hatch only): config key `DisableCsrfProtection=true` (env var `ASPNETCORE_DisableCsrfProtection`). The logic can be replaced by registering `ICsrfProtection` (`ValidateAsync(HttpContext)`) as a singleton.
- **Keep token antiforgery when:** you must support browsers without `Sec-Fetch-Site`, you use `IAntiforgeryAdditionalDataProvider`, or compliance requires defense in depth.
- **Warning:** If you rely on antiforgery without calling `UseAntiforgery()`, then disabling the CSRF middleware, or running on a non-`WebApplication` host, leaves those endpoints throwing. In that case, call `app.UseAntiforgery()`.
- Sources: <https://learn.microsoft.com/aspnet/core/security/anti-request-forgery?view=aspnetcore-11.0#automatic-csrf-protection-in-aspnet-core> and the migration guide 10 to 11, "Security".

## Async validation (`AsyncValidationAttribute`, `IAsyncValidatableObject`)

- **Status:** GA (11). The new BCL DataAnnotations APIs run through `Microsoft.Extensions.Validation`, for Minimal APIs and Blazor.
- **What:** Validators can await I/O (DB uniqueness, remote calls). Attributes on the same member start concurrently, and collection items validate in parallel. The existing ordering between member, type, and `IValidatableObject` validation is preserved.

```csharp
public sealed class UniqueEmailAttribute : AsyncValidationAttribute
{
    protected override ValidationResult? IsValid(object? v, ValidationContext c) =>
        throw new InvalidOperationException("Async only.");               // sync IsValid is abstract too
    protected override async Task<ValidationResult?> IsValidAsync(object? v, ValidationContext c, CancellationToken ct)
    {
        var users = c.GetRequiredService<IUserService>();
        return v is string e && await users.EmailExistsAsync(e, ct) ? new("That email is already registered.") : ValidationResult.Success;
    }
}
public class ReservationRequest : IAsyncValidatableObject
{
    [Required, UniqueEmail] public string Email { get; set; } = "";
    public DateOnly Date { get; set; }
    public IEnumerable<ValidationResult> Validate(ValidationContext c) => throw new InvalidOperationException("Async only.");
    public async IAsyncEnumerable<ValidationResult> ValidateAsync(ValidationContext c, [EnumeratorCancellation] CancellationToken ct = default)
    {
        if (!await c.GetRequiredService<IRoomService>().HasAvailabilityAsync(Date, ct))
            yield return new("No rooms are available on that date.", [nameof(Date)]);
    }
}
builder.Services.AddValidation();
app.MapPost("/reservations", (ReservationRequest r) => Results.Ok(r));
```

- **Gotcha:** Throw from the synchronous member when a type is async-only, so synchronous callers don't silently skip validation.
- Source: what's new 11, "Async validation for Minimal APIs".

## Built-in validation localization

- **Status:** GA (11). Calling `AddLocalization()` before `AddValidation()` turns localization on automatically.
- **Key resolution order:**
  1. An explicit `ErrorMessage` value, used as the resource key.
  2. `{DeclaringType}_{MemberName}_{AttributeType}_Error`
  3. `{DeclaringType}_{AttributeType}_Error`
  4. `{AttributeType}_Error`
  5. The attribute's built-in message.
- `ValidationOptions.LocalizerProvider` points lookups at a shared resource. A custom `IStringLocalizerFactory` (for example, DB-backed) takes precedence over resource files. Implement `IValidationMessageFormatter` for attributes that substitute custom arguments.

```csharp
builder.Services.AddLocalization();
builder.Services.AddValidation(o => o.LocalizerProvider = (_, f) => f.Create(typeof(ValidationMessages)));
```

- Source: what's new 11, "Validation localization is built in".

## `[ValidatableType]` and `[SkipValidation]` no longer experimental

- **Status:** GA (11). Remove `ASP0029` suppressions and any polyfill types from `Microsoft.Extensions.Validation.Embedded`.
- Source: migration guide 10 to 11.

## C# 15 union types in JSON bodies

- **Status:** GA (11). Works in Minimal APIs, MVC, the SignalR JSON protocol, and Blazor interop and state.

```csharp
public union UnionIntString(int, string);
app.MapGet("/value", () => new UnionIntString(42));
```

- **Not supported:** route, query, header, and form binding; the SignalR MessagePack and Newtonsoft protocols.
- **OpenAPI:** emitted as `anyOf` over case schemas, with no `$type` discriminator. Use a `[JsonUnion]` classifier when cases share a JSON shape. ApiExplorer detects unions through `JsonTypeInfoKind.Union`, so Swashbuckle and NSwag see them too.
- Source: what's new 11, "C# union types".

## `[ShortCircuit]` attribute

- **Status:** GA (11). This is the attribute form of the existing `.ShortCircuit()` from .NET 8. It runs the endpoint right after routing and skips auth, CORS, and other middleware. An optional status code is supported: `[ShortCircuit(404)]`.

```csharp
app.MapGet("/health", [ShortCircuit] () => "Healthy");
[ApiController, Route("robots.txt"), ShortCircuit]
public class RobotsController : ControllerBase { [HttpGet] public IActionResult Get() => Content("User-agent: *\nDisallow:", "text/plain"); }
```

- **Security:** Never use it on endpoints that need authentication or authorization, because that middleware is skipped.
- Source: what's new 11.

## Endpoint filters observe parameter-binding failures

- **Status:** GA (11). Behavioral change. When an endpoint has filters, the filter pipeline runs even after a binding failure, so a filter can check `StatusCode == 400` and write its own body. In Development, set `RouteHandlerOptions.ThrowOnBadRequest = false` for filters to observe the failure.
- Source: what's new 11.

## OpenAPI 3.2 by default (Microsoft.OpenApi 3.x)

- **Status:** GA (11). Breaking change: both the default version and the library major version changed.
- **Related changes:**
  - HTTP `QUERY` operations: native `query` in 3.2 documents, `x-oai-additionalOperations` in 3.0 and 3.1.
  - SSE described with `itemSchema`.
  - `[Obsolete]` maps to `deprecated: true` on operations, schemas, and properties.
  - Binary responses (`FileContentResult`, `FileStreamResult`, `FileContentHttpResult`, `FileStreamHttpResult`) appear as `type: string, format: binary`. Requires `.Produces<T>(contentType: ...)` or `[ProducesResponseType<T>]`.
  - Multiple `Produces` or `[ProducesResponseType]` declarations for one status code are all kept (separate content entries, or `anyOf`).
  - Non-body enum parameters keep their C# names; body enums use the JSON naming policy.
  - Array component IDs become `stringArray`, `TodoArray`.
  - Build-time generation can set the environment: `<OpenApiGenerationEnvironment>Development</OpenApiGenerationEnvironment>`.
  - The server URL has no trailing slash when `PathBase` is empty.

```csharp
builder.Services.AddOpenApi(o => o.OpenApiVersion = Microsoft.OpenApi.OpenApiSpecVersion.OpenApi3_1); // pin if tooling lacks 3.2
app.MapMethods("/search", ["QUERY"], (SearchRequest r) => SearchService.Run(r));
```

- **Transformer migration:** Replace `new OpenApiString("x")` with `JsonValue.Create("x")`, handle `IOpenApiSchema` interfaces, note that `ParseNode` was removed, and review the reshaped `OpenApiReference`. Guide: <https://github.com/microsoft/OpenAPI.NET/blob/main/docs/upgrade-guide-3.md>
- **Deprecated:** the `Microsoft.AspNetCore.Grpc.Swagger` package.
- Sources: what's new 11, OpenAPI section. <https://learn.microsoft.com/aspnet/core/breaking-changes/11/microsoft-openapi-3x>

## SignalR authentication refresh and client cancellation

- **Status:** GA (11).
- **Auth refresh:** A `/refresh` endpoint sits next to `/negotiate`, and the negotiate response reports the token lifetime. Clients re-authenticate without dropping the connection. It is enabled per hub. The .NET client refreshes automatically by default and can be configured with `WithAuthenticationRefresh`. The TypeScript client uses `withAuthenticationRefresh`.

```csharp
app.MapHub<ChatHub>("/chat", o =>
{
    o.EnableAuthenticationRefresh = true;
    o.CloseOnAuthenticationExpiration = true;
    o.OnAuthenticationRefresh = ctx => Task.FromResult(
        ctx.PreviousUser.FindFirstValue(ClaimTypes.NameIdentifier) == ctx.NewUser.FindFirstValue(ClaimTypes.NameIdentifier));
});
public class ChatHub : Hub { public override Task OnAuthenticationRefreshedAsync() => Task.CompletedTask; }
```

- **Security:** Always check in `OnAuthenticationRefresh` that the subject is unchanged, so a refresh cannot switch identities mid-connection.
- **Client cancellation of non-streaming invocations:** `connection.InvokeAsync("Work", cts.Token)` with `cts.Cancel()` triggers the hub method's `CancellationToken` parameter.
- Source: what's new 11, SignalR.

## Native OpenTelemetry HTTP server tracing

- **Status:** GA (11). Behavioral breaking change: `SuppressActivityOpenTelemetryData` now defaults to `false`.
- **What:** The hosting activity carries semantic-convention tags: `http.request.method`, `http.response.status_code`, `http.route` (conventional routes report resolved values, for example `Store/Checkout/{id?}`), `url.path`, `url.scheme`, `server.address`, `server.port`, `network.protocol.version`, and `user_agent.original`. `http.server.request.duration` gains `error.type` for 5xx responses. `Activity.StatusDescription` is no longer set on exceptions. `OpenTelemetry.Instrumentation.AspNetCore` is no longer required.

```csharp
// Old
builder.Services.AddOpenTelemetry().WithTracing(t => t.AddAspNetCoreInstrumentation());
// New (11)
builder.Services.AddOpenTelemetry().WithTracing(t => t.AddSource("Microsoft.AspNetCore").AddOtlpExporter());
// Revert tags: AppContext.SetSwitch("Microsoft.AspNetCore.Hosting.SuppressActivityOpenTelemetryData", true);
```

- **Duplicate tags:** If you keep the instrumentation package, update it; the latest version skips tags the framework already emits.
- Source: <https://learn.microsoft.com/aspnet/core/breaking-changes/11/http-activity-otel-semconv>

## Kestrel, server, and performance (GA, 11)

- **Non-throwing HTTP/1.1 parser:** Up to 20-40% more throughput under malformed traffic. No impact on valid requests.
- **HTTP logging:** The middleware pools `ResponseBufferingStream` instances. `WithHttpLogging()` and `[HttpLogging]` are not new; they date from the .NET 8 HTTP logging work.
- **HTTP/3** starts processing requests before receiving SETTINGS, which lowers first-request latency.
- **Trailer timeouts:** `RequestHeadersTimeout` now also applies to fragmented HTTP/2 and HTTP/3 trailers.
- **TLS:**
  - `ITlsHandshakeFeature.Exception` reports why a handshake failed.
  - `HttpsConnectionAdapterOptions.TlsClientHelloBytesCallback` is **obsolete**. Use `listenOptions.UseTlsClientHelloListener(...)`, called before `UseHttps()`.
  - `ITlsConnectionFeature.TryGetChannelBindingBytes(ChannelBindingKind.Endpoint, out cbt)` exposes the channel binding token.
  - Negotiate on Kestrel uses TLS channel binding automatically.
  - HTTP.sys has `HttpAuthenticationHardeningLevel` (`Legacy`, `Medium` default, `Strict`).
- **Zstandard** response compression and request decompression, enabled by default:

```csharp
builder.Services.AddResponseCompression();
builder.Services.AddRequestDecompression();
builder.Services.Configure<ZstandardCompressionProviderOptions>(o => o.CompressionOptions = new ZstandardCompressionOptions { Quality = 6 });
```

- **`Vary: Accept-Encoding`** is always emitted when compression is enabled (breaking; cache-correctness fix).
- **Runtime-async:** Shared-framework libraries are compiled with runtime-async on `net11.0`. Internal change; fewer per-await allocations. Watch for differences in exception stacks and `AsyncLocal` flow.
- **Rate limiting:** `FixedWindowRateLimiter` reports an accurate `RetryAfter`. Fixes for `TokenBucketRateLimiter` partial refills and for `CreateChained`.

```csharp
builder.Services.AddRateLimiter(o =>
{
    o.AddFixedWindowLimiter("api", l => { l.PermitLimit = 100; l.Window = TimeSpan.FromMinutes(1); });
    o.OnRejected = (ctx, ct) =>
    {
        if (ctx.Lease.TryGetMetadata(MetadataName.RetryAfter, out var ra))
            ctx.HttpContext.Response.Headers.RetryAfter = ((int)ra.TotalSeconds).ToString();
        ctx.HttpContext.Response.StatusCode = StatusCodes.Status429TooManyRequests;
        return ValueTask.CompletedTask;
    };
});
app.UseRateLimiter();
app.MapGet("/data", () => "ok").RequireRateLimiting("api");
```

- **Output caching:** `IOutputCachePolicyProvider` (`GetBasePolicies`, `GetPolicyAsync(name)`) supports dynamic or tenant-specific policies.
- **Tooling:**
  - `dotnet dev-certs https --trust` trusts the certificate in WSL and Windows.
  - `dotnet user-jwts create --file app.cs` works with file-based apps.
  - The `mcpserver` template is bundled with the SDK: `dotnet new mcpserver`.
- Source: what's new 11, Miscellaneous.

## Identity and auth (11)

- **`TimeProvider` in Identity:** GA. Identity uses `TimeProvider` for lockout, token expiry, and security stamps. Register `FakeTimeProvider` in tests.
- **Consistent authorization metadata:** `IAuthorizeData`, `AuthorizationPolicy`, and `IAuthorizationRequirementData` are honored the same way by MVC filters, SignalR hub methods, and Blazor. New `AuthorizationPolicy.CombineAsync(IAuthorizationPolicyProvider, IEnumerable<object>)`.
- **Device Bound Session Credentials:** **Experimental.** The `Microsoft.AspNetCore.Authentication.DeviceBoundSessions` package stays prerelease throughout .NET 11, and browser support is experimental (Chrome).

```csharp
builder.Services.AddAuthentication("Application").AddCookie("Application")
    .AddDeviceBoundSession("Application", o => o.ShortLivedCookieExpiration = TimeSpan.FromMinutes(10));
```

- Source: what's new 11, "Authentication and authorization".

## Blazor (one line, out of scope)

- Shared with the topics above: auto CSRF (Blazor SSR protected by default, `UseAntiforgery()` removed from the template), SignalR auth refresh flowing into circuits, and async validation. The experimental `Microsoft.AspNetCore.Components.AI` package stays prerelease.
