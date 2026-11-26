"""Plan, then apply, the GitHub settings of the repo-init standard, through `gh api`.

Reads the repository's current settings, works out what its visibility and plan
allow, and prints one line per setting: ok, change (current -> desired), or skip
with the reason. Nothing changes without --apply.

Settings:

- merge options: squash only, the pull request title and body as the commit,
  auto-merge allowed, branches deleted after merge, update branch allowed;
- two layered rulesets on the default branch: `main`, for everyone (no
  deletion, no force push, linear history, squash-only pull requests with
  threads resolved, required checks not strict; the release App may bypass),
  and `main-human-gates`, which the bots' App (Renovate's) and the release App
  are exempt from (branches up to date, the `CodeQL` check, and a code owner's
  approval for team profiles);
- workflow token read-only by default; actions must be pinned to a full SHA;
- Dependabot alerts on, Dependabot security updates off (Renovate opens them);
- secret scanning and push protection, private vulnerability reporting,
  immutable releases, Discussions, where allowed; CodeQL default setup off,
  because the `codeql.yml` workflow runs advanced setup;
- environments (`release`, `preview`, `staging`, `production`) limited to the
  default branch, with required reviewers where the plan has them.

Standard library only; needs an authenticated `gh` with admin rights on the
repository.

Usage:
    python3 scripts/github_settings.py --repo OWNER/NAME --profile PROFILE
        [--tier minimal|standard|complete] [--environment NAME ...]
        [--reviewer LOGIN] [--release-app-id ID] [--bots-app-id ID]
        [--check NAME ...] [--code-security] [--apply] [--json]

Exit codes: 0 nothing to change or everything applied, 1 changes pending (plan
only) or some changes failed, 2 the repository cannot be read.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass

PROFILES = ("personal-oss", "personal-private", "company-private", "company-oss")
TIERS = ("minimal", "standard", "complete")
DEFAULT_CHECKS = ("gate", "pr-title", "workflows", "pre-commit")
RULESET_NAME = "main"
HUMAN_GATES_NAME = "main-human-gates"
TIMEOUT = 60

Runner = Callable[[list[str], str | None], tuple[int, str, str]]


@dataclass
class Response:
    status: int
    data: object


@dataclass
class Change:
    area: str
    setting: str
    current: object
    desired: object
    action: str  # ok, change, skip
    reason: str = ""
    method: str = ""
    endpoint: str = ""
    body: object = None
    result: str = ""


def run_gh(args: list[str], stdin: str | None) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["gh", *args], input=stdin, capture_output=True, text=True, timeout=TIMEOUT
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout, completed.stderr


class GitHub:
    """A thin `gh api --include` client that never raises on HTTP errors."""

    def __init__(self, runner: Runner = run_gh) -> None:
        self.runner = runner

    def call(self, method: str, endpoint: str, body: object = None) -> Response:
        args = ["api", "--include", "--method", method, endpoint]
        stdin = None
        if body is not None:
            args += ["--input", "-"]
            stdin = json.dumps(body)
        code, out, err = self.runner(args, stdin)
        status = 0
        head, _, payload = out.replace("\r\n", "\n").partition("\n\n")
        match = re.match(r"HTTP/[\d.]+ (\d{3})", head)
        if match:
            status = int(match[1])
        else:
            payload = out
            found = re.search(r"HTTP (\d{3})", err)
            status = int(found[1]) if found else (200 if code == 0 else 0)
        try:
            data = json.loads(payload) if payload.strip() else None
        except json.JSONDecodeError:
            data = payload
        return Response(status, data)

    def get(self, endpoint: str) -> Response:
        return self.call("GET", endpoint)


def capabilities(visibility: str, owner_type: str, plan: str | None, code_security: bool) -> dict:
    """What the plan allows for this visibility (references/github-plans.md)."""
    public = visibility == "public"
    plan_name = (plan or "").lower()
    enterprise = "enterprise" in plan_name
    free_personal = owner_type == "User" and plan_name == "free"
    return {
        "rulesets": public or not free_personal,
        "environments": public or not free_personal,
        "environment_reviewers": public or enterprise,
        "secret_scanning": public or code_security,
        "codeql": public or code_security,
        "private_vulnerability_reporting": public,
        "discussions": True,
    }


def _compare(
    area: str, setting: str, current: object, desired: object, **request: object
) -> Change:
    action = "ok" if current == desired else "change"
    return Change(area, setting, current, desired, action, **request)  # type: ignore[arg-type]


def _skip(area: str, setting: str, reason: str, desired: object = None) -> Change:
    return Change(area, setting, None, desired, "skip", reason)


def _bypass(release_app_id: int | None, bots_app_id: int | None, mode: str) -> list[dict]:
    actors = []
    if release_app_id:
        actors.append(
            {"actor_id": release_app_id, "actor_type": "Integration", "bypass_mode": mode}
        )
    if bots_app_id and mode == "exempt":
        actors.append({"actor_id": bots_app_id, "actor_type": "Integration", "bypass_mode": mode})
    return actors


def _checks_rule(checks: list[str], strict: bool) -> dict:
    return {
        "type": "required_status_checks",
        "parameters": {
            "strict_required_status_checks_policy": strict,
            "do_not_enforce_on_create": False,
            "required_status_checks": [{"context": c} for c in checks],
        },
    }


def _target() -> dict:
    return {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}


def ruleset_body(checks: list[str], release_app_id: int | None) -> dict:
    """`main`, for everyone: what bots and people alike must respect."""
    return {
        "name": RULESET_NAME,
        "target": "branch",
        "enforcement": "active",
        "conditions": _target(),
        # The release App pushes the changelog commit and the tag.
        "bypass_actors": _bypass(release_app_id, None, "always"),
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "dismiss_stale_reviews_on_push": True,
                    "require_code_owner_review": False,
                    "require_last_push_approval": False,
                    "required_review_thread_resolution": True,
                    "allowed_merge_methods": ["squash"],
                },
            },
            _checks_rule(checks, strict=False),
        ],
    }


def human_gates_body(
    profile: str,
    checks: list[str],
    code_scanning: bool,
    release_app_id: int | None,
    bots_app_id: int | None,
) -> dict:
    """`main-human-gates`: the bars people meet and the bots' App is exempt from.

    Branches up to date (Dependabot never rebases a branch that is only behind;
    Renovate need not when it is exempt), the code scanning check, and, for
    teams, a code owner's approval (a bot cannot approve, and no workflow has
    to approve for it).
    """
    team = profile.startswith("company")
    rules = [_checks_rule(checks + (["CodeQL"] if code_scanning else []), strict=True)]
    if team:
        rules.append(
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "dismiss_stale_reviews_on_push": True,
                    "require_code_owner_review": True,
                    "require_last_push_approval": False,
                    "required_review_thread_resolution": True,
                    "allowed_merge_methods": ["squash"],
                },
            }
        )
    return {
        "name": HUMAN_GATES_NAME,
        "target": "branch",
        "enforcement": "active",
        "conditions": _target(),
        "bypass_actors": _bypass(release_app_id, bots_app_id, "exempt"),
        "rules": rules,
    }


def _ruleset_summary(ruleset: dict | None) -> dict | None:
    """The parts of a ruleset this script manages, for comparison."""
    if not ruleset:
        return None
    rules = {rule["type"]: rule.get("parameters") for rule in ruleset.get("rules", [])}
    pull_request = rules.get("pull_request") or {}
    checks = rules.get("required_status_checks") or {}
    return {
        "enforcement": ruleset.get("enforcement"),
        "rules": sorted(rules),
        "approvals": pull_request.get("required_approving_review_count"),
        "code_owners": pull_request.get("require_code_owner_review"),
        "merge_methods": pull_request.get("allowed_merge_methods"),
        "strict": checks.get("strict_required_status_checks_policy"),
        "checks": sorted(c["context"] for c in checks.get("required_status_checks", [])),
        "bypass": sorted(
            f"{a.get('actor_id')}:{a.get('bypass_mode')}"
            for a in ruleset.get("bypass_actors") or []
        ),
    }


def _ruleset_change(endpoint: str, body: dict, existing: dict | None) -> Change:
    """Create or update one ruleset; keep bypass actors set by hand when none are given."""
    current = _ruleset_summary(existing)
    if existing and not body["bypass_actors"]:
        body["bypass_actors"] = existing.get("bypass_actors") or []
    desired = _ruleset_summary(body)
    if existing:
        return _compare(
            "ruleset",
            body["name"],
            current,
            desired,
            method="PUT",
            endpoint=f"{endpoint}/rulesets/{existing['id']}",
            body=body,
        )
    return Change(
        "ruleset",
        body["name"],
        None,
        desired,
        "change",
        method="POST",
        endpoint=f"{endpoint}/rulesets",
        body=body,
    )


def plan(
    gh: GitHub,
    repo: str,
    profile: str,
    tier: str = "standard",
    environments: list[str] | None = None,
    reviewer: str | None = None,
    release_app_id: int | None = None,
    checks: list[str] | None = None,
    code_security: bool = False,
    bots_app_id: int | None = None,
) -> tuple[dict, list[Change]]:
    response = gh.get(f"repos/{repo}")
    if response.status != 200 or not isinstance(response.data, dict):
        raise RuntimeError(
            f"cannot read repos/{repo} (HTTP {response.status}): is gh authenticated?"
        )
    info = response.data
    owner = info.get("owner", {})
    owner_type = owner.get("type", "User")
    plan_name = None
    plan_endpoint = "user" if owner_type == "User" else f"orgs/{owner.get('login')}"
    plan_response = gh.get(plan_endpoint)
    readable = plan_response.status == 200 and isinstance(plan_response.data, dict)
    if readable and (owner_type != "User" or plan_response.data.get("login") == owner.get("login")):
        plan_name = (plan_response.data.get("plan") or {}).get("name")
    can = capabilities(info.get("visibility", "private"), owner_type, plan_name, code_security)
    context = {
        "repo": repo,
        "visibility": info.get("visibility"),
        "owner_type": owner_type,
        "plan": plan_name,
        "admin": (info.get("permissions") or {}).get("admin"),
        "capabilities": can,
    }
    oss = profile.endswith("oss")
    changes: list[Change] = []
    endpoint = f"repos/{repo}"

    # Merge options.
    merge = {
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": False,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
        "allow_auto_merge": True,
        "delete_branch_on_merge": True,
        "allow_update_branch": True,
    }
    for key, desired in merge.items():
        changes.append(
            _compare(
                "merge",
                key,
                info.get(key),
                desired,
                method="PATCH",
                endpoint=endpoint,
                body={key: desired},
            )
        )
    if oss and tier != "minimal":
        changes.append(
            _compare(
                "community",
                "has_discussions",
                info.get("has_discussions"),
                True,
                method="PATCH",
                endpoint=endpoint,
                body={"has_discussions": True},
            )
        )

    # Rulesets on the default branch.
    if can["rulesets"]:
        listed = gh.get(f"{endpoint}/rulesets")
        existing_by_name: dict[str, dict] = {}
        if listed.status == 200 and isinstance(listed.data, list):
            for item in listed.data:
                if item.get("name") in {RULESET_NAME, HUMAN_GATES_NAME}:
                    detail = gh.get(f"{endpoint}/rulesets/{item['id']}")
                    if isinstance(detail.data, dict):
                        existing_by_name[item["name"]] = detail.data
        required = checks or list(DEFAULT_CHECKS)
        code_scanning = tier != "minimal" and can["codeql"]
        bodies = [
            ruleset_body(required, release_app_id),
            human_gates_body(profile, required, code_scanning, release_app_id, bots_app_id),
        ]
        for body in bodies:
            changes.append(_ruleset_change(endpoint, body, existing_by_name.get(body["name"])))
        if not release_app_id:
            changes[-2].reason = "no release App on the bypass list: pass --release-app-id"
        if not bots_app_id:
            changes[-1].reason = (
                "the bots' App is not exempt: pass --bots-app-id (the Renovate App), or its "
                "pull requests wait for an up-to-date branch and a person's review"
            )
    else:
        changes.append(
            _skip(
                "ruleset",
                f"{RULESET_NAME}, {HUMAN_GATES_NAME}",
                "rulesets on private repositories need Pro, Team or Enterprise",
            )
        )

    # Actions: read-only token, SHA pinning.
    workflow = gh.get(f"{endpoint}/actions/permissions/workflow")
    if workflow.status == 200 and isinstance(workflow.data, dict):
        desired_workflow = {
            "default_workflow_permissions": "read",
            # No workflow approves pull requests: bots are exempt from the
            # approval of main-human-gates instead.
            "can_approve_pull_request_reviews": False,
        }
        current_workflow = {k: workflow.data.get(k) for k in desired_workflow}
        changes.append(
            _compare(
                "actions",
                "workflow token",
                current_workflow,
                desired_workflow,
                method="PUT",
                endpoint=f"{endpoint}/actions/permissions/workflow",
                body=desired_workflow,
            )
        )
    actions = gh.get(f"{endpoint}/actions/permissions")
    if actions.status == 200 and isinstance(actions.data, dict):
        current_pinning = actions.data.get("sha_pinning_required")
        body = {
            "enabled": True,
            "allowed_actions": actions.data.get("allowed_actions") or "all",
            "sha_pinning_required": True,
        }
        changes.append(
            _compare(
                "actions",
                "sha_pinning_required",
                current_pinning,
                True,
                method="PUT",
                endpoint=f"{endpoint}/actions/permissions",
                body=body,
            )
        )

    # Dependabot: alerts on, security updates off (Renovate opens them).
    alerts = gh.get(f"{endpoint}/vulnerability-alerts")
    changes.append(
        _compare(
            "dependencies",
            "Dependabot alerts",
            alerts.status == 204,
            True,
            method="PUT",
            endpoint=f"{endpoint}/vulnerability-alerts",
        )
    )
    fixes = gh.get(f"{endpoint}/automated-security-fixes")
    enabled = isinstance(fixes.data, dict) and bool(fixes.data.get("enabled"))
    changes.append(
        _compare(
            "dependencies",
            "Dependabot security updates",
            enabled,
            False,
            method="DELETE",
            endpoint=f"{endpoint}/automated-security-fixes",
            reason="Renovate opens vulnerability pull requests from the alerts",
        )
    )

    # Security.
    analysis = info.get("security_and_analysis") or {}
    for key in ("secret_scanning", "secret_scanning_push_protection"):
        if can["secret_scanning"]:
            current_state = (analysis.get(key) or {}).get("status")
            changes.append(
                _compare(
                    "security",
                    key,
                    current_state,
                    "enabled",
                    method="PATCH",
                    endpoint=endpoint,
                    body={"security_and_analysis": {key: {"status": "enabled"}}},
                )
            )
        else:
            changes.append(
                _skip("security", key, "needs a public repository or GitHub Secret Protection")
            )
    if can["private_vulnerability_reporting"]:
        reporting = gh.get(f"{endpoint}/private-vulnerability-reporting")
        current_reporting = isinstance(reporting.data, dict) and reporting.data.get("enabled")
        changes.append(
            _compare(
                "security",
                "private vulnerability reporting",
                bool(current_reporting),
                True,
                method="PUT",
                endpoint=f"{endpoint}/private-vulnerability-reporting",
            )
        )
    else:
        changes.append(
            _skip("security", "private vulnerability reporting", "public repositories only")
        )
    immutable = gh.get(f"{endpoint}/immutable-releases")
    if immutable.status == 200 and isinstance(immutable.data, dict):
        changes.append(
            _compare(
                "security",
                "immutable releases",
                bool(immutable.data.get("enabled")),
                True,
                method="PUT",
                endpoint=f"{endpoint}/immutable-releases",
            )
        )
    else:
        changes.append(
            _skip(
                "security",
                "immutable releases",
                f"not readable through the API (HTTP {immutable.status}): "
                "enable it in Settings, General",
            )
        )
    if tier == "minimal":
        changes.append(_skip("security", "CodeQL", "standard tier and up"))
    elif can["codeql"]:
        # codeql.yml runs advanced setup, whose `CodeQL` check main-human-gates
        # requires; default setup would refuse its uploads, so it stays off.
        codeql = gh.get(f"{endpoint}/code-scanning/default-setup")
        state = codeql.data.get("state") if isinstance(codeql.data, dict) else None
        changes.append(
            _compare(
                "security",
                "CodeQL default setup (off: codeql.yml runs advanced setup)",
                state,
                "not-configured",
                method="PATCH",
                endpoint=f"{endpoint}/code-scanning/default-setup",
                body={"state": "not-configured"},
            )
        )
    else:
        changes.append(
            _skip(
                "security",
                "CodeQL",
                "needs a public repository or GitHub Code Security: Semgrep runs in ci.yml",
            )
        )

    # Environments.
    for name in environments or []:
        if not can["environments"]:
            changes.append(
                _skip(
                    "environments",
                    name,
                    "environments on private repositories need Pro, Team or Enterprise",
                )
            )
            continue
        changes.extend(
            _environment_changes(gh, endpoint, name, reviewer, can["environment_reviewers"])
        )
    return context, changes


def _environment_changes(
    gh: GitHub, endpoint: str, name: str, reviewer: str | None, reviewers_allowed: bool
) -> list[Change]:
    wants_reviewer = name in {"release", "production"}
    body: dict = {
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}
    }
    reason = ""
    if wants_reviewer and reviewer and reviewers_allowed:
        user = gh.get(f"users/{reviewer}")
        if user.status == 200 and isinstance(user.data, dict):
            body["reviewers"] = [{"type": "User", "id": user.data["id"]}]
            body["prevent_self_review"] = False
    elif wants_reviewer and not reviewers_allowed:
        reason = "no required reviewers on this plan: the manual dispatch is the gate"
    elif wants_reviewer:
        reason = "pass --reviewer to require an approval"
    current = gh.get(f"{endpoint}/environments/{name}")
    exists = current.status == 200
    summary = None
    if exists and isinstance(current.data, dict):
        rules = current.data.get("protection_rules") or []
        reviewers = [
            r["reviewer"]["login"]
            for rule in rules
            if rule.get("type") == "required_reviewers"
            for r in rule.get("reviewers", [])
            if r.get("reviewer", {}).get("login")
        ]
        policy = current.data.get("deployment_branch_policy") or {}
        summary = {
            "reviewers": sorted(reviewers),
            "custom_branches": bool(policy.get("custom_branch_policies")),
        }
    desired = {
        "reviewers": [reviewer] if "reviewers" in body else (summary or {}).get("reviewers", []),
        "custom_branches": True,
    }
    changes = [
        _compare(
            "environments",
            name,
            summary,
            desired,
            method="PUT",
            endpoint=f"{endpoint}/environments/{name}",
            body=body,
            reason=reason,
        )
    ]
    policies = (
        gh.get(f"{endpoint}/environments/{name}/deployment-branch-policies") if exists else None
    )
    names = []
    if policies and isinstance(policies.data, dict):
        names = [p.get("name") for p in policies.data.get("branch_policies", [])]
    changes.append(
        _compare(
            "environments",
            f"{name}: deployment branch",
            "main" in names,
            True,
            method="POST",
            endpoint=f"{endpoint}/environments/{name}/deployment-branch-policies",
            body={"name": "main", "type": "branch"},
        )
    )
    return changes


def apply(gh: GitHub, changes: list[Change]) -> bool:
    ok = True
    for change in changes:
        if change.action != "change":
            continue
        response = gh.call(change.method, change.endpoint, change.body)
        if 200 <= response.status < 300:
            change.result = "applied"
        else:
            ok = False
            message = (
                response.data.get("message") if isinstance(response.data, dict) else response.data
            )
            change.result = f"failed (HTTP {response.status}): {message}"
    return ok


def format_plan(context: dict, changes: list[Change]) -> str:
    lines = [
        f"{context['repo']}: {context['visibility']}, owner {context['owner_type']}, "
        f"plan {context['plan'] or 'unknown'}, admin {context['admin']}",
        "",
    ]
    for change in changes:
        if change.action == "ok":
            line = f"  ok      {change.area}: {change.setting}"
        elif change.action == "skip":
            line = f"  skip    {change.area}: {change.setting} ({change.reason})"
        else:
            line = (
                f"  change  {change.area}: {change.setting}: "
                f"{change.current!r} -> {change.desired!r}"
            )
            if change.reason:
                line += f"\n          note: {change.reason}"
        if change.result:
            line += f"\n          {change.result}"
        lines.append(line)
    pending = sum(1 for c in changes if c.action == "change")
    lines += [
        "",
        f"{pending} change(s)"
        + ("" if any(c.result for c in changes) else ", run again with --apply to make them"),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None, gh: GitHub | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan and apply repository settings.")
    parser.add_argument("--repo", required=True, help="OWNER/NAME")
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--tier", default="standard", choices=TIERS)
    parser.add_argument("--environment", action="append", default=[], help="environment to create")
    parser.add_argument("--reviewer", help="login required to approve release and production")
    parser.add_argument(
        "--release-app-id", type=int, help="the release GitHub App's ID, for the bypass list"
    )
    parser.add_argument(
        "--bots-app-id",
        type=int,
        help="the Renovate App's ID, exempt from main-human-gates",
    )
    parser.add_argument(
        "--check", action="append", help="required check (default: the four of the standard)"
    )
    parser.add_argument(
        "--code-security", action="store_true", help="the private repository has the add-ons"
    )
    parser.add_argument("--apply", action="store_true", help="make the changes")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    gh = gh or GitHub()
    try:
        context, changes = plan(
            gh,
            args.repo,
            args.profile,
            args.tier,
            args.environment,
            args.reviewer,
            args.release_app_id,
            args.check,
            args.code_security,
            args.bots_app_id,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    ok = apply(gh, changes) if args.apply else True
    if args.json:
        print(
            json.dumps(
                {"context": context, "changes": [asdict(c) for c in changes]}, indent=2, default=str
            )
        )
    else:
        print(format_plan(context, changes))
    if args.apply:
        return 0 if ok else 1
    return 1 if any(c.action == "change" for c in changes) else 0


if __name__ == "__main__":
    sys.exit(main())
