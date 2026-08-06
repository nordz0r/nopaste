# Nopaste

[![CI](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml/badge.svg)](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml)
[![Docker Hub](https://img.shields.io/docker/v/nordz0r/nopaste?label=docker&logo=docker)](https://hub.docker.com/r/nordz0r/nopaste)
[![License](https://img.shields.io/badge/license-see%20repo-blue)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](./pyproject.toml)

Self-hosted pastebin for text, logs, notes, and configs. FastAPI + Jinja2, SQLite or PostgreSQL, optional Shlink short links, optional at-rest encryption.

> 🇷🇺 [Русская версия](./README.ru.md)

## Features

- Create pastes and share by ID or optional short URL
- Line anchors (`#L12`, `#L12-L20`) and one-click copy buttons
- Recent pastes list via signed browser cookie
- Syntax highlighting + Markdown / Mermaid rendering
- SQLite (default) or PostgreSQL first-class backends (SQLAlchemy + Alembic)
- Optional body encryption when `PASTE_ENCRYPTION_KEY` is set
- RU/EN UI strings from `Accept-Language` / browser language
- Health endpoints: `/health/live`, `/health/ready`
- Docker image `nordz0r/nopaste` and Compose profiles

## Architecture

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

## Quick start

```bash
# Dependencies
uv sync --frozen --extra test --group dev

# Dev server (bare imports live under src/)
PYTHONPATH=src uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or
uv run python src/main.py
```

Open http://localhost:8000

```bash
# Published image
docker compose up -d

# Local build
docker compose -f docker-compose.local.yml up --build -d

# App + Postgres profile
DATABASE_URL=postgresql+psycopg://nopaste:nopaste@postgres:5432/nopaste \
  docker compose --profile postgres up -d
```

## Configuration

Settings load from environment / `.env` (see `.env.example`).

| Variable | Description |
|----------|-------------|
| `APP_PORT` | Listen port (default `8000`) |
| `DEBUG` | FastAPI debug mode |
| `DATABASE_PATH` | SQLite path when URL/Postgres unset |
| `DATABASE_URL` | SQLAlchemy URL (`sqlite+…` or `postgresql+psycopg://…`) |
| `POSTGRES_*` | Discrete Postgres credentials (used if URL empty) |
| `PASTE_ENCRYPTION_KEY` | **Optional.** If set/non-empty, encrypt paste bodies at rest (Fernet). Unset = plaintext. |
| `COOKIE_SIGNING_SECRET` | HMAC secret for recent-pastes cookie |
| `MAX_PASTE_SIZE_BYTES` | Max paste size |
| `MAX_RECENT_PASTES` | Cookie history cap |
| `SHRINK_URL` / `SHRINK_TOKEN` | Shlink base URL + API key (both required) |
| `PUBLIC_BASE_URL` | Canonical / Open Graph base URL |
| `UI_DESIGN` | Template design under `templates/designs/<name>/` |
| `DOCS_ALLOWLIST` | CIDR/IP list for `/docs` (empty = open) |
| `APP_VERSION` | Display version (release images set this) |

### Encryption (optional)

- **Off** (default): bodies stored as plaintext — no key required.
- **On**: set `PASTE_ENCRYPTION_KEY` to a Fernet key or any passphrase (SHA-256 derived).
- New writes use prefix `enc:v1:…`. Legacy plaintext rows stay readable after enabling the key.
- Losing the key makes encrypted pastes unreadable; treat the key as a secret.

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

## Project layout

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

## Development & tests

```bash
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run ruff format src tests
uv run alembic upgrade head
```

Raw content:

```bash
curl -fsSL 'http://localhost:8000/raw/<paste_id>'
curl -fsSL 'http://localhost:8000/paste/<paste_id>/raw'
```

## CI/CD

- `ci.yml` — lint + unit tests; optional compose smoke on workflow_dispatch
- `dockerhub.yml` — publish `nordz0r/nopaste` from `main`
- `release.yml` — semantic-release (CHANGELOG, tags, versioned images)

Conventional Commits: `feat:` → minor, `fix:` → patch.

## License

See repository license / author metadata in `pyproject.toml`.
