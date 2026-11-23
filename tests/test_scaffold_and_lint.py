"""Scaffold plugins and skills in a temporary repository, then lint them."""

from __future__ import annotations

import json

import pytest
from helpers import write
from lint_skills import lint
from new_plugin import create_plugin
from new_skill import create_skill


def errors(root):
    return [issue.message for issue in lint(root) if issue.level == "error"]


def test_scaffolded_plugin_and_skill_are_lint_clean(repo):
    create_plugin(repo, "demo", "Demo plugin.", "development", ["demo"])
    create_skill(repo, "demo", "do-things", "Do things. Use when asked to.", ["claude-code", "api"])

    assert errors(repo) == []
    marketplace = json.loads((repo / ".claude-plugin" / "marketplace.json").read_text())
    assert marketplace["plugins"][0]["source"] == "./plugins/demo"
    config = json.loads((repo / "release-please-config.json").read_text())
    assert config["packages"]["plugins/demo"]["initial-version"] == "0.1.0"
    manifest = json.loads((repo / "plugins/demo/.claude-plugin/plugin.json").read_text())
    assert manifest["keywords"] == ["demo"]
    skill_md = (repo / "plugins/demo/skills/do-things/SKILL.md").read_text()
    assert "surfaces: claude-code, api" in skill_md


def test_create_plugin_rejects_invalid_or_duplicate_names(repo):
    with pytest.raises(SystemExit):
        create_plugin(repo, "Bad_Name", "x", "", [])
    create_plugin(repo, "demo", "Demo.", "", [])
    with pytest.raises(SystemExit):
        create_plugin(repo, "demo", "Demo.", "", [])


def test_create_skill_validates_inputs(repo):
    create_plugin(repo, "demo", "Demo.", "", [])
    with pytest.raises(SystemExit):
        create_skill(repo, "missing", "x", "Desc.", ["claude-code"])
    with pytest.raises(SystemExit):
        create_skill(repo, "demo", "x", "Desc.", ["vscode"])
    with pytest.raises(SystemExit):
        create_skill(repo, "demo", "x", "Has <xml>.", ["claude-code"])


def test_unlisted_and_unreleased_plugins_are_errors(repo):
    create_plugin(repo, "demo", "Demo.", "", [])
    write(repo / ".claude-plugin/marketplace.json", json.dumps({"plugins": []}))
    write(repo / "release-please-config.json", json.dumps({"packages": {}}))
    found = errors(repo)
    assert any("not listed" in message for message in found)
    assert any("release-please package" in message for message in found)


def test_marketplace_version_is_an_error(repo):
    create_plugin(repo, "demo", "Demo.", "", [])
    path = repo / ".claude-plugin/marketplace.json"
    data = json.loads(path.read_text())
    data["plugins"][0]["version"] = "1.0.0"
    write(path, json.dumps(data))
    assert any("sets 'version'" in message for message in errors(repo))


def test_skill_rules(repo):
    create_plugin(repo, "demo", "Demo.", "", [])
    skills = repo / "plugins/demo/skills"
    write(skills / "wrong-dir/SKILL.md", "---\nname: other\ndescription: d\n---\n")
    write(skills / "no-desc/SKILL.md", "---\nname: no-desc\n---\n")
    write(skills / "too-long/SKILL.md", "---\nname: too-long\ndescription: d\n---\n" + "x\n" * 600)
    write(skills / "bad-link/SKILL.md", "---\nname: bad-link\ndescription: d\n---\n[a](ref.md)\n")
    write(
        skills / "surf/SKILL.md",
        "---\nname: surf\ndescription: d\nmetadata:\n  surfaces: vscode\n---\n",
    )
    found = errors(repo)
    assert any("must match the folder name" in m for m in found)
    assert any("'description' is required" in m for m in found)
    assert any("lines" in m for m in found)
    assert any("broken relative link 'ref.md'" in m for m in found)
    assert any("unknown surfaces" in m for m in found)


def test_portable_skill_rules(repo):
    create_plugin(repo, "claude", "Demo.", "", [])
    skill = repo / "plugins/claude/skills/tool"
    write(skill / "SKILL.md", "---\nname: tool\ndescription: d\nmetadata:\n  surfaces: api\n---\n")
    write(skill / "scripts/run.js", "console.log(1)\n")
    write(skill / "scripts/run.py", "import requests\nprint('${CLAUDE_PLUGIN_ROOT}')\n")
    write(skill / "templates/ok.js", "// data file: allowed\n")
    found = errors(repo)
    assert any("reserved word 'claude'" in m for m in found)
    assert any("run.js" in m or "runtime not available" in m for m in found)
    assert any("only substituted by Claude Code" in m for m in found)
    assert any("imports 'requests'" in m for m in found)
    assert sum("runtime not available" in m for m in found) == 1


def test_python_stdlib_rule_allows_local_modules_and_exempt_dirs(repo):
    create_plugin(repo, "demo", "Demo.", "", [])
    base = repo / "plugins/demo"
    write(base / "hooks/helper.py", "import json\n")
    write(base / "hooks/main.py", "import helper\nfrom . import helper as h\nimport os.path\n")
    write(base / "servers/mcp/server.py", "import mcp\n")
    write(base / "tests/test_x.py", "import pytest\n")
    assert errors(repo) == []


def test_hooks_rules(repo):
    create_plugin(repo, "demo", "Demo.", "", [])
    hooks = {
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/missing.py"',
                        }
                    ]
                }
            ]
        }
    }
    write(repo / "plugins/demo/hooks/hooks.json", json.dumps(hooks))
    write(repo / "plugins/demo/agents/bad.md", "---\nname: bad\n---\n")
    found = errors(repo)
    assert any("'hooks/missing.py' does not exist" in m for m in found)
    assert any("'description' is required" in m for m in found)


def test_real_repository_is_lint_clean():
    from helpers import REPO_ROOT

    assert errors(REPO_ROOT) == []
