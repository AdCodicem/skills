---
type: llm
criteria: >-
  PASS if the Contact class the answer proposes does not use the C# 14 `field` keyword in its
  accessors (the project targets net9.0, C# 13). Mentioning `field` only as an option after
  upgrading to .NET 10 is a PASS. FAIL if the proposed class itself uses `field`.
---
