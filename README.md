# Nopaste

<p align="center">
  <img src="docs/hero.png" alt="Nopaste — self-hosted pastebin" width="800">
</p>

<p align="center">
  <strong>Self-hosted pastebin for text, logs, notes, and configs.</strong><br>
  Fast. Private. No accounts. One container.
</p>

<p align="center">

[![CI](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml/badge.svg)](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/nordz0r/nopaste?style=social)](https://github.com/nordz0r/nopaste/stargazers)
[![Docker Hub](https://img.shields.io/docker/v/nordz0r/nopaste?sort=semver&label=docker&logo=docker)](https://hub.docker.com/r/nordz0r/nopaste)
[![GHCR](https://img.shields.io/badge/ghcr-nordz0r%2Fnopaste-blue?logo=github)](https://github.com/nordz0r/nopaste/pkgs/container/nopaste)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](./pyproject.toml)

</p>

> 🇷🇺 [Русская версия](./README.ru.md)

```bash
docker compose up -d
# → http://localhost:8000
```

If Nopaste is useful, [star the repo](https://github.com/nordz0r/nopaste) — it is the single best way to help others find it.

## Why Nopaste

Most pastebins are either public SaaS or heavy appliances. Nopaste is a single container you can run at home, on a VPS, or behind your reverse proxy.

- **Share by ID** or an optional Shlink short URL
- **Line anchors** (`#L12`, `#L12-L20`) and one-click copy
- **RAW** view (`/raw/<id>`) for curl, CI, and editors
- **Syntax highlighting** plus Markdown / Mermaid
- **SQLite by default**, PostgreSQL when you need it
- **Optional at-rest encryption** (`PASTE_ENCRYPTION_KEY`)
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
| SQLite *or* Postgres | ✓ | ✓ | file store |
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
| Storage | SQLAlchemy + Alembic · SQLite or PostgreSQL |
| Ops | `/health/live`, `/health/ready`, in-memory rate limit, docs allowlist |

```mermaid
flowchart LR
  Browser -->|HTTP| App[Nopaste FastAPI]
  App --> Templates[Jinja2 + static]
  App --> Storage[SQLAlchemy repository]
  Storage --> SQLite[(SQLite)]
  Storage --> PG[(PostgreSQL)]
  App -.->|optional| Shlink[Shlink API]
  App -.->|optional| Crypto[Fernet encrypt]
  Crypto -.-> Storage
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
| `COOKIE_SIGNING_SECRET` | HMAC secret for the recent-pastes cookie. Change in production. |
| `MAX_PASTE_SIZE_BYTES` | Max paste size |
| `MAX_RECENT_PASTES` | Cookie history cap |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | Create/update rate limit |
| `SHRINK_URL` / `SHRINK_TOKEN` | Shlink base URL + API key (both required) |
| `PUBLIC_BASE_URL` | Canonical / Open Graph base URL |
| `UI_DESIGN` | Template design under `templates/designs/<name>/` |
| `GITHUB_REPO` | `owner/name` for the footer Feedback button (empty hides it) |
| `DOCS_ALLOWLIST` | CIDR/IP list for `/docs` (empty = open) |
| `APP_VERSION` | Display version (release images set this) |

### Encryption (optional)

- **Off** (default): bodies stored as plaintext.
- **On**: set `PASTE_ENCRYPTION_KEY`. New writes use `enc:v1:…`. Legacy plaintext rows stay readable.
- Losing the key makes encrypted pastes unreadable.

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

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
  storage/          models, repository, crypto, engine
  i18n/             en/ru catalogs
  highlighting.py   syntax / markdown
  templates/        Jinja2 designs
  static/           CSS, fonts, images, JS
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
