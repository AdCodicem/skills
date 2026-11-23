---
description: efcore knows EF Core 11 no longer loads SqlVector properties by default.
tags: [precision]
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

After upgrading to EF Core 11 (SQL Server provider), `Blog.Embedding`
(`SqlVector<float>`, column `vector(1536)`) is always null when we load blogs with
`await db.Blogs.Where(b => b.Id == id).SingleAsync()`. Saving still works. What changed and
how do we read the embedding? Short answer with code.
