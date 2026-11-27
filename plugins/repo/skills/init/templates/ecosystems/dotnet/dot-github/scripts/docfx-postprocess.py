#!/usr/bin/env python3
"""Make DocFX's Markdown output safe for Docusaurus.

DocFX writes heading anchors as raw HTML:

    ### <a id="Contoso_Widgets_Widget_Name"></a> Name

Docusaurus wraps every heading in its own anchor, which nests <a> elements,
invalid HTML that the build reports once per heading. Docusaurus has explicit
heading ids for exactly this, so the script rewrites the heading to:

    ### Name {#Contoso_Widgets_Widget_Name}

The id is kept verbatim, so the cross-references DocFX generates between pages
keep resolving.

Usage: python3 .github/scripts/docfx-postprocess.py docs/website/docs/reference/api
"""

import pathlib
import re
import sys

HEADING_ANCHOR = re.compile(
    r'^(?P<hashes>#{1,6}) <a id="(?P<id>[^"]+)"></a>[ ]*(?P<title>.*)$',
    re.MULTILINE,
)


def rewrite(text: str) -> tuple[str, int]:
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        title = match["title"].strip()
        if not title:
            # A heading with no text would render as an empty anchor: leave it.
            return match[0]
        count += 1
        return f'{match["hashes"]} {title} {{#{match["id"]}}}'

    return HEADING_ANCHOR.sub(replace, text), count


def main(directory: str) -> int:
    root = pathlib.Path(directory)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    files = sorted(root.rglob("*.md"))
    if not files:
        print(f"error: no Markdown found under {root}", file=sys.stderr)
        return 1

    total = 0
    for path in files:
        rewritten, count = rewrite(path.read_text(encoding="utf-8"))
        if count:
            path.write_text(rewritten, encoding="utf-8")
            total += count
    print(f"Rewrote {total} heading anchors across {len(files)} files.")

    remaining = sum(
        1
        for path in files
        for match in HEADING_ANCHOR.finditer(path.read_text(encoding="utf-8"))
        if match["title"].strip()
    )
    if remaining:
        print(f"error: {remaining} heading anchors were left unconverted", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/website/docs/reference/api"))
