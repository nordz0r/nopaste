<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset=".github/assets/banner-light.svg">
    <img alt="nordz0r/nopaste — self-hosted pastebin" src=".github/assets/banner-light.svg" width="100%">
  </picture>
</p>

<p align="center"><a href="README.md">Русский</a> · <b>English</b></p>

<p align="center">
  <img src="docs/hero.png" alt="Nopaste — self-hosted pastebin" width="800">
</p>

<p align="center">
  <strong>Self-hosted pastebin for text, logs, notes, and configs.</strong><br>
  Fast. Private. Anonymous by default. One container.
</p>

<p align="center">

[![CI](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml/badge.svg)](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/nordz0r/nopaste?style=social)](https://github.com/nordz0r/nopaste/stargazers)
[![Docker Hub](https://img.shields.io/docker/v/nordz0r/nopaste?sort=semver&label=docker&logo=docker)](https://hub.docker.com/r/nordz0r/nopaste)
[![GHCR](https://img.shields.io/badge/ghcr-nordz0r%2Fnopaste-blue?logo=github)](https://github.com/nordz0r/nopaste/pkgs/container/nopaste)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](./pyproject.toml)

</p>


```bash
docker compose up -d
# → http://localhost:8000
```

Local trials default to `DEBUG=true`. Production must set `DEBUG=false` and a unique `COOKIE_SIGNING_SECRET`.

If Nopaste is useful, [star the repo](https://github.com/nordz0r/nopaste) — it is the single best way to help others find it.

## Why Nopaste

Most pastebins are either public SaaS or heavy appliances. Nopaste is a single container you can run at home, on a VPS, or behind your reverse proxy.

- **Anonymous by default** — no sign-up needed to create or read a paste
- **Share by ID** or an optional Shlink short URL
- **Line anchors** (`#L12`, `#L12-L20`) and one-click copy
- **RAW** view (`/raw/<id>`) for curl, CI, and editors
- **Syntax highlighting** plus Markdown / Mermaid
- **SQLite by default**, PostgreSQL when you need it
- **Optional at-rest encryption** (`PASTE_ENCRYPTION_KEY`)
- **Optional accounts via OIDC** — personal bookmarks; owners edit their pastes; staff/admin may edit any paste
- **Bookmarks / favorites** and a 7-day paginated paste list
- **WebMCP tools** so AI agents can create and read pastes on the page
- **RU/EN UI** from `Accept-Language`
- **Feedback** in the footer opens a prefilled GitHub issue
- **No search indexing** (`robots.txt` + `noindex`)
- **Telegram preview / Instant View** support for paste pages

| | Nopaste | PrivateBin | haste-server |
|---|:---:|:---:|:---:|
| One Docker image | ✓ | ✓ | ✓ |
| Zero-knowledge / client crypto | — | ✓ | — |
| Optional server-side encryption | ✓ | — | — |
| Markdown + Mermaid | ✓ | — | — |
| Line anchors `#L12-L20` | ✓ | — | — |
| SQLite *or* Postgres | ✓ | ✓ | ✓ |
| Optional accounts (OIDC) | ✓ | — | — |
| Shlink short URLs | ✓ | — | — |
| RU / EN UI | ✓ | — | — |

## Quick start

```bash
# Published image (SQLite, data in a volume)
docker compose up -d

# Local build
docker compose -f docker-compose.local.yml up --build -d

# App + Postgres
DATABASE_URL=postgresql+psycopg://nopaste:nopaste@postgres:5432/nopaste \
  docker compose --profile postgres up -d
```

From source:

```bash
uv sync --frozen --extra test --group dev
PYTHONPATH=src uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

```bash
# Raw content
curl -fsSL "http://localhost:8000/raw/<paste_id>"
```

Telegram preview and Instant View setup: [docs/telegram-instant-view.md](docs/telegram-instant-view.md).

Images:

| Registry | Image |
|----------|--------|
| Docker Hub | `nordz0r/nopaste:latest` |
| GHCR | `ghcr.io/nordz0r/nopaste:latest` |
| Rolling `main` | `nordz0r/nopaste:main` |

## Features

| | |
|---|---|
| Editor | Ctrl/⌘+Enter to save, signed recent-pastes cookie |
| Viewer | Highlighted lines, Markdown toggle, `</>` RAW button |
| Links | Copy page URL or Shlink slug; click a line number to copy `#Ln` |
| Accounts | Optional OIDC login · bookmarks · edit/delete · 7-day list paging |
| Agents | WebMCP tools (`document.modelContext`): create with strict vanity slug, inspect short/share URLs, read pastes |
| Storage | SQLAlchemy + Alembic · SQLite or PostgreSQL |
| Ops | `/health/live`, `/health/ready`, in-memory rate limit, docs allowlist |


## Diagrams

Markdown pastes render two kinds of diagrams: animated [PR Lens](https://github.com/coldteadotai/pr-lens) graphs and [Mermaid](https://mermaid.js.org/). Both render in the browser, follow the site's light/dark theme and re-render when it changes.

### Nopaste architecture

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/assets/architecture-dark.gif">
  <source media="(prefers-color-scheme: light)" srcset=".github/assets/architecture-light.gif">
  <img alt="Nopaste architecture (PR Lens)" src=".github/assets/architecture-light.gif" width="100%">
</picture>

Drawn with PR Lens using the [pr-lens-diagrams](https://github.com/nordz0r/skills/tree/main/pr-lens-diagrams) skill (`PALETTE=github bash scripts/pr-lens-build.sh docs/diagrams/architecture.graph.json out both`). Source: [docs/diagrams/architecture.graph.json](docs/diagrams/architecture.graph.json) — you can paste it into a paste as well.

### PR Lens

Live example: [paste.goldfinches.ru/paste/tpw6qstn](https://paste.goldfinches.ru/paste/tpw6qstn).

**How to embed.** Create a Markdown paste and put a `graph.json` document (PR Lens schema, `schemaVersion` 0.2.0) into a code block:

- ` ```prlens ` — always rendered;
- ` ```json ` — rendered when the document has `"kind": "graph"` and a string `schemaVersion`; any other JSON stays a regular code block.

For a ` ```json ` block the source stays under a `graph.json` spoiler below the diagram.

**Features:**

- **Lens tabs** — one per lens listed in `lenses` (`architecture`, `data-flow`, …).
- **Download SVG** — saves the current lens in the current theme (`<title>-<lens>-<dark|light>.svg`).
- **Light/dark theme** — background, borders and text come from Nopaste theme CSS variables; diff colours (added/modified/removed) are kept.
- **Errors** — invalid JSON or a document that fails the schema is shown as a message inside the block instead of the diagram; the rest of the paste renders normally.

**Security.** The `@coldtea/pr-lens-renderer` (MIT, pinned version) is served from the same origin and loaded only when a paste contains a diagram. The resulting SVG is shown only as `<img src="blob:…">`: scripts and event handlers inside it never run, only SMIL animation plays. This fits the CSP (`script-src 'self' 'nonce-…'`, `img-src 'self' data: blob:`). The JSON source is escaped into a hidden `<textarea>`, never into markup.

Minimal working example:

````markdown
```prlens
{
  "schemaVersion": "0.2.0",
  "kind": "graph",
  "title": "Hello PR Lens",
  "lenses": ["architecture"],
  "provenance": {
    "repo": { "owner": "example", "name": "demo", "host": "github.com" },
    "base": { "sha": "0000000000000000000000000000000000000000", "ref": "main" },
    "head": { "sha": "0000000000000000000000000000000000000000", "ref": "main" },
    "generator": { "name": "manual", "version": "1.0.0" }
  },
  "lanes": [
    { "id": "client", "label": "Client", "order": 0 },
    { "id": "server", "label": "Server", "order": 1 }
  ],
  "nodes": [
    { "id": "browser", "label": "Browser", "kind": "ui", "delta": "unchanged", "lane": "client", "files": [], "badges": [] },
    { "id": "api", "label": "API", "kind": "service", "delta": "unchanged", "lane": "server", "files": [], "badges": [] },
    { "id": "db", "label": "Database", "kind": "datastore", "delta": "unchanged", "lane": "server", "files": [], "badges": [] }
  ],
  "edges": [
    { "id": "e1", "from": "browser", "to": "api", "kind": "http", "delta": "unchanged", "emphasis": "hero", "animated": true, "label": "HTTP", "files": [] },
    { "id": "e2", "from": "api", "to": "db", "kind": "data", "delta": "unchanged", "emphasis": "normal", "animated": true, "files": [] }
  ],
  "flows": []
}
```
````

The bundle is built in the Dockerfile (`frontend/prlens`, `npm ci` from the lock file) and is not stored in git. For a local run without Docker: `cd frontend/prlens && npm ci && npm run build`.

### Mermaid

A ` ```mermaid ` block is rendered by Mermaid (vendored, same origin) in PR Lens style: `base` theme with Nopaste colours, large 16 px font, curved edges and an animated flow along the edges.

- Re-renders when the light/dark theme is switched.
- With `prefers-reduced-motion: reduce` the animation is turned off.
- `securityLevel: "strict"`: HTML in labels and click handlers are disabled.

```mermaid
flowchart LR
  Browser -->|HTTP| App[FastAPI]
  App --> Storage[(SQLite / PostgreSQL)]
  App -.->|optional| Shlink[Shlink API]
```

## Configuration

Settings load from the environment / `.env` (see `.env.example`).

| Variable | Description |
|----------|-------------|
| `APP_PORT` | Listen port (default `8000`) |
| `DEBUG` | FastAPI debug mode |
| `DATABASE_PATH` | SQLite path when URL/Postgres unset |
| `DATABASE_URL` | SQLAlchemy URL (`sqlite+…` or `postgresql+psycopg://…`) |
| `POSTGRES_*` | Discrete Postgres credentials (used if URL empty) |
| `PASTE_ENCRYPTION_KEY` | **Optional.** Fernet key or passphrase — encrypts bodies at rest |
| `COOKIE_SIGNING_SECRET` | HMAC secret for the recent-pastes cookie. Required unique value when `DEBUG=false`. |
| `TRUSTED_PROXY_IPS` | Comma-separated proxy IPs/CIDRs allowed to supply `X-Forwarded-For`. Empty ignores the header. |
| `FORWARDED_ALLOW_IPS` | Matching uvicorn `--forwarded-allow-ips` value. Keep in sync with `TRUSTED_PROXY_IPS`. |
| `MAX_PASTE_SIZE_BYTES` | Max paste size |
| `MAX_RECENT_PASTES` | Cookie history cap |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | Create/update rate limit |
| `SHRINK_URL` / `SHRINK_TOKEN` | Shlink base URL + API key (both required) |
| `PUBLIC_BASE_URL` | Canonical / Open Graph base URL |
| `UI_DESIGN` | Template design under `templates/designs/<name>/` |
| `GITHUB_REPO` | `owner/name` for the footer Feedback button (empty hides it) |
| `DOCS_ALLOWLIST` | CIDR/IP list for `/docs` (empty = open) |
| `APP_VERSION` | Display version (release images set this) |
| `OIDC_DISCOVERY_URL` | **Optional.** OIDC discovery document URL — enables login |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | OIDC client credentials (both required for login) |
| `OIDC_SCOPES` / `OIDC_REDIRECT_URI` | Requested scopes and the registered callback URL |
| `SESSION_SECRET_KEY` | Session cookie signing secret (falls back to `COOKIE_SIGNING_SECRET`) |
| `SESSION_COOKIE_NAME` / `SESSION_MAX_AGE_SECONDS` | Session cookie name and lifetime |
| `YANDEX_METRIKA_ID` | **Optional.** Your Yandex.Metrika counter ID (empty = no analytics tag) |

### Encryption (optional)

- **Off** (default): bodies stored as plaintext.
- **On**: set `PASTE_ENCRYPTION_KEY`. New writes use `enc:v1:…`. Legacy plaintext rows stay readable.
- Losing the key makes encrypted pastes unreadable.

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

### Accounts (optional)

Nopaste is fully usable **anonymously** — no login is required to create or read
a paste. Accounts are optional and off by default.

Set `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID`, and `OIDC_CLIENT_SECRET` to enable
login with any standard OpenID Connect provider (Keycloak, Authentik, Nextcloud,
Google, …). When enabled, signed-in users get:

- **Bookmarks / favorites** — a personal list of saved pastes
- **Edit and delete** their own pastes; `role=staff` or `role=admin` may edit any paste
- A **7-day paginated list** of recent pastes

Anonymous ownership of freshly created pastes still works through the signed
`user_pastes` cookie, independent of accounts.

## Releases

Releases are cut automatically from Conventional Commits on `main`:

| Prefix | Version bump |
|--------|----------------|
| `feat:` | minor |
| `fix:` / `perf:` | patch |

Workflow:

1. `release.yml` runs [python-semantic-release](https://python-semantic-release.readthedocs.io/) — updates `pyproject.toml` + `CHANGELOG.md`, tags `vX.Y.Z`, opens a GitHub Release.
2. The same workflow publishes versioned images (`1.13.1`, `v1.13.1`, `1.13`, `latest`) to Docker Hub and GHCR.
3. `dockerhub.yml` also publishes the rolling `main` and `sha-*` tags. It never overwrites `latest`.

See [CHANGELOG.md](./CHANGELOG.md) or the in-app footer changelog.

## Development

```text
src/
  main.py           FastAPI routes
  config.py         pydantic-settings
  auth.py           OIDC login + session helpers
  cookies.py        signed cookie encode/decode
  storage/          models, repository, crypto, engine
  i18n/             en/ru catalogs
  highlighting.py   syntax / markdown
  list_paging.py    7-day calendar paging
  templates/        Jinja2 designs
  static/           CSS, fonts, images, JS (app.js, webmcp.js, sw.js)
alembic/            migrations
tests/              pytest
.github/workflows/  CI, Docker, semantic-release
```

```bash
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run ruff format src tests
uv run alembic upgrade head
```

## License

[MIT](./LICENSE) © nordz0r
