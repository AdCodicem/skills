from __future__ import annotations

import pytest
from skills_lib import (
    FrontmatterError,
    package_name,
    parse_frontmatter,
    parse_surfaces,
    render_frontmatter,
)


def test_parse_frontmatter_splits_header_and_body():
    data, body = parse_frontmatter("---\nname: demo\ndescription: Does things.\n---\n# Title\n")
    assert data == {"name": "demo", "description": "Does things."}
    assert body == "# Title\n"


@pytest.mark.parametrize("text", ["# No frontmatter", "---\n: [broken\n---\n", "---\n- a\n---\n"])
def test_parse_frontmatter_rejects_invalid_input(text):
    with pytest.raises(FrontmatterError):
        parse_frontmatter(text)


def test_render_frontmatter_round_trips():
    text = render_frontmatter({"name": "demo", "description": 'Say "hi": now'}, "Body\n")
    assert parse_frontmatter(text) == ({"name": "demo", "description": 'Say "hi": now'}, "Body\n")


@pytest.mark.parametrize(
    ("plugin", "skill", "expected"),
    [
        ("dotnet", "repo-init", "dotnet-repo-init"),
        ("dotnet", "dotnet-format", "dotnet-format"),
        ("github", "github", "github"),
    ],
)
def test_package_name(plugin, skill, expected):
    assert package_name(plugin, skill) == expected


@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [
        ({}, {"claude-code"}),
        ({"metadata": {"surfaces": "claude-code, claude-ai"}}, {"claude-code", "claude-ai"}),
        ({"metadata": {"surfaces": "api claude-ai"}}, {"api", "claude-ai"}),
        ({"metadata": {"surfaces": ["api"]}}, {"api"}),
    ],
)
def test_parse_surfaces(frontmatter, expected):
    assert parse_surfaces(frontmatter) == expected
