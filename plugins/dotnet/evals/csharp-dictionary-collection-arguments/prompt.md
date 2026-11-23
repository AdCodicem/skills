---
description: csharp knows C# 15 collection expression arguments do not target IDictionary.
tags: [precision]
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

The project targets net11.0 (C# 15). Rewrite this class with C# 15 collection
expression arguments where possible. Keep the field types and the public API unchanged.
Reply with the code only.

```csharp
public sealed class WordStats
{
    private readonly IDictionary<string, int> _counts =
        new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
    private readonly HashSet<string> _stopWords =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { "a", "the" };

    public int Count(string word) => _counts.TryGetValue(word, out var n) ? n : 0;
}
```
