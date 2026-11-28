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
ADMIN_PR_BYPASS = {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"}


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
        ("GET", f"repos/{REPO}/code-scanning/default-setup"): (200, {"state": "configured"}),
        ("GET", "users/me"): (200, {"id": 42, "login": "me"}),
    }
    base.update(overrides or {})
    return base


def changes_by_setting(changes):
    return {c.setting: c for c in changes}


CODEQL_DEFAULT = "CodeQL default setup (off: codeql.yml runs advanced setup)"


def rules_of(change):
    return {r["type"]: r.get("parameters") for r in change.body["rules"]}


def contexts(rule):
    return [c["context"] for c in rule["required_status_checks"]]


def test_public_personal_repository_gets_the_full_standard():
    fake = FakeGh(responses())
    context, changes = gs.plan(
        gs.GitHub(fake),
        REPO,
        "personal-oss",
        environments=["release"],
        reviewer="me",
        release_app_id=7,
        bots_app_id=8,
    )
    assert context["plan"] == "free" and context["visibility"] == "public"
    settings = changes_by_setting(changes)
    assert settings["allow_squash_merge"].action == "ok"
    assert settings["allow_merge_commit"].action == "change"
    assert settings["has_discussions"].action == "change"

    main = settings["main"]
    assert main.method == "POST"
    rules = rules_of(main)
    assert {"deletion", "non_fast_forward", "required_linear_history"} <= set(rules)
    assert rules["pull_request"]["required_approving_review_count"] == 0
    assert rules["pull_request"]["allowed_merge_methods"] == ["squash"]
    checks = rules["required_status_checks"]
    assert checks["strict_required_status_checks_policy"] is False
    assert contexts(checks) == ["gate", "pr-title", "workflows", "pre-commit"]
    assert main.body["bypass_actors"] == [
        ADMIN_PR_BYPASS,
        {"actor_id": 7, "actor_type": "Integration", "bypass_mode": "always"},
    ]

    gates = settings["main-human-gates"]
    gate_rules = rules_of(gates)
    assert gate_rules["required_status_checks"]["strict_required_status_checks_policy"] is True
    assert contexts(gate_rules["required_status_checks"])[-1] == "CodeQL"
    assert "pull_request" not in gate_rules  # solo: no approval
    assert gates.body["bypass_actors"] == [
        ADMIN_PR_BYPASS,
        {"actor_id": 7, "actor_type": "Integration", "bypass_mode": "exempt"},
        {"actor_id": 8, "actor_type": "Integration", "bypass_mode": "exempt"},
    ]
    assert gates.reason == ""

    assert settings["Dependabot alerts"].action == "ok"
    assert settings["Dependabot security updates"].method == "DELETE"
    assert settings["secret_scanning"].action == "ok"
    assert settings["secret_scanning_push_protection"].action == "change"
    assert settings["private vulnerability reporting"].action == "change"
    assert settings[CODEQL_DEFAULT].desired == "not-configured"
    assert settings["sha_pinning_required"].action == "change"
    assert settings["workflow token"].desired["can_approve_pull_request_reviews"] is False
    assert settings["release"].body["reviewers"] == [{"type": "User", "id": 42}]
    assert fake.writes() == []  # planning never writes


def test_private_free_repository_skips_what_the_plan_forbids():
    fake = FakeGh(responses(visibility="private"))
    _, changes = gs.plan(gs.GitHub(fake), REPO, "personal-private", environments=["release"])
    settings = changes_by_setting(changes)
    for name in (
        "main, main-human-gates",
        "release",
        "secret_scanning",
        "private vulnerability reporting",
        "CodeQL",
    ):
        assert settings[name].action == "skip", name
    assert "Pro" in settings["main, main-human-gates"].reason
    assert "Semgrep" in settings["CodeQL"].reason
    assert "has_discussions" not in settings


def test_private_pro_repository_has_environments_without_reviewers_and_no_codeql_check():
    fake = FakeGh(responses(visibility="private", plan="pro"))
    _, changes = gs.plan(
        gs.GitHub(fake), REPO, "personal-private", environments=["production"], reviewer="me"
    )
    settings = changes_by_setting(changes)
    assert settings["main"].action == "change"
    gate_checks = rules_of(settings["main-human-gates"])["required_status_checks"]
    assert "CodeQL" not in contexts(gate_checks)  # Semgrep runs inside gate instead
    assert "reviewers" not in settings["production"].body
    assert "dispatch" in settings["production"].reason


def test_company_profile_requires_a_code_owner_approval_bots_are_exempt_from():
    fake = FakeGh(responses(owner_type="Organization", plan="team"))
    _, changes = gs.plan(gs.GitHub(fake), REPO, "company-oss")
    settings = changes_by_setting(changes)
    assert rules_of(settings["main"])["pull_request"]["required_approving_review_count"] == 0
    approval = rules_of(settings["main-human-gates"])["pull_request"]
    assert approval["required_approving_review_count"] == 1
    assert approval["require_code_owner_review"] is True
    assert "release App" in settings["main"].reason
    assert "--bots-app-id" in settings["main-human-gates"].reason


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
    settings = changes_by_setting(changes)
    ruleset = settings["main"]
    assert ruleset.method == "PUT" and ruleset.endpoint == f"repos/{REPO}/rulesets/9"
    assert ruleset.body["bypass_actors"] == [ADMIN_PR_BYPASS, *existing["bypass_actors"]]
    assert settings["main-human-gates"].method == "POST"


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
    assert ("POST", f"repos/{REPO}/rulesets") in written
    assert ("PUT", f"repos/{REPO}/vulnerability-alerts") not in written  # already enabled
    failed = changes_by_setting(changes)[CODEQL_DEFAULT]
    assert failed.result.startswith("failed (HTTP 403)")


def test_minimal_tier_and_unreadable_immutable_releases():
    fake = FakeGh(responses(overrides={("GET", f"repos/{REPO}/immutable-releases"): (404, None)}))
    _, changes = gs.plan(gs.GitHub(fake), REPO, "personal-oss", tier="minimal")
    settings = changes_by_setting(changes)
    assert settings["CodeQL"].action == "skip"
    assert "CodeQL" not in contexts(
        rules_of(settings["main-human-gates"])["required_status_checks"]
    )
    assert settings["immutable releases"].action == "skip"
    assert "has_discussions" not in settings


def test_main_exit_codes(capsys):
    plan_only = ["--repo", REPO, "--profile", "personal-oss", "--bots-app-id", "8"]
    assert gs.main(plan_only, gh=gs.GitHub(FakeGh(responses()))) == 1
    assert "main-human-gates" in capsys.readouterr().out
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


def test_company_profiles_get_no_admin_bypass():
    fake = FakeGh(responses())
    _, changes = gs.plan(gs.GitHub(fake), REPO, "company-oss", release_app_id=7)
    settings = changes_by_setting(changes)
    assert ADMIN_PR_BYPASS not in settings["main"].body["bypass_actors"]
    assert ADMIN_PR_BYPASS not in settings["main-human-gates"].body["bypass_actors"]


def test_admin_bypass_can_be_turned_off_for_a_personal_profile():
    fake = FakeGh(responses())
    _, changes = gs.plan(gs.GitHub(fake), REPO, "personal-oss", admin_bypass="none")
    assert changes_by_setting(changes)["main"].body["bypass_actors"] == []


def test_admin_bypass_replaces_an_always_bypass_set_by_hand():
    existing = {
        "id": 9,
        "name": "main",
        "enforcement": "active",
        "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
        "rules": [{"type": "deletion"}],
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
    assert changes_by_setting(changes)["main"].body["bypass_actors"] == [ADMIN_PR_BYPASS]
