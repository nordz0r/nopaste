# Repository Guidelines

## Project Structure & Module Organization
`src/` contains the FastAPI application. `src/main.py` defines routes and mounts templates/static assets, `src/database.py` wraps SQLite access, and `src/config.py` loads environment-based settings. Jinja templates live in `src/templates/`; CSS and images live in `src/static/`. Tests are under `tests/`. Runtime and delivery files stay at the repo root: `Dockerfile`, `docker-compose.yml`, shell helpers, `pyproject.toml`, and `uv.lock`.

## Build, Test, and Development Commands
`uv sync` installs the pinned Python dependencies.
`uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` starts the local dev server with reload.
`uv run python src/main.py` runs the app through its entry point.
`uv run pytest` executes the test suite.
`uv run pytest --cov=src --cov-report=term-missing` checks coverage for changed code.
`uv run ruff check src tests` lints Python sources and tests.
`uv run ruff format src tests` formats Python code.
`docker compose up --build` runs the app in a container.

## Coding Style & Naming Conventions
Target Python 3.12 and follow the Ruff configuration in `pyproject.toml`. Use 4-space indentation, `snake_case` for modules/functions/variables, and `PascalCase` for classes. Add type hints to new Python code and keep route handlers thin; move persistence logic into `src/database.py` or another dedicated module instead of embedding SQL in endpoints. Keep template filenames lowercase and route-aligned, for example `index.html` and `paste.html`.

## Testing Guidelines
Use `pytest` with FastAPI’s `TestClient`. Name files `test_*.py` and test functions `test_*`. Add coverage for new routes, redirects, cookie behavior, and database interactions. No minimum coverage threshold is enforced in config, so avoid lowering coverage on touched code and run the coverage command before opening a PR.

## Commit & Pull Request Guidelines
Recent history favors short, imperative commit subjects; `feat:` and `fix:` prefixes are common for code changes. Prefer focused messages such as `feat: add paste validation` over vague subjects like `update`. PRs should include a concise description, linked issue when applicable, the verification commands you ran, and screenshots for HTML/CSS changes.

## Security & Configuration Tips
Store local overrides in `.env`; `src/config.py` reads `APP_PORT`, `DEBUG`, and `DATABASE_PATH`. Do not commit `.env`, SQLite database files, or log output. The default local database path is `/tmp/pastes.db`; set an explicit path or Docker volume for persistent environments.
