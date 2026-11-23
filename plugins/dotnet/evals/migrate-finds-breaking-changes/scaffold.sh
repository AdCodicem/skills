#!/usr/bin/env bash
# Writes the fixture project into the run's working directory.
set -euo pipefail

cat > 'Directory.Build.props' <<'FIXTURE'
<Project>
  <PropertyGroup>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
  </PropertyGroup>
</Project>
FIXTURE

cat > 'global.json' <<'FIXTURE'
{
  "sdk": { "version": "9.0.100", "rollForward": "latestFeature" }
}
FIXTURE

mkdir -p 'src/Api'
cat > 'src/Api/Api.csproj' <<'FIXTURE'
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.AspNetCore.OpenApi" Version="9.0.11" />
    <PackageReference Include="System.Linq.Async" Version="6.0.3" />
  </ItemGroup>
</Project>
FIXTURE

mkdir -p 'src/Api'
cat > 'src/Api/Program.cs' <<'FIXTURE'
using Microsoft.AspNetCore.Authentication.Cookies;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
    .AddCookie(o => o.LoginPath = "/login");
builder.Services.AddAuthorization();
builder.Services.AddOpenApi();
var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();
app.MapOpenApi();

app.MapGet("/api/orders", (OrderStore store) =>
        store.GetOrdersAsync().SelectAwait(async o => await store.EnrichAsync(o)))
    .RequireAuthorization()
    .WithOpenApi(op => { op.Summary = "Lists orders"; return op; });

app.MapGet("/login", () => Results.Content("<form method='post'>...</form>", "text/html"));
app.Run();

public sealed class OrderStore
{
    public async IAsyncEnumerable<string> GetOrdersAsync()
    {
        await Task.Yield();
        yield return "order-1";
    }

    public Task<string> EnrichAsync(string order) => Task.FromResult(order.ToUpperInvariant());
}
FIXTURE

