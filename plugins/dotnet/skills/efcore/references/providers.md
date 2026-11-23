# Provider support matrix

Check the provider before using a provider-specific feature. Blank cells mean
unsupported or not verified: check the provider documentation.

| Feature | SQL Server | Azure SQL | PostgreSQL (Npgsql) | SQLite | Cosmos |
| --- | --- | --- | --- | --- | --- |
| LeftJoin/RightJoin (10), FullJoin (11) | yes | yes | relational, expected (not explicitly verified in Npgsql notes) | yes (RIGHT/FULL JOIN need SQLite 3.39+, not verified in EF docs) | no |
| Named query filters (10) | yes | yes | yes | yes | yes |
| Complex types JSON (10) | `json` (2025/compat 170) or nvarchar | `json` | `jsonb` (Npgsql 10) | text | EF11 |
| ExecuteUpdate into JSON (10) | `.modify()` / JSON_MODIFY | yes | `jsonb_set` | provider-dependent | n/a |
| Vector distance (10) | SQL Server 2025 | yes | pgvector via Npgsql plugin (not covered here) | no | yes (GA in 10) |
| VectorSearch + vector index (11) | experimental, 2025 | experimental | | | (Cosmos has own vector index) |
| Full-text | FTS catalogs/indexes + TVFs (11) | | (Npgsql has own tsvector support) | | FullTextContains/Score + RRF (10) |
| JSON indexes (11) | SQL Server 2025 | | Npgsql 11: HasIndex on ToJson (B-tree/GIN) | | indexing policy (11) |

Open points (not verified when this was written):

- Public API to opt vector properties back into auto-loading in EF11 GA (the docs say "later in the EF Core 11 release"; only internal `IsAutoLoaded` was seen).
- The diagnostic ID of the EF10 raw-SQL concatenation analyzer.
- Explicit Npgsql/SQLite confirmation for LeftJoin/RightJoin/FullJoin translation and the minimum SQLite version for RIGHT/FULL JOIN.
