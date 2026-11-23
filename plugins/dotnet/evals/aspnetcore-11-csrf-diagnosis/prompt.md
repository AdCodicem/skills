---
description: aspnetcore explains the ASP.NET Core 11 automatic CSRF protection and the CORS fix.
tags: [precision]
max_turns: 12
allowed_tools: [Skill, Read, Glob, Grep]
---

We upgraded our ASP.NET Core app from net10.0 to net11.0. Since then, the HTML form
on https://app.contoso.com that posts to our API (`app.MapPost("/subscribe", ([FromForm] string
email) => ...)`, cookie authentication) gets HTTP 400. Same-origin posts still work. Why, and
what is the right fix? Short answer with code.
