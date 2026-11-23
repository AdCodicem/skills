---
description: efcore fires on a left join request and uses the EF Core 10 LeftJoin operator.
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

We use EF Core 10 (Microsoft.EntityFrameworkCore.SqlServer 10.0.x, net10.0). Write a query
that lists every customer with the total of their orders, including customers without
orders. There is no navigation property between Customer and Order, only Order.CustomerId.
Reply with the code only.
