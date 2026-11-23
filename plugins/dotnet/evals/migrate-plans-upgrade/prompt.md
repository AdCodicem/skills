---
description: migrate fires on an upgrade request and plans the SDK pin and breaking changes.
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

Our solution targets net8.0 everywhere (ASP.NET Core API + EF Core 8 with SQL Server,
xUnit tests, global.json pinned to 8.0.400). .NET 8 is out of support: plan the upgrade
to .NET 10. Give me the plan only, don't change anything.
