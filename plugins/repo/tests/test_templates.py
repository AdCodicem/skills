"""Structural checks of the repo-init templates: every file parses, every workflow
and fragment follows the security rules of references/areas/ci.md, and the
fragments assemble into valid workflows.

actionlint and zizmor run on assembled repositories when the skill is changed
(see the pull request that added this file); these checks hold the rules that
can be verified without them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

TEMPLATES = Path(__file__).resolve().parents[1] / "skills" / "init" / "templates"
PLACEHOLDER = re.compile(r"(?<![${])\{\{([a-z][a-z0-9-]*)\}\}")
MODULE_PREFIXES = {
    "ecosystems/dotnet": "dotnet-",
    "ecosystems/node": "node-",
    "ecosystems/react": "react-",
    "ecosystems/python": "python-",
    "iac/bicep": "bicep-",
    "iac/pulumi": "pulumi-",
    "iac/cloudflare": "wrangler-",
}


def fill(text: str) -> str:
    return PLACEHOLDER.sub(lambda m: "x" if "dir" not in m[1] else "infra", text)


def load(path: Path):
    return yaml.safe_load(fill(path.read_text(encoding="utf-8")))


YAML_FILES = sorted(p for p in TEMPLATES.rglob("*") if p.suffix in {".yml", ".yaml"})
JSON_FILES = sorted(p for p in TEMPLATES.rglob("*.json"))
WORKFLOW_FILES = [p for p in YAML_FILES if "workflows" in p.parts or p.parent.name == "deploy"] + [
    p for p in YAML_FILES if p.name in {"ci-jobs.yml", "deploy.yml", "container.yml", "staging.yml"}
]
WORKFLOW_FILES = sorted(set(WORKFLOW_FILES))
STEP_FILES = sorted(
    p
    for p in YAML_FILES
    if p.name in {"release-pack.yml", "release-publish.yml", "docs-api.yml"}
    or "toolchains" in p.parts
)


def rel(path: Path) -> str:
    return path.relative_to(TEMPLATES).as_posix()


def jobs_of(data) -> dict:
    return (data or {}).get("jobs") or {}


def steps_of(data) -> list:
    if isinstance(data, dict) and "steps" in data:
        return data["steps"] or []
    return data if isinstance(data, list) else []


def all_steps(path: Path) -> list[dict]:
    data = load(path)
    steps = [s for job in jobs_of(data).values() for s in job.get("steps") or []]
    return steps + steps_of(data)


@pytest.mark.parametrize("path", YAML_FILES, ids=rel)
def test_yaml_templates_parse(path):
    load(path)


@pytest.mark.parametrize("path", JSON_FILES, ids=rel)
def test_json_templates_parse(path):
    json.loads(fill(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", YAML_FILES, ids=rel)
def test_no_pull_request_target(path):
    assert "pull_request_target" not in yaml.safe_dump(load(path))


@pytest.mark.parametrize("path", WORKFLOW_FILES, ids=rel)
def test_jobs_declare_permissions_and_timeouts(path):
    data = load(path)
    if isinstance(data, dict) and (True in data or "on" in data):
        assert "permissions" in data, "a workflow sets top-level permissions"
    for name, job in jobs_of(data).items():
        assert "permissions" in job, f"{name}: job-level permissions"
        if "uses" not in job:  # a reusable workflow call takes no timeout
            assert "timeout-minutes" in job, f"{name}: timeout-minutes"


@pytest.mark.parametrize("path", WORKFLOW_FILES + STEP_FILES, ids=rel)
def test_actions_are_named_by_version_and_checkouts_keep_no_credentials(path):
    for step in all_steps(path):
        uses = step.get("uses")
        if not uses or uses.startswith(("./", "$/", "docker://")):
            continue
        ref = uses.rpartition("@")[2]
        assert re.match(r"^v\d+(\.\d+){0,2}$", ref), f"{uses}: a version tag, pinned at generation"
        if uses.startswith("actions/checkout@"):
            with_ = step.get("with") or {}
            assert with_.get("persist-credentials") is False, (
                f"{rel(path)}: persist-credentials: false"
            )


PUBLISHING = [
    TEMPLATES / "release/dot-github/workflows/release.yml",
    TEMPLATES / "release/dot-github/workflows/preview.yml",
    TEMPLATES / "release/dot-github/workflows/docs.yml",
    *sorted(TEMPLATES.glob("deploy/*/deploy.yml")),
    *sorted(TEMPLATES.glob("iac/*/deploy.yml")),
    *sorted(TEMPLATES.glob("ecosystems/*/release-*.yml")),
]


@pytest.mark.parametrize("path", PUBLISHING, ids=rel)
def test_no_cache_where_something_is_published(path):
    for step in all_steps(path):
        with_ = step.get("with") or {}
        uses = step.get("uses") or ""
        assert "cache" not in with_ or with_["cache"] in ("", False), f"{uses}: cache"
        assert with_.get("enable-cache") in (None, False), f"{uses}: enable-cache"
        if uses.startswith("actions/setup-node@"):
            assert with_.get("package-manager-cache") is False, (
                f"{rel(path)}: package-manager-cache"
            )


@pytest.mark.parametrize(("folder", "prefix"), sorted(MODULE_PREFIXES.items()))
def test_module_ci_jobs_are_prefixed(folder, prefix):
    jobs = jobs_of(load(TEMPLATES / folder / "ci-jobs.yml"))
    assert jobs
    assert all(name.startswith(prefix) for name in jobs), sorted(jobs)


def test_fragments_assemble_into_one_ci_workflow():
    ci = load(TEMPLATES / "core/dot-github/workflows/ci.yml")
    gate = ci["jobs"].pop("gate")
    for folder in MODULE_PREFIXES:
        jobs = jobs_of(load(TEMPLATES / folder / "ci-jobs.yml"))
        assert not set(jobs) & set(ci["jobs"]), f"{folder}: job ids collide"
        ci["jobs"].update(jobs)
    gate["needs"] = list(ci["jobs"])
    for job in ci["jobs"].values():
        needs = job.get("needs") or []
        for need in [needs] if isinstance(needs, str) else needs:
            assert need in ci["jobs"], f"unknown need {need}"
    assert gate["if"] == "always()"
    assert "success" in gate["steps"][0]["run"]


def test_release_workflows_have_the_fragment_slots_and_isolation():
    release = load(TEMPLATES / "release/dot-github/workflows/release.yml")
    jobs = release["jobs"]
    assert list(jobs) == ["plan", "verify", "pack", "publish"]
    assert jobs["publish"]["environment"] == "release"
    assert jobs["pack"]["permissions"] == {"contents": "read"}
    assert "id-token" not in jobs["pack"]["permissions"]
    assert {"VERSION", "LAST_VERSION"} <= set(jobs["pack"]["env"])
    preview = load(TEMPLATES / "release/dot-github/workflows/preview.yml")
    assert preview["jobs"]["publish"]["environment"] == "preview"
    releaserc = json.loads((TEMPLATES / "release/dot-releaserc.json").read_text(encoding="utf-8"))
    analyzer = dict(p for p in releaserc["plugins"] if isinstance(p, list))[
        "@semantic-release/commit-analyzer"
    ]
    assert analyzer["releaseRules"][0] == {"breaking": True, "release": "minor"}
    github = dict(p for p in releaserc["plugins"] if isinstance(p, list))[
        "@semantic-release/github"
    ]
    assert github["draftRelease"] is True


def test_dotfiles_use_the_dot_prefix():
    hidden = [rel(p) for p in TEMPLATES.rglob("*") if p.name.startswith(".")]
    assert hidden == []
