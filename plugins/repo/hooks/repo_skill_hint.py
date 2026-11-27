"""UserPromptSubmit hook: point Claude at /repo:init for repository setup and audits.

The skill's description alone is often skipped for short requests about one
part of a repository ("add CI with pytest and ruff, just list the files"): the
evals measured 1 trigger in 3 for such a request. When the prompt asks to set
up, initialize, standardize or audit a repository or one of its parts (CI,
release pipeline, dependency bot, rulesets, infrastructure as code), or names a
tool of that domain, this hook adds a short reminder to load the skill. It
prints nothing otherwise. Reads the hook event as JSON on stdin and always
exits 0: it must never block or break a prompt. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys

# Terms that only appear in repository tooling requests.
DOMAIN = re.compile(
    r"\brenovate\b|\bdependabot\b|\brulesets?\b|branch protection|protection de branche"
    r"|semantic-release|release-please|\bcodeql\b|\bzizmor\b|\bactionlint\b|\bscorecard\b"
    r"|pre-commit|trusted publish|infrastructure as code|\biac\b|\bbicep\b|\bpulumi\b"
    r"|\bwrangler\b|github actions?|actions\.lock|\.github/workflows",
    re.IGNORECASE,
)

# An intent to set up or audit (English and French)...
VERB = re.compile(
    r"\b(?:init(?:iali[sz]e|ialiser)?|set\s?up|bootstrap|scaffold|standardi[sz]e|audit(?:er)?"
    r"|harden|upgrade|met(?:s|tre)?\s+(?:\S+\s+){0,3}à\s+niveau"
    r"|configure[rz]?|ajoute[rz]?|add|cr[ée]e[rz]?|create|new)\b",
    re.IGNORECASE,
)
# ...applied to a repository or one of its parts. "CI" is matched in capitals
# only: "ci" is a common French word ("celle-ci", "ci-dessous").
OBJECT = re.compile(
    r"\b(?:repo|repos|repository|repositories|d[ée]p[ôo]t|pipelines?|workflows?|releases?"
    r"|deployments?|d[ée]ploiements?|infra|infrastructure)\b",
    re.IGNORECASE,
)
CI = re.compile(r"\bCI(?:/CD)?\b")

HINT = (
    "This request is about setting up, auditing or upgrading a repository or one of its parts "
    "(CI, release or deployment pipeline, dependency updates, rulesets, infrastructure as code). "
    "Load the repo:init skill with the Skill tool before answering, even when only one part or "
    "only a list of files is asked: it holds the standard, the scripts that resolve the latest "
    "versions, and the questions to ask first."
)


def hint(prompt: str) -> str | None:
    """The reminder to add for this prompt, or None when it is not repository tooling."""
    if DOMAIN.search(prompt):
        return HINT
    if VERB.search(prompt) and (OBJECT.search(prompt) or CI.search(prompt)):
        return HINT
    return None


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
    message = hint(prompt)
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
