# Repository Guidelines

## Project Structure & Module Organization
`src/` contains the FastAPI application. `src/main.py` defines routes and mounts templates/static assets, `src/database.py` wraps SQLite access, and `src/config.py` loads environment-based settings. Jinja templates live in `src/templates/`; CSS and images live in `src/static/`. Tests are under `tests/`. Delivery files stay at the repo root: `Dockerfile`, `docker-compose.yml`, `docker-compose.local.yml`, shell helpers, `pyproject.toml`, `uv.lock`, `release-please-config.json`, `.release-please-manifest.json`, `version.txt`, and `CHANGELOG.md`.

## Build, Test, and Development Commands
`uv sync --extra test --group dev` installs the pinned app, test dependencies, and dev tools such as Ruff.
`uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` starts the local dev server with reload.
`uv run python src/main.py` runs the app through its entry point.
`uv run pytest` executes the test suite.
`uv run pytest --cov=src --cov-report=term-missing` checks coverage for changed code.
`uv run ruff check src tests` lints Python sources and tests.
`uv run ruff format src tests` formats Python code.
`docker compose up -d` runs the published `nordz0r/nopaste:main` image.
`docker compose -f docker-compose.local.yml up --build -d` builds and runs the local source tree.
`COMPOSE_FILE=docker-compose.local.yml ./restart.sh nopaste-app` restarts the local compose service using the helper scripts.

## Coding Style & Naming Conventions
Target Python 3.12 and follow the Ruff configuration in `pyproject.toml`. Use 4-space indentation, `snake_case` for modules/functions/variables, and `PascalCase` for classes. Add type hints to new Python code and keep route handlers thin; move persistence logic into `src/database.py` or another dedicated module instead of embedding SQL in endpoints. Keep template filenames lowercase and route-aligned, for example `index.html` and `paste.html`.

## Testing Guidelines
Use `pytest` with FastAPI’s `TestClient`. Name files `test_*.py` and test functions `test_*`. Add coverage for new routes, redirects, cookie behavior, and database interactions. No minimum coverage threshold is enforced in config, so avoid lowering coverage on touched code and run the coverage command before opening a PR.

## Commit & Pull Request Guidelines
This repository uses conventional commits because `release-please` derives semver bumps and changelog entries from commit history. Use `feat:` for minor releases, `fix:` for patch releases, and keep `ci:`, `docs:`, and `chore:` for non-user-facing changes. Prefer focused subjects such as `fix: validate empty paste content` over vague messages like `update`. PRs should include a concise description, linked issue when applicable, the verification commands you ran, and screenshots for HTML/CSS changes.

## Security & Configuration Tips
Store local overrides in `.env`; `src/config.py` reads `APP_PORT`, `DEBUG`, `DATABASE_PATH`, `COOKIE_SIGNING_SECRET`, `MAX_PASTE_SIZE_BYTES`, and `MAX_RECENT_PASTES`. Do not commit `.env`, SQLite database files, or log output. The default local database path is `/tmp/pastes.db`; the compose files override this to `/data/pastes.db` inside a Docker volume. For GitHub automation, keep `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, and `RELEASE_PLEASE_TOKEN` in repository secrets rather than in tracked files.
