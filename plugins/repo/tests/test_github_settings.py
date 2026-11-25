"""Tests for skills/init/scripts/github_settings.py, with a fake gh."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "init" / "scripts" / "github_settings.py"
spec = importlib.util.spec_from_file_location("github_settings", SCRIPT)
gs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = gs
spec.loader.exec_module(gs)

REPO = "me/lib"


class FakeGh:
    """Answers `gh api --include --method M endpoint` from a table; records writes."""

    def __init__(self, responses: dict[tuple[str, str], tuple[int, object]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, object]] = []

    def __call__(self, args: list[str], stdin: str | None) -> tuple[int, str, str]:
        method, endpoint = args[args.index("--method") + 1], args[args.index("--method") + 2]
        body = json.loads(stdin) if stdin else None
        self.calls.append((method, endpoint, body))
        status, data = self.responses.get((method, endpoint), (404, {"message": "Not Found"}))
        if method != "GET" and (method, endpoint) not in self.responses:
            status, data = 204, None
        payload = "" if data is None else json.dumps(data)
        out = f"HTTP/2.0 {status} X\r\ncontent-type: application/json\r\n\r\n{payload}"
        return (0 if status < 400 else 1), out, ("" if status < 400 else f"gh: (HTTP {status})")

    def writes(self) -> list[tuple[str, str, object]]:
        return [c for c in self.calls if c[0] != "GET"]


def responses(visibility="public", owner_type="User", plan="free", overrides=None):
    base = {
        ("GET", f"repos/{REPO}"): (
            200,
            {
                "visibility": visibility,
                "owner": {"type": owner_type, "login": "me"},
                "permissions": {"admin": True},
                "allow_squash_merge": True,
                "allow_merge_commit": True,
                "allow_rebase_merge": True,
                "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
                "squash_merge_commit_message": "COMMIT_MESSAGES",
                "allow_auto_merge": False,
                "delete_branch_on_merge": False,
                "allow_update_branch": False,
                "has_discussions": False,
                "security_and_analysis": {
                    "secret_scanning": {"status": "enabled"},
                    "secret_scanning_push_protection": {"status": "disabled"},
                },
            },
        ),
        ("GET", "user" if owner_type == "User" else "orgs/me"): (
            200,
            {"login": "me", "plan": {"name": plan}},
        ),
        ("GET", f"repos/{REPO}/rulesets"): (200, []),
        ("GET", f"repos/{REPO}/actions/permissions/workflow"): (
            200,
            {"default_workflow_permissions": "write", "can_approve_pull_request_reviews": False},
        ),
        ("GET", f"repos/{REPO}/actions/permissions"): (
            200,
            {"enabled": True, "allowed_actions": "all"},
        ),
        ("GET", f"repos/{REPO}/vulnerability-alerts"): (204, None),
        ("GET", f"repos/{REPO}/automated-security-fixes"): (
            200,
            {"enabled": True, "paused": False},
        ),
        ("GET", f"repos/{REPO}/private-vulnerability-reporting"): (200, {"enabled": False}),
        ("GET", f"repos/{REPO}/immutable-releases"): (200, {"enabled": False}),
        ("GET", f"repos/{REPO}/code-scanning/default-setup"): (200, {"state": "not-configured"}),
        ("GET", "users/me"): (200, {"id": 42, "login": "me"}),
    }
    base.update(overrides or {})
    return base


def changes_by_setting(changes):
    return {c.setting: c for c in changes}


def test_public_personal_repository_gets_the_full_standard():
    fake = FakeGh(responses())
    context, changes = gs.plan(
        gs.GitHub(fake), REPO, "personal-oss", environments=["release"], reviewer="me",
        release_app_id=7,
    )  # fmt: skip
    assert context["plan"] == "free" and context["visibility"] == "public"
    settings = changes_by_setting(changes)
    assert settings["allow_squash_merge"].action == "ok"
    assert settings["allow_merge_commit"].action == "change"
    assert settings["has_discussions"].action == "change"
    ruleset = settings["main"]
    assert ruleset.method == "POST"
    rules = {r["type"]: r.get("parameters") for r in ruleset.body["rules"]}
    assert rules["pull_request"]["required_approving_review_count"] == 0
    assert rules["pull_request"]["allowed_merge_methods"] == ["squash"]
    assert rules["required_status_checks"]["strict_required_status_checks_policy"] is False
    assert [c["context"] for c in rules["required_status_checks"]["required_status_checks"]] == [
        "gate",
        "pr-title",
        "workflows",
        "pre-commit",
    ]
    assert ruleset.body["bypass_actors"] == [
        {"actor_id": 7, "actor_type": "Integration", "bypass_mode": "always"}
    ]
    assert settings["Dependabot alerts"].action == "ok"
    assert settings["Dependabot security updates"].method == "DELETE"
    assert settings["secret_scanning"].action == "ok"
    assert settings["secret_scanning_push_protection"].action == "change"
    assert settings["private vulnerability reporting"].action == "change"
    assert settings["CodeQL default setup"].action == "change"
    assert settings["sha_pinning_required"].action == "change"
    assert settings["release"].body["reviewers"] == [{"type": "User", "id": 42}]
    assert fake.writes() == []  # planning never writes


def test_private_free_repository_skips_what_the_plan_forbids():
    fake = FakeGh(responses(visibility="private"))
    _, changes = gs.plan(gs.GitHub(fake), REPO, "personal-private", environments=["release"])
    settings = changes_by_setting(changes)
    for name in ("main", "release", "secret_scanning", "private vulnerability reporting",
                 "CodeQL default setup"):  # fmt: skip
        assert settings[name].action == "skip", name
    assert "Pro" in settings["main"].reason
    assert "has_discussions" not in settings


def test_private_pro_repository_has_environments_without_reviewers():
    fake = FakeGh(responses(visibility="private", plan="pro"))
    _, changes = gs.plan(
        gs.GitHub(fake), REPO, "personal-private", environments=["production"], reviewer="me"
    )
    settings = changes_by_setting(changes)
    assert settings["main"].action == "change"
    assert "reviewers" not in settings["production"].body
    assert "dispatch" in settings["production"].reason


def test_company_profile_requires_an_approval_and_lets_actions_approve():
    fake = FakeGh(responses(owner_type="Organization", plan="team"))
    _, changes = gs.plan(gs.GitHub(fake), REPO, "company-oss")
    settings = changes_by_setting(changes)
    rules = {r["type"]: r.get("parameters") for r in settings["main"].body["rules"]}
    assert rules["pull_request"]["required_approving_review_count"] == 1
    assert rules["pull_request"]["require_code_owner_review"] is True
    assert settings["workflow token"].desired["can_approve_pull_request_reviews"] is True
    assert "release App" in settings["main"].reason


def test_existing_ruleset_is_updated_and_its_bypass_kept():
    existing = {
        "id": 9,
        "name": "main",
        "enforcement": "active",
        "bypass_actors": [{"actor_id": 3, "actor_type": "Integration", "bypass_mode": "always"}],
        "rules": [
            {"type": "deletion"},
            {"type": "pull_request", "parameters": {"required_approving_review_count": 1}},
        ],
    }
    fake = FakeGh(
        responses(
            overrides={
                ("GET", f"repos/{REPO}/rulesets"): (200, [{"id": 9, "name": "main"}]),
                ("GET", f"repos/{REPO}/rulesets/9"): (200, existing),
            }
        )
    )
    _, changes = gs.plan(gs.GitHub(fake), REPO, "personal-oss")
    ruleset = changes_by_setting(changes)["main"]
    assert ruleset.method == "PUT" and ruleset.endpoint == f"repos/{REPO}/rulesets/9"
    assert ruleset.body["bypass_actors"] == existing["bypass_actors"]
    assert ruleset.reason == ""


def test_apply_makes_only_the_changes_and_reports_failures():
    fake = FakeGh(
        responses(
            overrides={
                ("PATCH", f"repos/{REPO}/code-scanning/default-setup"): (403, {"message": "no"})
            }
        )
    )
    github = gs.GitHub(fake)
    _, changes = gs.plan(github, REPO, "personal-oss", tier="standard")
    ok = gs.apply(github, changes)
    assert ok is False
    written = {(m, e) for m, e, _ in fake.writes()}
    assert ("DELETE", f"repos/{REPO}/automated-security-fixes") in written
    assert ("PATCH", f"repos/{REPO}") in written
    assert ("PUT", f"repos/{REPO}/vulnerability-alerts") not in written  # already enabled
    failed = changes_by_setting(changes)["CodeQL default setup"]
    assert failed.result.startswith("failed (HTTP 403)")


def test_minimal_tier_and_unreadable_immutable_releases():
    fake = FakeGh(responses(overrides={("GET", f"repos/{REPO}/immutable-releases"): (404, None)}))
    _, changes = gs.plan(gs.GitHub(fake), REPO, "personal-oss", tier="minimal")
    settings = changes_by_setting(changes)
    assert settings["CodeQL default setup"].action == "skip"
    assert settings["immutable releases"].action == "skip"
    assert "has_discussions" not in settings


def test_main_exit_codes(capsys):
    plan_only = ["--repo", REPO, "--profile", "personal-oss"]
    assert gs.main(plan_only, gh=gs.GitHub(FakeGh(responses()))) == 1
    assert "change" in capsys.readouterr().out
    unreadable = gs.GitHub(FakeGh({}))
    assert gs.main(plan_only, gh=unreadable) == 2
    fake = FakeGh(responses())
    args = ["--repo", REPO, "--profile", "personal-oss", "--apply", "--json"]
    assert gs.main(args, gh=gs.GitHub(fake)) == 0
    output = json.loads(capsys.readouterr().out)
    assert all(c["result"] == "applied" for c in output["changes"] if c["action"] == "change")


@pytest.mark.parametrize(
    ("visibility", "owner", "plan", "rulesets", "reviewers"),
    [
        ("public", "User", "free", True, True),
        ("private", "User", "free", False, False),
        ("private", "User", "pro", True, False),
        ("private", "Organization", "team", True, False),
        ("private", "Organization", "enterprise", True, True),
        ("private", "Organization", None, True, False),
    ],
)
def test_capabilities(visibility, owner, plan, rulesets, reviewers):
    can = gs.capabilities(visibility, owner, plan, code_security=False)
    assert can["rulesets"] is rulesets
    assert can["environment_reviewers"] is reviewers
