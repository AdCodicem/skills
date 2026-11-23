"""Upload packaged skills to the Claude API (`/v1/skills`).

Reads `<dist>/manifest.json` written by package_skills.py and uploads every
skill whose surfaces include `api`. A skill is matched to an existing custom
skill of the workspace by its display name (the package name): a match gets a
new version, otherwise the skill is created. Skills that only target claude.ai
are skipped: claude.ai has no upload API, so they are attached to the GitHub
release for a manual upload.

Requires the ANTHROPIC_API_KEY environment variable. Uploading does not run a
model, so it consumes no tokens.

Usage: python scripts/upload_skills.py [--dist dist] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from collections.abc import Callable
from pathlib import Path

from skills_lib import REPO_ROOT, load_json

API_URL = "https://api.anthropic.com/v1/skills"
API_VERSION = "2026-10-21"
#: Page size for listing skills. One page is enough for a personal workspace.
LIST_LIMIT = 1000

Requester = Callable[[str, str, bytes | None, dict[str, str]], dict]


def encode_multipart(
    fields: dict[str, str], files: list[tuple[str, str, bytes]]
) -> tuple[bytes, str]:
    """Encode form fields and (field, filename, content) files as multipart/form-data."""
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for name, value in fields.items():
        header = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
        parts.append(f"{header}{value}\r\n".encode())
    for field, filename, content in files:
        header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            "Content-Type: application/zip\r\n\r\n"
        )
        parts.append(header.encode() + content + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def http_request(method: str, url: str, body: bytes | None, headers: dict[str, str]) -> dict:
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} failed with HTTP {exc.code}: {detail}") from exc


class SkillsClient:
    def __init__(self, api_key: str, requester: Requester = http_request) -> None:
        self._headers = {"x-api-key": api_key, "anthropic-version": API_VERSION}
        self._request = requester

    def list_custom(self) -> list[dict]:
        url = f"{API_URL}?source=custom&limit={LIST_LIMIT}"
        return self._request("GET", url, None, dict(self._headers)).get("data", [])

    def _post_zip(self, url: str, zip_path: Path, fields: dict[str, str]) -> dict:
        body, content_type = encode_multipart(
            fields, [("files[]", zip_path.name, zip_path.read_bytes())]
        )
        headers = {**self._headers, "content-type": content_type}
        return self._request("POST", url, body, headers)

    def create(self, display_name: str, zip_path: Path) -> dict:
        return self._post_zip(API_URL, zip_path, {"display_name": display_name})

    def create_version(self, skill_id: str, zip_path: Path) -> dict:
        return self._post_zip(f"{API_URL}/{skill_id}/versions", zip_path, {})


def upload(dist: Path, client: SkillsClient | None, dry_run: bool = False) -> list[str]:
    """Upload API-targeted skills and return one log line per skill."""
    manifest = load_json(dist / "manifest.json")
    targets = [s for s in manifest.get("skills", []) if "api" in s["surfaces"]]
    if not targets:
        return ["No skill targets the API: nothing to upload."]

    existing: dict[str, list[dict]] = {}
    if client is not None:
        for skill in client.list_custom():
            existing.setdefault(skill.get("display_name", ""), []).append(skill)

    log = []
    for item in targets:
        name, zip_path = item["package"], dist / item["zip"]
        matches = existing.get(name, [])
        if len(matches) > 1:
            raise SystemExit(f"Several custom skills are named '{name}': remove the duplicates.")
        if dry_run or client is None:
            action = "new version of" if matches else "create"
            log.append(f"[dry-run] would {action} '{name}' from {zip_path.name}")
        elif matches:
            result = client.create_version(matches[0]["id"], zip_path)
            log.append(f"'{name}': new version {result.get('id', '?')} of {matches[0]['id']}")
        else:
            result = client.create(name, zip_path)
            log.append(f"'{name}': created skill {result.get('id', '?')}")
    return log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, default=REPO_ROOT / "dist", help="packaged skills")
    parser.add_argument("--dry-run", action="store_true", help="show what would be uploaded")
    args = parser.parse_args(argv)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not args.dry_run:
        print("ANTHROPIC_API_KEY is not set: skipping the upload.")
        return 0
    client = SkillsClient(api_key) if api_key else None
    for line in upload(args.dist, client, args.dry_run):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
