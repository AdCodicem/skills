---
name: greet
description: Greet someone by name in English, French, Spanish or German, optionally as an ASCII banner. Use when the user asks to say hello to, welcome or greet a person, or asks for a greeting banner.
metadata:
  surfaces: claude-code, claude-ai, api
---

# Greet

Produce a greeting for a named person with the bundled script, so that the
wording is always the same for a given language.

## Workflow

1. Identify the person's name and the language. Default to English when the
   user gives no language. Supported codes: `en`, `fr`, `es`, `de`.
2. Run the script from this skill's folder:

   ```bash
   python3 scripts/greet.py --name "Ada" --lang fr
   ```

   Add `--banner` when the user asks for a banner or something eye-catching.
3. Reply with the script's output unchanged. If the script reports an
   unsupported language, tell the user which languages are available.

The script only uses the Python standard library, so it runs in Claude Code,
on claude.ai and in the Claude API code execution container.
