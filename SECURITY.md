# Security

## Reporting

Email the maintainer listed in `pyproject.toml` / GitHub profile. Do not file a public issue for a vulnerability.

## Deployment notes

- Change `COOKIE_SIGNING_SECRET` in every non-local environment
- Leave `PASTE_ENCRYPTION_KEY` unset unless you need at-rest encryption; treat it as a secret if set
- Set `DOCS_ALLOWLIST` in production if `/docs` must not be public
- Put the app behind TLS; cookies become `Secure` automatically on HTTPS
- The in-memory rate limiter is per-process. Use a reverse-proxy limit if you run multiple workers

## Scope

Nopaste stores whatever text users paste. Treat an instance as a private sharing tool, not a public archive. Search indexing is disabled by default.
