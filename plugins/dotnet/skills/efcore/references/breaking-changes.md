# Breaking changes when upgrading EF Core

## Breaking changes when upgrading to EF Core 10 (from 9)

| Change | Impact | Mitigation |
| --- | --- | --- |
| EF tools require `--framework` for multi-targeted projects | Medium | `dotnet ef ... --framework net10.0` |
| Microsoft.Data.SqlClient 6.1.x adds `Microsoft.Identity.Client.Broker` dependency (larger publish) | Low | If you don't use Entra ID, reference SqlClient 7.x explicitly (no Azure auth deps in core) |
| `Application Name` injected into connection string when absent; separate pools from Dapper/ADO with the same string, possible distributed transaction escalation in `TransactionScope` | Low | Set `Application Name` explicitly |
| `json` type used by default with `UseAzureSql` or compat 170+; migration ALTERs nvarchar JSON columns | Low | `UseCompatibilityLevel(160)` or `HasColumnType("nvarchar(max)")` |
| Parameterized collections use multiple parameters by default | Low | `UseParameterizedCollectionMode(ParameterTranslationMode.Parameter)` or per query `EF.Parameter(...)` |
| `ExecuteUpdate` setters param is `Func<>` (non-expression) | Low | Replace hand-built expression trees with a statement lambda |
| Complex type column names uniquified (no silent sharing) | Low | `HasColumnName` explicitly if sharing was intended |
| Nested complex columns use the full path (`Complex_Nested_Prop`) | Low | `HasColumnName("Nested_Prop")` to keep old names |
| `IDiscriminatorPropertySetConvention` takes `IConventionTypeBaseBuilder` | Low | Update custom conventions |
| `IRelationalCommandDiagnosticsLogger` methods add `logCommandText` | Low | Update custom implementations |
| SQL parameter names simplified (`@city`) | Low | Update SQL snapshot tests and interceptors that parse names; expect a plan recompile spike |
| **Microsoft.Data.Sqlite**: `GetDateTimeOffset` without offset assumes UTC; DateTimeOffset written to REAL as UTC; `GetDateTime` with offset returns UTC | **High** | Fix code; temporary fallback `AppContext.SetSwitch("Microsoft.Data.Sqlite.Pre10TimeZoneHandling", true)` |
| Requires .NET 10 runtime/SDK | | Retarget to net10.0 |
| Npgsql 10: array `Contains` translates to `= ANY(...)` (use a GIN index via `HasMethod("gin")` to get `@>`); `Network()`/`Merge()` return `IPNetwork` | | Per Npgsql release notes |

Source: <https://learn.microsoft.com/en-us/ef/core/what-is-new/ef-core-10.0/breaking-changes>, <https://www.npgsql.org/efcore/release-notes/10.0.html>

## Breaking changes when upgrading to EF Core 11 (from 10)

| Change | Impact | Mitigation |
| --- | --- | --- |
| Cosmos: unmapped JSON properties no longer preserved (lost on save) | **High** | Map every property, or use `CosmosClient` directly |
| Cosmos: sync I/O fully removed (no opt-in) | Medium | Use async APIs only |
| Microsoft.Data.SqlClient 7.0: Entra ID auth moved out of core; `ActiveDirectoryPassword` obsolete | Medium | Add `Microsoft.Data.SqlClient.Extensions.Azure`; move to `ActiveDirectoryDefault`/`Interactive` |
| Cosmos: projection evaluating to `undefined` throws | Medium | `EF.Functions.IsDefined` filter or `CoalesceUndefined` |
| Cosmos: illegal `id` characters (`/ \ ? #`) no longer escaped; existing docs with `^2F` etc. not found | Medium | `AppContext.SetSwitch("Microsoft.EntityFrameworkCore.EscapeIllegalCosmosIdCharacters", true)` (keeps the collision bug) |
| Cosmos: `__jObject` removed; Newtonsoft no longer used | Low | Use `CosmosClient` + `JsonElement` for raw docs |
| SQL Server default compat level 150 changed to 160 (LEAST/GREATEST etc.) | Low | `UseCompatibilityLevel(150)` for SQL Server 2019 and older |
| `Migrate()` throws when no migrations exist | Low | Remove the call or `ConfigureWarnings(w => w.Ignore(RelationalEventId.MigrationsNotFound))` |
| Scaffolded migration class names include the ID (`_20261118152232_AddBlog`); may trigger CA1707 | Low | `.editorconfig`: `[Migrations/*.cs] dotnet_diagnostic.CA1707.severity = none` |
| `EFOptimizeContext` MSBuild property removed | Low | Use `EFScaffoldModelStage`/`EFPrecompileQueriesStage` (`build`/`publish`); automatic with `PublishAot` |
| Tools/Tasks packages no longer reference `Microsoft.EntityFrameworkCore.Design` | Low | Add `Design` with `PrivateAssets="all"` |
| `SqlVector<T>` not loaded by default (null on entities) | Low | Project explicitly |
| Cosmos: empty owned collections materialize as empty, not null | Low | Drop null checks |
| Cosmos: discriminator model property is `Discriminator` (JSON still `$type`) | Low | Update `EF.Property(e, "$type")` to `"Discriminator"` |
| Cosmos: float to fixed-point materialization truncates instead of rounding | Low | `Math.Round` explicitly |
| Owned JSON collections without explicit key are obsolete (`OwnedEntityMappedToJsonCollectionWarning`) | Low | Migrate to `ComplexCollection(...).ToJson()`, or add a key; suppress via `CoreEventId.OwnedEntityMappedToJsonCollectionWarning` |
| `Property()` no longer configures primitive collections | Low | Use `PrimitiveCollection()` |
| Split queries throw `DbQueryConcurrencyException` on concurrent modification (previously returned empty collections silently) | Low | Retry, wrap in a Serializable/Snapshot transaction, or use `AsSingleQuery()` |
| Same owned instance on two navigations throws | Low | Copy the instance, or switch to a complex type |
| **Microsoft.Data.Sqlite 11**: targets `net10.0` only (no .NET Framework) | Medium | Stay on 10.0.x for .NET Framework |
| SQLitePCLRaw bundles (`bundle_e_sqlcipher`, `bundle_sqlite3`, `bundle_winsqlite3`, `bundle_green`, `bundle_e_sqlite3mc`) unmaintained, incompatible with SQLitePCLRaw.Core 3.x | Medium | Switch to provider packages + `SQLitePCL.raw.SetProvider(...)`; for encryption use `SQLite3MC.PCLRaw.bundle` |
| SQLite: no UWP / classic Xamarin native builds | Low | Move to Windows App SDK / MAUI |
| Requires .NET 11 | | Retarget to net11.0 |
| Npgsql 11: assumes PostgreSQL 16 (was 14); transient failures no longer wrapped in `InvalidOperationException`; serialization failures and deadlocks in `SaveChanges` throw `DbUpdateConcurrencyException`; `NpgsqlServiceCollectionExtensions` renamed | | `SetPostgresVersion(...)` for older servers; rebuild |

Source: <https://learn.microsoft.com/en-us/ef/core/what-is-new/ef-core-11.0/breaking-changes>, <https://www.npgsql.org/efcore/release-notes/11.0.html>
