---
description: csharp fires on a modernization request for a net10.0 project and uses the field keyword.
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

This class is in a project whose .csproj has `<TargetFramework>net10.0</TargetFramework>`
and no LangVersion. Modernize it. Reply with the new code only, don't write files.

```csharp
public class Customer
{
    private string _name = "";
    public string Name
    {
        get { return _name; }
        set { _name = value?.Trim() ?? throw new ArgumentNullException(nameof(value)); }
    }
}
```
