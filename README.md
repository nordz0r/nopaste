# Nopaste

Простое FastAPI-приложение для хранения и публикации текстовых сниппетов. Данные сохраняются в SQLite, интерфейс собран на Jinja2-шаблонах, а контейнерный деплой ориентирован на Docker Hub и GitHub Actions.

## Возможности

- создание паст и переход по короткой ссылке
- ссылки на конкретные строки и диапазоны вида `#L12` и `#L12-L20`, плюс кнопки копирования line-link
- список пользовательских паст через cookie
- health-check endpoints: `/health/live` и `/health/ready`
- локальный запуск через `uv` или Docker Compose
- автоматическая публикация образа `nordz0r/nopaste`

## Структура проекта

```text
src/
  main.py          FastAPI routes and app setup
  database.py      SQLite access layer
  config.py        environment-based settings
  templates/       Jinja2 templates
  static/          CSS and images
tests/             pytest suite
.github/workflows/ Docker Hub and release workflows
```

В корне также лежат `docker-compose.yml`, `docker-compose.local.yml`, `CHANGELOG.md`, `pyproject.toml` и `uv.lock`.

## Локальная разработка

Требования:

- Python 3.12
- `uv`
- Docker и Docker Compose, если нужен контейнерный запуск

Установка зависимостей:

```bash
uv sync --frozen --extra test --group dev
```

Запуск dev-сервера:

```bash
# PYTHONPATH=src нужен, потому что проект использует bare-импорты
# (from config import ..., from database import ...) и src/ выступает корнем.
# Это согласуется с настройкой pytest (pythonpath = ["./src"]).
PYTHONPATH=src uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Приложение будет доступно на `http://localhost:8000`.

Альтернатива (работает без PYTHONPATH, т.к. Python сам добавляет директорию скрипта в sys.path):
```bash
uv run python src/main.py
```

## Получение исходного текста

Исходное содержимое nopaste без HTML-обёртки доступно по основному raw URL:

```bash
curl -fsSL 'http://localhost:8000/raw/<paste_id>'
```

Также поддерживается alias, привязанный к URL страницы nopaste:

```bash
curl -fsSL 'http://localhost:8000/paste/<paste_id>/raw'
```

Оба endpoint возвращают `text/plain; charset=utf-8`.

Проверки:

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
```

## Docker Compose

Основной compose-файл тянет опубликованный образ `main` из Docker Hub:

```bash
docker compose up -d
```

Локальная сборка из текущего исходного кода выполняется отдельным файлом:

```bash
docker compose -f docker-compose.local.yml up --build -d
```

Helper-скрипты поддерживают выбор compose-файла через `COMPOSE_FILE`:

```bash
COMPOSE_FILE=docker-compose.local.yml ./restart.sh nopaste-app
COMPOSE_FILE=docker-compose.local.yml ./logs.sh nopaste-app
COMPOSE_FILE=docker-compose.local.yml ./stop.sh nopaste-app
```

По умолчанию локальные данные SQLite сохраняются в volume `/data/pastes.db` внутри контейнера.
В production (`paste.goldfinches.ru`) pastes хранятся в shared PostgreSQL (tenant `nopaste`) и переживают рестарт pod.

## Конфигурация

Настройки читаются из переменных окружения и `.env`:

- `APP_PORT` — внешний порт приложения, по умолчанию `8000`
- `DEBUG` — включает debug-режим FastAPI
- `DATABASE_PATH` — путь к SQLite-базе (local/tests; используется, если Postgres не задан)
- `DATABASE_URL` — PostgreSQL DSN (`postgresql://...`); приоритетнее `DATABASE_PATH` и `POSTGRES_*`
- `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_SSLMODE` — дискретные credentials для production
- `COOKIE_SIGNING_SECRET` — секрет подписи cookie со списком recent pastes
- `MAX_PASTE_SIZE_BYTES` — максимальный размер одного paste в байтах
- `MAX_RECENT_PASTES` — сколько recent pastes хранить в cookie
- `SHRINK_URL` — базовый URL Shlink, если нужен короткий URL для paste
- `SHRINK_TOKEN` — API-ключ Shlink
- `PUBLIC_BASE_URL` — внешний базовый URL приложения для canonical/Open Graph/Twitter preview-метаданных (например, `https://paste.goldfinches.ru`)
- `APP_VERSION` — отображаемая версия приложения; release-образ получает её автоматически из `python-semantic-release`, локально используется fallback из `pyproject.toml`

## CI/CD и релизы

GitHub Actions выполняют две независимые задачи:

- `.github/workflows/dockerhub.yml` публикует образ `nordz0r/nopaste` для ветки `main`
- `.github/workflows/release.yml` выполняет semver-релиз напрямую из `main` через `python-semantic-release`

Release workflow:

- вычисляет следующую версию по conventional commits
- обновляет `pyproject.toml` и `CHANGELOG.md`
- создаёт release commit, tag и GitHub Release без промежуточного release PR
- передаёт вычисленную версию в Docker build через `APP_VERSION`
- публикует semver-теги и `latest` образа в Docker Hub и GHCR

Релиз использует:

- `CHANGELOG.md`
- `pyproject.toml`
- `uv.lock`

Для корректной работы релизов нужны secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

## Коммиты

Репозиторий использует conventional commits. Для релизов это важно:

- `feat:` повышает minor-версию
- `fix:` повышает patch-версию
- breaking changes повышают major-версию

Примеры:

```text
feat: add paste expiration
fix: validate empty paste content
ci: update Docker publish workflow
```
