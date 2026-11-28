# Security policy

Plugins from this repository run on your machine with Claude Code's permissions:
hooks execute commands and MCP servers run as local processes. Review a plugin
before installing it.

## Supported versions

Only the latest release of each plugin receives security fixes.

## Reporting a vulnerability

Please **do not** open a public issue for a vulnerability.

Use GitHub's private vulnerability reporting instead: open the **Security** tab
of this repository, then **Report a vulnerability**. The report stays private
between you and the maintainer until a fix is published.

You can expect a first answer within 14 days. A confirmed vulnerability is
fixed privately, then published as a GitHub Security Advisory with the release
that fixes it, crediting the reporter unless they prefer otherwise.

## Verifying a release

Every release is built by GitHub Actions, and the skill zips attached to it
carry a signed build provenance attestation. To check a downloaded file:

```bash
gh attestation verify <plugin>-<skill>.zip --repo AdCodicem/skills
```
