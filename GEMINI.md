# GEMINI.md

## Project Overview
**Nopaste** is a lightweight FastAPI-based web application for storing and sharing text snippets (pastes). It uses SQLite for persistence and Jinja2 for server-side template rendering. The project is designed for modern Python development with `uv` for dependency management and Docker for containerized deployment.

### Core Technologies
- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Database:** SQLite
- **Templates:** Jinja2
- **Settings:** Pydantic Settings (env-based)
- **Tooling:** `uv` (package manager), `ruff` (linting/formatting), `pytest` (testing)
- **Deployment:** Docker, Docker Compose, GitHub Actions (CI/CD)

---

## Project Structure
- `src/main.py`: Entry point, FastAPI routes, application logic, and cookie-based session management.
- `src/database.py`: SQLite database abstraction layer.
- `src/config.py`: Configuration management using environment variables.
- `src/templates/`: Jinja2 HTML templates (`base.html`, `index.html`, `paste.html`, `list.html`).
- `src/static/`: Static assets including CSS and images.
- `tests/`: Automated test suite using `pytest`.
- `pyproject.toml`: Project metadata, dependencies, and tool configurations (Ruff, Pytest, Coverage, Semantic Release).

---

## Building and Running

### Local Development
Ensure you have `uv` installed.

1.  **Install dependencies:**
    ```bash
    uv sync --frozen --extra test --group dev
    ```
2.  **Run the development server:**
    ```bash
    uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
    ```
3.  **Run tests:**
    ```bash
    uv run pytest
    ```
4.  **Lint and Format:**
    ```bash
    uv run ruff check src tests
    uv run ruff format src tests
    ```

### Docker Deployment
1.  **Production (Docker Hub image):**
    ```bash
    docker compose up -d
    ```
2.  **Local Build:**
    ```bash
    docker compose -f docker-compose.local.yml up --build -d
    ```

---

## Development Conventions

### Coding Style & Linting
- **Ruff:** Used for both linting and formatting. Configuration is in `pyproject.toml`.
- **Type Hints:** Strict type checking is enabled via `mypy` configuration.
- **Docstrings:** Important for configuration classes and database methods.

### Commits & Releases
- **Conventional Commits:** The project uses `python-semantic-release`. Commits must follow the conventional commit format (e.g., `feat:`, `fix:`, `chore:`, `ci:`) to automate versioning and changelog generation.
- **Versioning:** `python-semantic-release` updates `pyproject.toml` and `CHANGELOG.md`; release Docker builds inject the computed SemVer through `APP_VERSION`.

### Database
- SQLite is used for simplicity. The database is initialized automatically on startup (`src/database.py`).
- Default path inside containers is `/data/pastes.db` (mounted as a volume).

### Security
- **Cookie Signing:** User paste history is stored in a signed cookie `user_pastes` to prevent tampering. The `COOKIE_SIGNING_SECRET` should be set in production.
- **Paste IDs:** Short, human-readable IDs are generated using a specific alphabet (omitting ambiguous characters).

---

## CI/CD Pipeline
- **Docker Hub:** Automatically publishes the `nordz0r/nopaste` image on pushes to `main`.
- **Release:** Handles semantic versioning, updates `pyproject.toml` and `CHANGELOG.md`, tags the repo, injects `APP_VERSION` into release images, and creates GitHub releases.
