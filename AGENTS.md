# Repository Guidelines

Guidelines for coding agents working in this repository. Keep this file about **project structure and workflow** — not any private deployment topology.

## Project Structure & Module Organization

```text
src/
  main.py           FastAPI routes, middleware, app lifespan
  config.py         Environment settings (pydantic-settings)
  storage/          Persistence: models, repository, engine factory
  i18n/             Locale resolution and message catalogs (ru/en)
  highlighting.py   Syntax / markdown detection
  templates/        Jinja2 templates (designs under designs/<name>/)
  static/           CSS, fonts, images, vendor JS
alembic/            Database migrations
tests/              pytest suite
.github/workflows/  CI, Docker publish, semantic-release
```

Root delivery files: `Dockerfile`, `docker-compose.yml`, `docker-compose.local.yml`, `pyproject.toml`, `uv.lock`, `CHANGELOG.md`, `.env.example`.

## Where to Change What

| Concern | Location |
|---------|----------|
| HTTP routes / HTML context | `src/main.py`, `src/templates/` |
| DB models / queries | `src/storage/` |
| Schema changes | `alembic/versions/` (never hand-edit prod DBs ad hoc) |
| Settings / env | `src/config.py`, `.env.example` |
| UI strings / API errors (i18n) | `src/i18n/` |
| Styles / client UX | `src/static/css/`, template `<script>` blocks |
| Release notes page | `CHANGELOG.md` → served at `/nopaste_changelog` |

## Build, Test, and Development Commands

```bash
uv sync --frozen --extra test --group dev
PYTHONPATH=src uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
uv run python src/main.py
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run ruff format src tests
uv run alembic upgrade head
docker compose up -d
docker compose --profile postgres up -d
docker compose -f docker-compose.local.yml up --build -d
```

`PYTHONPATH=src` is required for uvicorn because the app uses bare imports (`from config import ...`), matching pytest `pythonpath = ["./src"]`.

## Coding Style & Naming Conventions

- Python 3.12, 4-space indent, Ruff config in `pyproject.toml`
- `snake_case` functions/modules, `PascalCase` classes, type hints on new code
- Keep route handlers thin; persistence in `src/storage/`
- Template names lowercase and route-aligned (`index.html`, `paste.html`)

## Testing Guidelines

- `pytest` + FastAPI `TestClient`
- Files `test_*.py`, functions `test_*`
- Cover routes, cookies, storage backends, i18n `Accept-Language`, Shlink slug errors
- Prefer SQLite in-memory for unit tests; optional Postgres via compose profile / CI service

## Commit & Pull Request Guidelines

Conventional Commits (semantic-release):

- `feat:` minor · `fix:` patch · `docs:` / `ci:` / `chore:` non-user-facing

PRs: short description, commands run, screenshots for HTML/CSS changes.

## Security & Configuration

- Local overrides in `.env` (never commit)
- Do not commit secrets, API keys, or database files
- Document env vars generically in `.env.example` and README (`DATABASE_URL`, `SHRINK_URL`, `SHRINK_TOKEN`, …)
- `PASTE_ENCRYPTION_KEY` is **optional**: unset/empty → plaintext paste bodies; set → Fernet `enc:v1:` ciphertext for new writes (legacy plaintext still readable)

## Shipping

1. Push to `main` (CI lint/test; Docker image publish when paths match).
2. Releases: semantic-release updates `CHANGELOG.md` and tags; release workflow publishes versioned images.
3. Operators deploy the published image with **their** orchestrator or `docker compose pull && docker compose up -d`.

Do not put hostnames, SSH, cluster namespaces, or private inventory in this file.
