---
description: csharp switches over a C# 15 union with a null arm instead of a discard.
tags: [precision]
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

The project targets net11.0. Given these types, write a method
`static string Describe(Pet pet)` that returns "cat Tom" or "dog Rex" with a switch expression.
Reply with the method only.

```csharp
public record Cat(string Name);
public record Dog(string Name);
public union Pet(Cat, Dog);
```
