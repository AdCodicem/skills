---
name: efcore
description: 'Write, review and modernize Entity Framework Core code with what EF Core 10 and 11 added: LeftJoin, RightJoin and FullJoin, MaxBy and MinBy, named query filters, complex types mapped to JSON instead of owned types, ExecuteUpdate with regular lambdas, parameterized collection modes, SQL Server 2025 vector and json types, full-text search, plus the security and performance defaults and the upgrade breaking changes, for the EF Core version and provider in use. Use it before writing or reviewing any EF Core code, even a single query: DbContext, entity configuration, LINQ to Entities queries, migrations or raw SQL in a .NET project that references Microsoft.EntityFrameworkCore; also when asked to modernize, optimize or upgrade EF Core code. Example requests: "add a soft-delete filter", "left join orders and customers", "replace these owned types", "optimise cette requête EF", "passe ce DbContext en EF Core 10". Not for Dapper-only or non-.NET data access.'
metadata:
  surfaces: claude-code
---

# EF Core 10 and 11

Make EF Core code use the best construct the project's EF Core version and
database provider support, without breaking what already works. EF Core 10 is
LTS and needs .NET 10; EF Core 11 is STS and needs .NET 11.

## Before writing code

1. **Detect the target.** Run the detection script (use `python` if `python3`
   is missing) on the solution or project folder:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/csharp/scripts/detect_target.py" <path>
   ```

   Note the EF Core package version (the `efcore` stack), the provider package
   (`...SqlServer`, `Npgsql...`, `...Sqlite`, `...Cosmos`), the target framework
   and the C# version. If the script reports nothing for EF Core, read the
   `.csproj` and `Directory.Packages.props` yourself.
2. **Gate every feature** on the EF Core major version, the provider, and for
   SQL Server the server version or compatibility level (`UseCompatibilityLevel`,
   `UseAzureSql`). If the server version is unknown, do not use SQL Server 2025
   features (vector, native `json`, JSON indexes) without asking.
3. **Load the reference you need**, not all of them:
   - [references/ef10.md](references/ef10.md): EF Core 7-9 baseline and EF Core 10.
   - [references/ef11.md](references/ef11.md): EF Core 11.
   - [references/providers.md](references/providers.md): what each provider supports.
   - [references/breaking-changes.md](references/breaking-changes.md): upgrading to 10 and 11.
4. **When a detail is not covered or looks uncertain**, check Microsoft Learn
   with the `microsoft_docs_search` / `microsoft_docs_fetch` tools if they are
   available, before writing code that depends on it.

## Rules

- **Change only what the task needs.** New code uses modern constructs; in
  existing code you touch, *mention* what could be modernized, do not rewrite it
  unless asked.
- **Modern only when it reads better or is safer or faster.** Each row in the
  table below has a reason; if the reason does not apply, keep the simpler form.
- **Experimental or preview APIs** (EF Core 11 `VectorSearch()` and vector
  indexes, NativeAOT precompiled queries): explain them when relevant, never
  introduce them unless the user asks.
- **Upgrades are a separate step.** If a feature would need a newer EF Core or
  .NET, say so and offer the upgrade (the `migrate` skill of this plugin covers
  it); do not bump packages silently.

## Use this, not that

| Instead of | Prefer | Needs |
| --- | --- | --- |
| `GroupJoin` + `SelectMany` + `DefaultIfEmpty` | `LeftJoin` / `RightJoin` (method syntax only); navigations when a relationship exists | EF 10, relational |
| Full outer join emulated with unions | `FullJoin` | EF 11, relational |
| `OrderByDescending(x).FirstOrDefaultAsync()` for "the max" | `MaxByAsync(x)` / `MinByAsync(x)` | EF 11 |
| One combined `HasQueryFilter` and `IgnoreQueryFilters()` | Named filters: `HasQueryFilter("SoftDelete", ...)`, `IgnoreQueryFilters(["SoftDelete"])` | EF 10 |
| `OwnsOne` / `OwnsMany(... ToJson())` for value objects | `ComplexProperty` / `ComplexCollection(..., b => b.ToJson())`, with immutable records | EF 10 (collections must be JSON) |
| Load, modify, `SaveChanges` for set-based updates | `ExecuteUpdateAsync` / `ExecuteDeleteAsync` | EF 7 |
| Hand-built `SetPropertyCalls` expression trees | Statement lambda with `if` inside `ExecuteUpdateAsync` | EF 10 |
| Raw SQL to update a JSON property | `ExecuteUpdateAsync` on a complex type mapped to JSON | EF 10 |
| `TranslateParameterizedCollectionsTo*()` | `UseParameterizedCollectionMode(...)`, or `EF.Parameter` per query | EF 10 |
| `HasData` with computed or dynamic values | `UseSeeding` / `UseAsyncSeeding` (idempotent) | EF 9 |
| `UseSqlServer` against Azure SQL | `UseAzureSql` | EF 9 |
| `EF.Property<DateTime>(e, "PeriodStart")` | Period columns mapped to CLR properties | EF 11 |
| Community vector-search package | `SqlVector<float>` + `EF.Functions.VectorDistance` | EF 10, SQL Server 2025 / Azure SQL |
| `ToAsyncEnumerable()` on a query | `AsAsyncEnumerable()` | any |

## Security

- **Raw SQL**: use `FromSql($"... {value}")` or `SqlQuery<T>($"...")`, which
  parameterize interpolated values. Never concatenate into `FromSqlRaw` /
  `ExecuteSqlRaw`; EF Core 10 ships an analyzer that flags it. Identifiers
  (table or column names) cannot be parameters: validate them against an allowlist.
- **Multitenancy**: put the tenant filter in its own named query filter and
  only ever disable filters by name, so showing soft-deleted rows never drops
  tenant isolation.
- **Logs**: EF Core 10 redacts inlined constants by default. Never enable
  `EnableSensitiveDataLogging()` or detailed errors outside development.
- **SQL Server auth**: Microsoft.Data.SqlClient 7 (EF Core 11) moved Entra ID
  authentication to `Microsoft.Data.SqlClient.Extensions.Azure`;
  `ActiveDirectoryPassword` is obsolete. Prefer `ActiveDirectoryDefault` or
  managed identity.

## Performance

- Read-only queries: `AsNoTracking()` and projection to a DTO with `Select`.
- Collections: `AsSplitQuery()` for several collection includes, always with a
  deterministic `OrderBy` ending on a unique key when paging.
- Large `Contains` lists: the EF Core 10 default (one parameter per value,
  padded) hits SQL Server's ~2100 parameter limit; use `EF.Parameter(list)` or
  `ParameterTranslationMode.Parameter` for big lists.
- Bulk changes: `ExecuteUpdateAsync` / `ExecuteDeleteAsync` instead of tracking.
  They bypass the change tracker: tracked entities are not refreshed.
- Vectors: EF Core 11 no longer loads `SqlVector<T>` columns into entities;
  project them explicitly when needed.
- Several improvements are automatic on upgrade (EF Core 11: leaner SQL for
  to-one includes, no-op `CAST` removal). Mention them as upgrade benefits.

## Modes

- **Writing code**: apply the rules above to the code you write.
- **Review**: report, per finding, the current code, the modern alternative,
  the version it needs, and why (security, performance, readability). Separate
  findings that need an upgrade from those available now.
- **Modernize on request**: list the planned changes first, grouped by risk
  (behavior-preserving vs. behavior- or schema-changing such as owned to complex
  types, which changes column names and migrations). Generate a migration and
  show it before applying anything to a database.
- **Upgrade**: follow [references/breaking-changes.md](references/breaking-changes.md),
  and the `migrate` skill for the rest of the solution.

## Verify

- Build the project (`dotnet build`) and run the tests.
- After a model change, run `dotnet ef migrations add <Name>` and read the
  generated migration: an unexpected rename or column type change (owned to
  complex types, native `json`, named default constraints) means a mapping
  needs `HasColumnName` / `HasColumnType`, or the user must decide.
- For query changes, check the generated SQL with `ToQueryString()` or logging.
