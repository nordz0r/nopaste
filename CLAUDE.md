# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nopaste is a lightweight paste-sharing web app built with FastAPI, SQLite, and Jinja2 templates. Users create text snippets that get short IDs and can be viewed/shared via URL. Paste ownership is tracked via HMAC-SHA256 signed cookies (no auth system).

## Commands

```bash
# Install all deps (app + test + dev tools)
uv sync --frozen --extra test --group dev

# Dev server with auto-reload
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_main.py::test_create_paste

# Coverage
uv run pytest --cov=src --cov-report=term-missing

# Lint and format
uv run ruff check src tests
uv run ruff format src tests

# Docker (published image)
docker compose up -d

# Docker (local build)
docker compose -f docker-compose.local.yml up --build -d
```

## Architecture

**`src/main.py`** - FastAPI app with all routes, cookie signing/verification logic, paste ID generation, and template rendering. This is the monolith; persistence helpers are in `database.py` but everything else (cookie HMAC, content normalization, line building) lives here.

**`src/database.py`** - Thin SQLite wrapper (`Database` class). Single `pastes` table with `id`, `content`, `created_at`, `short_url`. `get_user_pastes()` preserves cookie-based ordering via in-memory sort.

**`src/config.py`** - Pydantic Settings loading from env vars / `.env` file. Key settings: `DATABASE_PATH`, `COOKIE_SIGNING_SECRET`, `MAX_PASTE_SIZE_BYTES`, `MAX_RECENT_PASTES`, `SHRINK_URL`, `SHRINK_TOKEN`.

**Routes:** `GET /` (form), `POST /paste` (create), `GET /paste/{id}` (view), `GET /list` (user's pastes from cookie), `GET /health/live`, `GET /health/ready`.

**Paste IDs** are 6 chars from a confusable-free alphabet (`23456789abcdefghjkmnpqrstuvwxyz`), generated with collision retry (max 20 attempts).

**Cookie format:** `{base64_payload}.{hmac_sha256_signature}`. Legacy unsigned cookies (pre-signing) are accepted read-only for backwards compatibility.

**Templates** in `src/templates/` use Jinja2. Static assets (CSS, bundled fonts, SVG icons) in `src/static/` are fully self-contained with no external URLs or CDN dependencies.

**URL shortening (Shlink):** When `SHRINK_URL` and `SHRINK_TOKEN` are set, paste creation calls `POST {SHRINK_URL}/rest/v3/short-urls` to generate a short link (stored in `short_url` column). The short URL is shown on the paste view and used by the Copy Link button. Falls back gracefully when Shlink is unavailable.

## Testing

Tests use FastAPI's `TestClient` via a `client` fixture that monkeypatches the database to a temp path. Tests cover routes, cookie tampering, paste size limits, ID collision handling, line anchors, and list ordering. No minimum coverage threshold is enforced.

## Conventions

- **Conventional commits required** - `feat:` (minor), `fix:` (patch), `ci:`/`docs:`/`chore:` (no release). Releases are automated via `python-semantic-release`.
- **Versioning:** `python-semantic-release` owns `pyproject.toml` and `CHANGELOG.md`; release Docker builds inject the computed SemVer through `APP_VERSION`.
- Python 3.12, type hints on new code, Ruff for lint+format (config in `pyproject.toml`).
- Keep route handlers thin; persistence logic belongs in `database.py`.
- `pythonpath` in pytest config is set to `["./src"]`, so imports use bare module names (e.g., `from config import settings`).
