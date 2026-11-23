---
description: aspnetcore fires on a Minimal API request and uses built-in validation.
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

In my ASP.NET Core Minimal API (Microsoft.NET.Sdk.Web, net10.0), add a POST /products
endpoint that accepts a product with a required name and a quantity between 1 and 1000,
and returns 400 with problem details when invalid. Show Program.cs only, don't write files.
