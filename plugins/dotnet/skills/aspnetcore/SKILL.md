---
name: aspnetcore
description: 'Write, review and modernize ASP.NET Core web APIs and server code with what ASP.NET Core 10 and 11 added: built-in Minimal API validation (sync and async), TypedResults and Server-Sent Events, built-in OpenAPI 3.1/3.2 with XML comments, passkeys in Identity, automatic CSRF protection, cookie auth returning 401/403 on APIs, JSON Patch on System.Text.Json, OpenTelemetry, rate limiting, SignalR auth refresh, plus the obsoleted APIs to avoid and the breaking changes when upgrading. Matches the ASP.NET Core version the project targets. Use whenever writing or reviewing Program.cs, Minimal API endpoints, controllers, middleware, authentication, OpenAPI or SignalR code in a .NET web project, or when asked to modernize, secure or upgrade an ASP.NET Core app. Example requests: "add a POST endpoint with validation", "stream progress to the client", "secure this API", "ajoute OpenAPI à cette API", "modernise ce Program.cs". Not for Blazor UI components.'
metadata:
  surfaces: claude-code
---

# ASP.NET Core 10 and 11

Make web code use the hosting model, APIs and security defaults of the
ASP.NET Core version the project targets. ASP.NET Core 10 is LTS (`net10.0`);
ASP.NET Core 11 is STS (`net11.0`), GA since 2026-11-10. ASP.NET Core 8 and 9
are out of support. Blazor components are out of scope.

## Before writing code

1. **Detect the target** (use `python` if `python3` is missing):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/csharp/scripts/detect_target.py" <path>
   ```

   The ASP.NET Core version follows the target framework (`Microsoft.NET.Sdk.Web`
   or a `Microsoft.AspNetCore.App` framework reference). Also note the C#
   version: the `csharp` skill covers language features.
2. **Read how the app is built** before adding to it: Minimal APIs or
   controllers, route groups, authentication scheme, OpenAPI package (built-in
   `Microsoft.AspNetCore.OpenApi` or Swashbuckle/NSwag), validation library.
   Extend the existing approach; propose a switch only when asked or when the
   current one is obsolete.
3. **Load the reference you need**:
   - [references/aspnetcore-10.md](references/aspnetcore-10.md): validation, SSE, OpenAPI 3.1, passkeys, cookie 401/403, JSON Patch, obsoletions.
   - [references/aspnetcore-11.md](references/aspnetcore-11.md): automatic CSRF, async validation, unions in JSON, OpenAPI 3.2, SignalR, OpenTelemetry, Kestrel.
   - [references/breaking-changes.md](references/breaking-changes.md): upgrading to 10 and 11.
4. **When a detail is not covered or looks uncertain**, check Microsoft Learn
   with the `microsoft_docs_search` / `microsoft_docs_fetch` tools if they are
   available. Learn's "What's new in ASP.NET Core 11" page may still read like a
   preview: the content is current.

## Rules

- **Change only what the task needs.** New code uses current APIs; in existing
  code you touch, *mention* obsolete or weaker patterns, do not rewrite them
  unless asked.
- **Modern only when it improves the code**: less code, a safer default, better
  performance or observability.
- **Never generate obsolete APIs**: `WebHostBuilder` / `IWebHost` / `WebHost`
  (ASPDEPR004/008), `UseStartup` on a web host builder, `WithOpenApi()`
  (ASPDEPR002), `IActionContextAccessor` (ASPDEPR006),
  `HttpOverrides.IPNetwork` / `KnownNetworks` (ASPDEPR005), Razor runtime
  compilation (ASPDEPR003), `SetCompatibilityVersion`, the removed
  `UseConcurrencyLimiter` middleware (11), `TlsClientHelloBytesCallback` (11).
- **Experimental** (Device Bound Session Credentials, the validation resolver
  APIs in 10): explain them, never introduce them unasked.

## Use this, not that

| Instead of | Prefer | Needs |
| --- | --- | --- |
| `new WebHostBuilder()...UseStartup<Startup>()` | `WebApplication.CreateBuilder(args)` | any supported version |
| Manual `Validator.TryValidateObject` in handlers | `builder.Services.AddValidation();` + DataAnnotations on records | 10 |
| Sync-only validators calling services with `.Result` | `AsyncValidationAttribute`, `IAsyncValidatableObject` | 11 |
| `IResult` / `Results.Ok` without types | `TypedResults` with `Results<Ok<T>, NotFound>` return types | 7 (in controllers: 10) |
| Hand-written `text/event-stream` loop | `TypedResults.ServerSentEvents(asyncEnumerable, eventType: "x")` | 10 |
| Swashbuckle for document generation | `AddOpenApi()` + `MapOpenApi()`; XML docs via `GenerateDocumentationFile` and method-group handlers | 9 (3.1 in 10, 3.2 in 11) |
| `.WithOpenApi(op => ...)` | `.WithSummary()`, `.WithDescription()` or `.AddOpenApiOperationTransformer(...)` | 10 |
| Try/catch in every endpoint | `AddProblemDetails()` + `IExceptionHandler` + `UseExceptionHandler()` | 8 |
| Newtonsoft JSON Patch + `AddNewtonsoftJson` | `Microsoft.AspNetCore.JsonPatch.SystemTextJson` on a DTO | 10 |
| Custom WebAuthn library with Identity | Identity passkeys (`IdentitySchemaVersions.Version3`, explicit `ServerDomain`) | 10 |
| Token antiforgery only, for form posts | Automatic CSRF (header based), on by default; CORS with explicit origins and `AllowCredentials` for trusted cross-origin callers | 11 |
| `UseConcurrencyLimiter` | `AddRateLimiter(o => o.AddConcurrencyLimiter(...))` + `UseRateLimiter()` | 7 (required in 11) |
| `OpenTelemetry.Instrumentation.AspNetCore` for HTTP spans | `AddSource("Microsoft.AspNetCore")` | 11 |
| `.ShortCircuit()` chains for health or robots endpoints | `[ShortCircuit]` attribute | 11 |
| Manual `Url.IsLocalUrl` checks in Minimal APIs | `RedirectHttpResult.IsLocalUrl(url)` before redirecting | 10 |
| `public partial class Program { }` for tests | Nothing: it is generated | 10 |

## Security

- **Hosts and redirects**: set `AllowedHosts`; validate redirect targets with
  `RedirectHttpResult.IsLocalUrl`; behind proxies configure forwarded headers
  with `KnownIPNetworks` / `KnownProxies`, never trust all.
- **CORS**: explicit origins. Never combine cookie authentication with
  `AllowAnyOrigin`. On 11, a cross-origin form post is only trusted when the
  CORS policy names the origin *and* has `AllowCredentials()`.
- **CSRF (11)**: automatic for form-binding endpoints. Disable it per endpoint
  (`DisableAntiforgery()`) only for non-browser or non-cookie callers such as
  webhooks; never set `DisableCsrfProtection` globally to make an error go away.
- **Cookie-authenticated APIs (10+)** answer 401/403 instead of redirecting:
  keep it, and only re-enable redirects for page endpoints.
- **Passkeys**: set `IdentityPasskeyOptions.ServerDomain` explicitly; HTTPS only.
- **JSON Patch**: patch a dedicated DTO, cap the number of operations, require
  authorization, re-validate after `ApplyTo`, and do not save on error
  (`ApplyTo` mutates even when it reports errors).
- **`[ShortCircuit]`** skips authentication and authorization middleware: never
  on protected endpoints.
- **SignalR auth refresh (11)**: verify in `OnAuthenticationRefresh` that the
  user identity did not change.
- **Validation**: reject unknown JSON members when the contract is strict
  (`JsonUnmappedMemberHandling.Disallow`).

## Performance

- Prefer `TypedResults` and source-generated validation (AOT friendly, no
  reflection scanning). For NativeAOT, use `CreateSlimBuilder` and a
  `JsonSerializerContext`.
- Stream with `IAsyncEnumerable<T>` / SSE instead of buffering large results.
- Custom `JsonConverter`s must handle `Utf8JsonReader.HasValueSequence`:
  request bodies are parsed from a `PipeReader` since 10.
- Output caching and rate limiting are built in; Zstandard compression is
  available in 11 (`AddResponseCompression`).
- Observability: OpenTelemetry with the built-in meters (`Microsoft.AspNetCore.*`,
  including authentication, authorization and Identity in 10).

## Modes

- **Writing code**: apply the rules above to the code you write.
- **Review**: report security findings first (CORS, CSRF, redirects, auth on
  endpoints, secrets in configuration), then obsolete APIs, then
  modernization. Give the version each fix needs.
- **Modernize on request**: list the planned changes first, flagging those that
  change behavior for clients (status codes, OpenAPI document version, CSRF
  400s, cookie redirects). Apply after agreement.
- **Upgrade**: follow [references/breaking-changes.md](references/breaking-changes.md),
  and the `migrate` skill for the rest of the solution.

## Verify

- `dotnet build` with no new ASPDEPR or ASP warnings, then the tests
  (`WebApplicationFactory<Program>` for endpoint tests).
- Run the app and call new endpoints, including an invalid payload (expect a
  400 problem details) and an unauthenticated call (expect 401, not 302).
- When OpenAPI changed, fetch `/openapi/v1.json` and check the new operations.
