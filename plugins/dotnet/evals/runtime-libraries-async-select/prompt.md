---
description: runtime-libraries uses in-box async LINQ with explicitly typed lambda parameters.
tags: [precision]
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

net10.0 console app, no extra packages. I have `IAsyncEnumerable<int> ids` and
`Task<string> LoadNameAsync(int id, CancellationToken ct)`. Write the LINQ expression that maps
ids to names asynchronously, passing the cancellation token, and returns an
`IAsyncEnumerable<string>`. Code only.
