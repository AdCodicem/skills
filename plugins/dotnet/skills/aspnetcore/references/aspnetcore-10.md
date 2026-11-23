# ASP.NET Core 10 (November 2025, LTS)

All items are GA unless marked otherwise. Main sources:
[What's new in ASP.NET Core 10](https://learn.microsoft.com/aspnet/core/release-notes/aspnetcore-10.0),
[breaking changes](https://learn.microsoft.com/aspnet/core/breaking-changes/10/overview).

## Built-in Minimal API validation (`AddValidation`)

- **Status:** GA in 10. The underlying validation *resolver* APIs are marked experimental. The top-level `AddValidation`, `DisableValidation`, and the validation filter are stable. In 10, `[ValidatableType]` and `[SkipValidation]` were experimental (ASP0029). They are no longer experimental in 11.
- **What:** A source generator plus an endpoint filter validate DataAnnotations on query, header, and body parameters, on records and classes, on nested objects and collections, and through `IValidatableObject`. On failure, the endpoint returns 400 with validation problem details. The APIs live in the `Microsoft.Extensions.Validation` package and namespace, so they also work outside HTTP.
- **Old vs new:**

```csharp
// Old (pre-10): manual or third-party (FluentValidation, MiniValidation) inside each handler
app.MapPost("/products", (Product p) =>
{
    var ctx = new ValidationContext(p); var results = new List<ValidationResult>();
    if (!Validator.TryValidateObject(p, ctx, results, true))
        return Results.ValidationProblem(results.ToDictionary(r => r.MemberNames.First(), r => new[] { r.ErrorMessage! }));
    return Results.Ok(p);
});

// New (10+)
builder.Services.AddValidation();
app.MapPost("/products", (Product p) => TypedResults.Ok(p));          // auto 400 on invalid
app.MapPost("/raw", ([Required] string name) => TypedResults.Ok(name)).DisableValidation();
public record Product([Required] string Name, [Range(1, 1000)] int Quantity);
```

- **Use when:** you build Minimal APIs and DataAnnotations are enough. **Avoid when:** you have complex rule engines (keep FluentValidation). Note that the generator only discovers types in the assembly that calls `AddValidation`. Endpoints defined in other assemblies need their own `AddValidation` call.
- **Gotchas:** Unmapped JSON properties are not rejected. To reject them, set `JsonSerializerOptions.UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow`. The error response format can be customized through `IProblemDetailsService` (new in 10).
- **Perf/security:** The generator path is AOT-friendly, with no reflection scanning.
- Source: what's new 10, "Validation support in Minimal APIs" and the sections after it. Also <https://learn.microsoft.com/aspnet/core/fundamentals/validation>

## Server-Sent Events: `TypedResults.ServerSentEvents`

- **Status:** GA (10). Works in Minimal APIs and controllers.
- **What:** Streams an `IAsyncEnumerable<T>` or `IAsyncEnumerable<SseItem<T>>` (`System.Net.ServerSentEvents`) as `text/event-stream`. The optional `eventType` argument sets the event type.
- **Old vs new:**

```csharp
// Old: hand-written SSE
app.MapGet("/hr", async (HttpContext ctx, CancellationToken ct) =>
{
    ctx.Response.ContentType = "text/event-stream";
    while (!ct.IsCancellationRequested)
    {
        await ctx.Response.WriteAsync($"event: heartRate\ndata: {Random.Shared.Next(60,100)}\n\n", ct);
        await ctx.Response.Body.FlushAsync(ct);
        await Task.Delay(2000, ct);
    }
});

// New (10+)
app.MapGet("/hr", (CancellationToken ct) => TypedResults.ServerSentEvents(GetHeartRate(ct), eventType: "heartRate"));
static async IAsyncEnumerable<int> GetHeartRate([EnumeratorCancellation] CancellationToken ct)
{
    while (!ct.IsCancellationRequested) { yield return Random.Shared.Next(60, 100); await Task.Delay(2000, ct); }
}
```

- **Use when:** you need one-way server push over plain HTTP, such as notifications, progress, or LLM token streams. **Avoid when:** you need bidirectional messaging or a fan-out backplane (use SignalR).
- **In 11:** OpenAPI 3.2 documents describe SSE responses with `itemSchema`. You must return through `TypedResults.ServerSentEvents`; a handler that returns `IAsyncEnumerable<SseItem<T>>` directly is serialized as JSON, not SSE. Use the `SseItem<T>` overload without `eventType`, or use a plain `IAsyncEnumerable<T>` with `eventType`.
- Source: what's new 10, "Support for Server-Sent Events (SSE)". What's new 11, "Server-Sent Events support in OpenAPI 3.2".

## OpenAPI 3.1 by default (Microsoft.OpenApi 2.0)

- **Status:** GA (10). Superseded by the 3.2 default in 11.
- **What:** Generated documents are OpenAPI 3.1 (JSON Schema 2020-12). Nullable types appear as `type: [X, "null"]`, and nullable complex types use `oneOf`. With the default `NumberHandling = AllowReadingFromString`, `int` and `long` are emitted without `type: integer` and with a digit `pattern`. Set `NumberHandling = Strict` to get `type: integer`. Descriptions can now be siblings of `$ref`. Unknown HTTP methods are excluded from the document. Generation uses the invariant culture.
- **Old vs new:**

```csharp
builder.Services.AddOpenApi();                                  // 10: 3.1 by default
builder.Services.AddOpenApi(o => o.OpenApiVersion = Microsoft.OpenApi.OpenApiSpecVersion.OpenApi3_0); // pin 3.0 for old tooling
```

  For build time, set `<OpenApiGenerateDocumentsOptions>--openapi-version OpenApi3_1</OpenApiGenerateDocumentsOptions>`.

- **Breaking:** Microsoft.OpenApi 2.0 changes transformers. Entities are now interfaces (`IOpenApiSchema`, plus `OpenApiSchemaReference`). `OpenApiSchema.Nullable` is removed; check `JsonSchemaType.Null` instead. `OpenApiAny` and `OpenApiString` are replaced by `JsonNode`. These changes apply even if you pin 3.0.
- Source: what's new 10, "OpenAPI 3.1 support" and "OpenAPI 3.1 breaking changes".

## OpenAPI served as YAML

- **Status:** GA (10). Only the runtime endpoint serves YAML; build-time YAML generation was not confirmed.

```csharp
if (app.Environment.IsDevelopment()) app.MapOpenApi("/openapi/{documentName}.yaml");
```

- Source: what's new 10, "OpenAPI in YAML".

## XML doc comments in OpenAPI

- **Status:** GA (10).
- **What:** A source generator in `Microsoft.AspNetCore.OpenApi` reads XML comments (`<summary>`, `<remarks>`, `<param>`, `<returns>`, and others) from the app and its project references, then injects them through a document transformer. It requires `<GenerateDocumentationFile>true</GenerateDocumentationFile>`. **Lambdas don't carry XML docs**, so use method groups.

```csharp
app.MapGet("/hello", Hello);
static partial class Program
{
    /// <summary>Sends a greeting.</summary>
    /// <param name="name">The name of the person to greet.</param>
    public static string Hello(string name) => $"Hello, {name}!";
}
```

- XML comments on `[AsParameters]` type properties are also picked up. To pull XML from other assemblies, such as `ProblemDetails`, add an `AdditionalFiles` MSBuild target.
- Source: what's new 10, "Populate XML doc comments into OpenAPI document" and "Improvements to the XML comment generator".

## Other OpenAPI items in 10 (GA)

- `Description` on `[ProducesResponseType]`, `[Produces]`, and `[ProducesDefaultResponseType]`. Works for controllers and Minimal APIs.
- `IOpenApiDocumentProvider` is available in DI, so you can read the document outside HTTP, for example in background services.
- In transformer contexts, `context.GetOrCreateSchemaAsync(type)` and `context.Document.AddComponent(...)` generate and register reusable schemas.
- Endpoint-specific operation transformers: `.AddOpenApiOperationTransformer((op, ctx, ct) => ...)`.
- JSON Patch bodies are described as `application/json-patch+json` with a detailed schema.
- The `webapiaot` template includes OpenAPI by default (`--no-openapi` turns it off).
- **Obsoleted:** `WithOpenApi()` reports **ASPDEPR002**. Migrate to `AddOpenApiOperationTransformer`. For Swashbuckle, use `IOperationFilter`; for NSwag, use `IOperationProcessor`.

```csharp
// Old
app.MapGet("/weather", () => ...).WithOpenApi(op => { op.Summary = "Gets weather"; return op; });
// New
app.MapGet("/weather", () => ...).AddOpenApiOperationTransformer((op, ctx, ct) => { op.Summary = "Gets weather"; return Task.CompletedTask; });
```

  Simple metadata can also use `.WithSummary()`, `.WithDescription()`, and `.WithName()`.

- Sources: what's new 10, OpenAPI section. <https://learn.microsoft.com/aspnet/core/breaking-changes/10/withopenapi-deprecated>

## Passkeys (WebAuthn/FIDO2) in ASP.NET Core Identity

- **Status:** GA (10). Only the Blazor Web App template ships passkey UI; for MVC, Razor Pages, or APIs you wire the endpoints yourself.
- **What:** Passkey registration (attestation) and sign-in (assertion) built into `SignInManager<TUser>`: `MakePasskeyCreationOptionsAsync`, `PerformPasskeyAttestationAsync`, `MakePasskeyRequestOptionsAsync`, `PasskeySignInAsync`, `PerformPasskeyAssertionAsync`, and `UserManager.AddOrUpdatePasskeyAsync`. Passkeys require Identity schema **Version3** and an EF migration. Configure them with `IdentityPasskeyOptions`: `ServerDomain` (the RP ID), `AuthenticatorTimeout` (default 5 minutes), `ChallengeSize` (default 32 bytes), and callbacks for attestation and origin validation. `IPasskeyHandler<TUser>` can be replaced.

```csharp
builder.Services.AddIdentityCore<ApplicationUser>(o =>
{
    o.SignIn.RequireConfirmedAccount = true;
    o.Stores.SchemaVersion = IdentitySchemaVersions.Version3;   // passkey tables
})
.AddEntityFrameworkStores<ApplicationDbContext>().AddSignInManager().AddDefaultTokenProviders();

builder.Services.Configure<IdentityPasskeyOptions>(o => o.ServerDomain = "contoso.com");

app.MapPost("/Account/PasskeyRequestOptions", async (SignInManager<ApplicationUser> sm, UserManager<ApplicationUser> um, string? username) =>
{
    var user = string.IsNullOrEmpty(username) ? null : await um.FindByNameAsync(username);
    return TypedResults.Content(await sm.MakePasskeyRequestOptionsAsync(user), "application/json");
});
// Sign-in: var result = await signInManager.PasskeySignInAsync(credentialJson);
```

- **Limitations:** Passkeys are a primary factor only, with no built-in 2FA use. Attestation statements are not validated by default. The feature is scoped to Identity and is not a general WebAuthn library.
- **Security:** Set `ServerDomain` explicitly, or validate host headers. Otherwise the RP ID comes from the `Host` header, which allows credential scoping attacks. When using forwarded headers, set `AllowedHosts`. Never serve untrusted content on subdomains within the RP ID. HTTPS is required. If you call `IPasskeyHandler` directly, you must protect the attestation state yourself, for example in a data-protected cookie.
- **11 changes:** `PasskeySignInAsync` now runs `PreSignInCheck`, which enforces lockout and confirmed email, phone, and account (breaking change, see [breaking-changes.md](breaking-changes.md)). Display names are inferred from the authenticator AAGUID, extensible via the `PasskeyAuthenticators` dictionary in template code.
- Sources: <https://learn.microsoft.com/aspnet/core/security/authentication/passkeys/> and <https://learn.microsoft.com/aspnet/core/security/authentication/passkeys/blazor>

## Cookie auth returns 401/403 for API endpoints instead of redirecting (breaking)

- **Status:** GA (10). Behavioral breaking change.
- **What:** Cookie challenge and forbid return 401 and 403 instead of a 302 to the login or access-denied page for "known API endpoints": `[ApiController]`, Minimal APIs that read or write JSON, `TypedResults` returns, and SignalR. The `Location` header is still set. Detection uses `IDisableCookieRedirectMetadata`. The 10 what's new page calls this `IApiEndpointMetadata`; the breaking-change page uses `IDisableCookieRedirectMetadata` and `IAllowCookieRedirectMetadata`.

```csharp
app.MapGet("/reports/summary", () => new { Total = 1000 }).RequireAuthorization().AllowCookieRedirect(); // opt back in
app.MapGet("/page-ish", ...).DisableCookieRedirect();   // force 401/403 on a non-detected endpoint
// [AllowCookieRedirect] attribute exists for MVC.
```

  App-wide revert in the csproj:

```xml
<ItemGroup><RuntimeHostConfigurationOption Include="Microsoft.AspNetCore.Authentication.Cookies.IgnoreRedirectMetadata" Value="true" /></ItemGroup>
```

- Source: <https://learn.microsoft.com/aspnet/core/breaking-changes/10/cookie-authentication-api-endpoints>

## Auth, authz, and Identity metrics

- **Status:** GA (10).
- Authentication metrics: authenticated request duration, challenge, forbid, sign-in, and sign-out counts. Authorization metric: count of requests requiring authorization. The meters are `Microsoft.AspNetCore.Authentication` and `Microsoft.AspNetCore.Authorization`.
- Identity meter `Microsoft.AspNetCore.Identity`: `aspnetcore.identity.user.{create,update,delete}.duration`, `aspnetcore.identity.user.check_password_attempts`, `aspnetcore.identity.user.generated_tokens`, `aspnetcore.identity.user.verify_token_attempts`, `aspnetcore.identity.sign_in.authenticate.duration`, `aspnetcore.identity.sign_in.check_password_attempts`, `aspnetcore.identity.sign_in.sign_ins`, `aspnetcore.identity.sign_in.sign_outs`, and `aspnetcore.identity.sign_in.two_factor_clients_{remembered,forgotten}`.

```csharp
builder.Services.AddOpenTelemetry().WithMetrics(m => m
    .AddMeter("Microsoft.AspNetCore.Hosting", "Microsoft.AspNetCore.Server.Kestrel",
              "Microsoft.AspNetCore.Authentication", "Microsoft.AspNetCore.Authorization",
              "Microsoft.AspNetCore.Identity", "Microsoft.AspNetCore.MemoryPool"));
```

- Source: what's new 10. Also <https://learn.microsoft.com/aspnet/core/log-mon/metrics/built-in>

## Exception handler: `SuppressDiagnosticsCallback` and handled exceptions no longer logged (breaking)

- **Status:** GA (10). Behavioral breaking change.
- **What:** When `IExceptionHandler.TryHandleAsync` returns `true`, the middleware no longer logs `UnhandledException`, no longer emits the `HandledException` EventSource event, and no longer adds `error.type` to `http.server.request.duration`. The new `ExceptionHandlerOptions.SuppressDiagnosticsCallback` controls this behavior.

```csharp
builder.Services.AddExceptionHandler<MyHandler>();
builder.Services.AddProblemDetails();
app.UseExceptionHandler(new ExceptionHandlerOptions
{
    SuppressDiagnosticsCallback = ctx => false   // restore pre-10 logging of handled exceptions
});
```

  The Learn sample has a stray `;` inside the initializer and does not compile as written. The code above is corrected.

- **When:** Keep the new default if your handler does its own logging. Restore the old behavior if dashboards relied on `error.type` for handled exceptions.
- Source: <https://learn.microsoft.com/aspnet/core/breaking-changes/10/exception-handler-diagnostics-suppressed>

## JSON Patch with System.Text.Json

- **Status:** GA (10). Package `Microsoft.AspNetCore.JsonPatch.SystemTextJson`; stable 10.0.x and 11.0.0 exist on NuGet. Namespace `Microsoft.AspNetCore.JsonPatch.SystemTextJson`.
- **What:** An RFC 6902 implementation on STJ that replaces the Newtonsoft-based `Microsoft.AspNetCore.JsonPatch` combined with `AddNewtonsoftJson`. Microsoft benchmark: apply takes 1.584 µs and 3 KB with the new package, against 271.9 µs and 25 KB with Newtonsoft. It is **not a drop-in replacement**: dynamic types such as `ExpandoObject` are not supported. `ApplyTo` uses the runtime type of the target.

```csharp
// Old: builder.Services.AddControllers().AddNewtonsoftJson(); + Microsoft.AspNetCore.JsonPatch (Newtonsoft)
// New:
using Microsoft.AspNetCore.JsonPatch.SystemTextJson;
app.MapPatch("/customers/{id}", async Task<Results<Ok<Customer>, ValidationProblem, NotFound>> (string id, JsonPatchDocument<Customer> patch, AppDb db) =>
{
    if (await db.Customers.FindAsync(id) is not { } c) return TypedResults.NotFound();
    Dictionary<string, string[]>? errors = null;
    patch.ApplyTo(c, e => (errors ??= new())[e.AffectedObject.GetType().Name] = [e.ErrorMessage]);
    if (errors is not null) return TypedResults.ValidationProblem(errors);   // object already mutated: don't save
    await db.SaveChangesAsync();
    return TypedResults.Ok(c);
}).Accepts<JsonPatchDocument<Customer>>("application/json-patch+json");
```

- **Security (Microsoft's guidance; the library does not mitigate these):**
  - DoS through `copy` amplification: limit the number and size of operations before calling `ApplyTo`.
  - Business-logic subversion: patch a dedicated DTO, never the entity with IDs or flags, and revalidate after applying.
  - Always require authentication and authorization.
  - `ApplyTo` mutates the target in place, even when it reports an error.
- Sources: what's new 10. Also <https://learn.microsoft.com/aspnet/core/web-api/jsonpatch>

## Kestrel, HTTP.sys, hosting, and performance (GA, 10)

- **Automatic memory pool eviction:** Kestrel, IIS, and HTTP.sys pools release idle memory automatically. New meter `Microsoft.AspNetCore.MemoryPool`. `IMemoryPoolFactory<byte>` is available in DI. Custom factories don't get eviction.
- **Json+PipeReader:** MVC, Minimal APIs, and `ReadFromJsonAsync` deserialize from a `PipeReader`. This can break custom `JsonConverter`s that ignore `Utf8JsonReader.HasValueSequence`, causing data loss or `ArgumentOutOfRangeException`. Fix the converter; the temporary escape hatch is the AppContext switch `Microsoft.AspNetCore.UseStreamBasedJsonParsing=true`.
- **`.localhost` TLD:** Kestrel binds `*.localhost` to loopback, not `0.0.0.0`. The dev cert covers `*.dev.localhost`. `dotnet new web --localhost-tld` uses it.
- **HTTP.sys:** `HttpSysOptions.RequestQueueSecurityDescriptor` sets a custom ACL on new request queues.
- **Testing:** A source generator emits `public partial class Program`, so tests can use `WebApplicationFactory<Program>` without boilerplate. An analyzer suggests removing a manual declaration.
- **Empty form strings bind to null** for nullable value types in `[FromForm]` complex objects in Minimal APIs.
- **`RedirectHttpResult.IsLocalUrl(url)`** helps prevent open redirects:

```csharp
if (RedirectHttpResult.IsLocalUrl(returnUrl)) return Results.LocalRedirect(returnUrl);
```

- **TypedResults in controllers:** The 10 analyzer-deprecation page states that `TypedResults` are supported in controller APIs in .NET 10, so `Task<Results<Ok<T>, NotFound>>` works as an action return type.
- **Networking (runtime):** HTTP/3 is disabled by default with `PublishTrimmed` (source-incompatible).
- Source: what's new 10, Miscellaneous. Also <https://learn.microsoft.com/dotnet/core/compatibility/10>

## SignalR in 10

- The 10 what's new page has an empty SignalR section, so there are no notable server features. SignalR endpoints get `IDisableCookieRedirectMetadata`, so they return 401/403 with cookie auth.

## Obsoletions introduced in 10 (all source-incompatible warnings)

| API | Diagnostic | Replacement |
| --- | --- | --- |
| `WebHostBuilder`, `IWebHost`, `WebHost` | ASPDEPR004 / ASPDEPR008 | `WebApplication.CreateBuilder` or `new HostBuilder().ConfigureWebHost(...)` (with `UseTestServer()` + `host.GetTestServer()` in tests) |
| Razor runtime compilation (`AddRazorRuntimeCompilation`, `MvcRazorRuntimeCompilationOptions`, ...) | ASPDEPR003 | Build-time compilation plus Hot Reload |
| `IActionContextAccessor`, `ActionContextAccessor` | ASPDEPR006 | `IHttpContextAccessor` + `HttpContext.GetEndpoint()?.Metadata.GetMetadata<ActionDescriptor>()` |
| `Microsoft.AspNetCore.HttpOverrides.IPNetwork`, `ForwardedHeadersOptions.KnownNetworks` | ASPDEPR005 | `System.Net.IPNetwork` + `KnownIPNetworks` |
| `WithOpenApi()` | ASPDEPR002 | `AddOpenApiOperationTransformer` |
| `IncludeOpenAPIAnalyzers` MSBuild property and MVC API analyzers | ASPDEPR007 | `TypedResults` / `Results<...>` return types |
| `Microsoft.Extensions.ApiDescription.Client` (`OpenApiReference`, `dotnet openapi`) | Build warning | NSwag, Kiota, or openapi-generator CLIs |

```csharp
// Old
var host = new WebHostBuilder().UseKestrel().UseStartup<Startup>().Build();
// New
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

// Old
app.UseForwardedHeaders(new ForwardedHeadersOptions { KnownNetworks = { new Microsoft.AspNetCore.HttpOverrides.IPNetwork(IPAddress.Parse("10.0.0.0"), 8) } });
// New
var fho = new ForwardedHeadersOptions { ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto };
fho.KnownIPNetworks.Add(System.Net.IPNetwork.Parse("10.0.0.0/8"));
app.UseForwardedHeaders(fho);
```

`System.Net.IPNetwork.Parse` with CIDR notation is standard BCL API since .NET 8; the `KnownIPNetworks` property name comes from the breaking-change page.

- Sources: <https://learn.microsoft.com/aspnet/core/breaking-changes/10/overview> and the linked pages for each item.
