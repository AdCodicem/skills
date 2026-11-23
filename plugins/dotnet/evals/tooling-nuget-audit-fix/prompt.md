---
description: tooling fixes a NuGet audit error without disabling the audit.
tags: [precision]
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

After moving our solution to .NET 10, `dotnet build` fails with
`error NU1903: Warning As Error: Package 'Newtonsoft.Json' 12.0.1 has a known high severity
vulnerability`. We don't reference Newtonsoft.Json directly and we use TreatWarningsAsErrors.
How do we fix it? Short answer with commands and project changes.
