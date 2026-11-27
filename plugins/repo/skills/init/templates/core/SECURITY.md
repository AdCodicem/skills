# Security policy

## Supported versions

Only the latest release receives security fixes. Previews receive none of
their own: the fix ships in the next release and the previews that follow it.

## Reporting a vulnerability

Please **do not** open a public issue for a vulnerability.

Use GitHub's private vulnerability reporting instead: open the **Security** tab
of this repository, then **Report a vulnerability**. The report stays private
between you and the maintainers until a fix is published.

You can expect a first answer within 14 days. A confirmed vulnerability is
fixed privately, then published as a GitHub Security Advisory with the release
that fixes it, crediting the reporter unless they prefer otherwise.

## Verifying a release

Every release is built by GitHub Actions and its packages carry a signed build
provenance attestation. To check a downloaded file:

```bash
gh attestation verify <file> --repo {{owner}}/{{repo}}
```
