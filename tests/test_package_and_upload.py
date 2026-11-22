from __future__ import annotations

import json
import zipfile

import pytest
from helpers import write
from new_plugin import create_plugin
from new_skill import create_skill
from package_skills import package, select_plugins
from skills_lib import parse_frontmatter
from upload_skills import SkillsClient, encode_multipart, upload


@pytest.fixture
def built(repo, tmp_path):
    create_plugin(repo, "demo", "Demo.", "", [])
    create_skill(repo, "demo", "portable", "Portable skill.", ["claude-code", "claude-ai", "api"])
    create_skill(repo, "demo", "web-only", "claude.ai only.", ["claude-code", "claude-ai"])
    create_skill(repo, "demo", "local", "Claude Code only.", ["claude-code"])
    skill = repo / "plugins/demo/skills/portable"
    write(skill / "scripts/run.py", "print('hi')\n")
    write(skill / "tests/test_run.py", "def test(): pass\n")
    write(skill / "scripts/__pycache__/run.cpython-311.pyc", "x")
    out = tmp_path / "dist"
    return package(select_plugins(repo, [], include_examples=False), out), out


def test_package_builds_only_portable_skills(built):
    items, out = built
    assert [i["package"] for i in items] == ["demo-portable", "demo-web-only"]
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["skills"] == items


def test_package_layout_and_frontmatter(built):
    _, out = built
    with zipfile.ZipFile(out / "demo-portable.zip") as archive:
        names = archive.namelist()
        skill_md = archive.read("demo-portable/SKILL.md").decode()
    assert names == ["demo-portable/SKILL.md", "demo-portable/scripts/run.py"]
    frontmatter, body = parse_frontmatter(skill_md)
    assert frontmatter == {"name": "demo-portable", "description": "Portable skill."}
    assert body.lstrip().startswith("# Portable")


def test_package_is_reproducible(repo, tmp_path):
    create_plugin(repo, "demo", "Demo.", "", [])
    create_skill(repo, "demo", "portable", "Portable.", ["api"])
    plugins = select_plugins(repo, [], include_examples=False)
    package(plugins, tmp_path / "a")
    package(plugins, tmp_path / "b")
    first = (tmp_path / "a/demo-portable.zip").read_bytes()
    assert first == (tmp_path / "b/demo-portable.zip").read_bytes()


def test_select_plugins_rejects_unknown_names(repo):
    with pytest.raises(SystemExit):
        select_plugins(repo, ["nope"], include_examples=False)


def test_encode_multipart_contains_fields_and_file():
    body, content_type = encode_multipart({"display_name": "x"}, [("files[]", "x.zip", b"PK")])
    boundary = content_type.split("boundary=")[1]
    assert body.startswith(f"--{boundary}\r\n".encode())
    assert b'name="display_name"\r\n\r\nx\r\n' in body
    assert b'name="files[]"; filename="x.zip"' in body
    assert body.endswith(f"--{boundary}--\r\n".encode())


class FakeApi:
    def __init__(self, existing):
        self.existing = existing
        self.calls = []

    def __call__(self, method, url, body, headers):
        self.calls.append((method, url))
        assert headers["x-api-key"] == "key"
        assert headers["anthropic-version"]
        if method == "GET":
            return {"data": self.existing}
        return {"id": "skver_new" if url.endswith("/versions") else "skill_new"}


def test_upload_creates_or_versions_api_skills_only(built):
    _, out = built
    api = FakeApi([{"id": "skill_1", "display_name": "demo-portable"}])
    log = upload(out, SkillsClient("key", requester=api))
    assert api.calls[1] == ("POST", "https://api.anthropic.com/v1/skills/skill_1/versions")
    assert len(api.calls) == 2  # web-only is never uploaded
    assert "new version" in log[0]

    api = FakeApi([])
    upload(out, SkillsClient("key", requester=api))
    assert api.calls[1] == ("POST", "https://api.anthropic.com/v1/skills")


def test_upload_refuses_ambiguous_names(built):
    _, out = built
    duplicates = [
        {"id": "a", "display_name": "demo-portable"},
        {"id": "b", "display_name": "demo-portable"},
    ]
    with pytest.raises(SystemExit):
        upload(out, SkillsClient("key", requester=FakeApi(duplicates)))


def test_upload_dry_run_makes_no_call(built):
    _, out = built
    assert upload(out, None, dry_run=True) == [
        "[dry-run] would create 'demo-portable' from demo-portable.zip"
    ]
