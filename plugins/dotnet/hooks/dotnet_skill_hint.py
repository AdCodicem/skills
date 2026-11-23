"""UserPromptSubmit hook: point Claude at the dotnet plugin skills for .NET work.

Skill descriptions alone do not always make Claude load a skill for short requests
("code only"). When the prompt is about .NET, or the session runs in a .NET
repository, this hook adds a short reminder listing the skills that match the
prompt. It prints nothing otherwise. Reads the hook event as JSON on stdin and
always exits 0: it must never block or break a prompt. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DOTNET_PROMPT = re.compile(
    r"(?<![\w#])C#(?![\w#])|\.NET\b|\bdotnet\b|\bnet\d{1,2}\.\d\b|\bcsproj\b|\.slnx?\b"
    r"|\bASP\.NET\b|\bEF\s?Core\b|\bEntity\s?Framework\b|\bDbContext\b|\bNuGet\b|\bMSBuild\b"
    r"|\bRoslyn\b|\bIAsyncEnumerable\b|\bxUnit\b|\bMSTest\b|\bNUnit\b|\bBlazor\b|\bRazor\b"
    r"|\bSystem\.(?:Text|Linq|IO|Net|Security|Collections|Threading)\b|\bLangVersion\b"
    r"|\bTargetFramework\b|\bglobal\.json\b",
    re.IGNORECASE,
)

SKILLS = {
    "csharp": (
        "any C# code (language features allowed by the target framework)",
        r".",  # every .NET prompt that involves code
    ),
    "runtime-libraries": (
        "JSON, LINQ and IAsyncEnumerable, collections, IO, processes, crypto, threading, perf",
        r"json|linq|i?async\s?enumerable|collection|dictionary|stream|file|zip|process|"
        r"crypt|hash|password|pbkdf|certificate|thread|lock|task|regex|perf|optimi|alloc|span",
    ),
    "aspnetcore": (
        "ASP.NET Core endpoints, middleware, auth, OpenAPI, SignalR",
        r"asp\.net|minimal\s?api|endpoint|controller|middleware|program\.cs|openapi|swagger|"
        r"signalr|kestrel|cors|csrf|antiforgery|auth|cookie|jwt|passkey|webapplication",
    ),
    "efcore": (
        "EF Core DbContext, entity configuration, queries, migrations",
        r"ef\s?core|entity\s?framework|dbcontext|dbset|migration|linq to entities|"
        r"sql\s?server|postgres|npgsql|sqlite|cosmos|executeupdate|owned type|complex type",
    ),
    "tooling": (
        "SDK, CLI, csproj and props files, NuGet, tests, C# scripts",
        r"csproj|\.props|global\.json|nuget|nu\d{4}|dotnet (?:run|test|build|tool|new|sln|package)|"
        r"slnx?|msbuild|xunit|mstest|nunit|testing\.platform|script|dnx|analy[sz]er",
    ),
    "migrate": (
        "upgrading a solution to .NET 10 or 11",
        r"upgrad|migrat|retarget|move (?:to|from) \.?net|passe[rz]? (?:en|à)|mont[ée]e de version",
    ),
}

REPO_MARKERS = ("*.sln", "*.slnx", "*.csproj", "global.json", "Directory.Build.props")


def is_dotnet_repo(cwd: str | None) -> bool:
    if not cwd:
        return False
    root = Path(cwd)
    try:
        if any(next(root.glob(pattern), None) for pattern in REPO_MARKERS):
            return True
        return next(root.glob("src/*/*.csproj"), None) is not None
    except OSError:
        return False


def hint(prompt: str, cwd: str | None) -> str | None:
    """The reminder to add for this prompt, or None when it is not .NET work."""
    if not (DOTNET_PROMPT.search(prompt) or is_dotnet_repo(cwd)):
        return None
    lowered = prompt.lower()
    matched = [name for name, (_, pattern) in SKILLS.items() if re.search(pattern, lowered)]
    lines = [
        "This request involves .NET. Before writing, changing or reviewing code, load the "
        "matching skills of the dotnet plugin with the Skill tool, even for a short snippet: "
        "they detect the project's target framework and hold the .NET 10/11 and C# 14/15 "
        "details. Skip them for questions that involve no code.",
    ]
    lines += [f"- dotnet:{name}: {SKILLS[name][0]}" for name in matched]
    return "\n".join(lines)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    if not isinstance(event, dict):
        return 0
    prompt = event.get("prompt")
    if not isinstance(prompt, str):
        return 0
    message = hint(prompt, event.get("cwd") if isinstance(event.get("cwd"), str) else None)
    if message:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": message,
            }
        }
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
