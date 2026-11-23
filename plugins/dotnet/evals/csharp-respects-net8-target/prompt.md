---
description: csharp keeps to C# 12 on a net8.0 project: no field keyword, a classic backing field.
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

My project's .csproj has `<TargetFramework>net8.0</TargetFramework>` and no LangVersion.
Add a `Email` property to this class that trims the value and rejects null.
Reply with the code only, don't write files.

```csharp
public class Contact
{
    public string Name { get; set; } = "";
}
```
