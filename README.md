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

В корне также лежат `docker-compose.yml`, `docker-compose.local.yml`, `CHANGELOG.md` и `version.txt`.

## Локальная разработка

Требования:

- Python 3.12
- `uv`
- Docker и Docker Compose, если нужен контейнерный запуск

Установка зависимостей:

```bash
uv sync --extra test --group dev
```

Запуск dev-сервера:

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Приложение будет доступно на `http://localhost:8000`.

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

По умолчанию данные SQLite сохраняются в volume `/data/pastes.db` внутри контейнера.

## Конфигурация

Настройки читаются из переменных окружения и `.env`:

- `APP_PORT` — внешний порт приложения, по умолчанию `8000`
- `DEBUG` — включает debug-режим FastAPI
- `DATABASE_PATH` — путь к SQLite-базе
- `COOKIE_SIGNING_SECRET` — секрет подписи cookie со списком recent pastes
- `MAX_PASTE_SIZE_BYTES` — максимальный размер одного paste в байтах
- `MAX_RECENT_PASTES` — сколько recent pastes хранить в cookie

## CI/CD и релизы

GitHub Actions выполняют две независимые задачи:

- `.github/workflows/dockerhub.yml` публикует образ `nordz0r/nopaste` для ветки `main`
- `.github/workflows/release.yml` выполняет semver-релиз напрямую из `main` через `python-semantic-release`

Release workflow:

- вычисляет следующую версию по conventional commits
- обновляет `pyproject.toml`, `version.txt` и `CHANGELOG.md`
- создаёт release commit, tag и GitHub Release без промежуточного release PR
- публикует semver-теги образа в Docker Hub и GHCR

Релиз использует:

- `version.txt`
- `CHANGELOG.md`
- `pyproject.toml`

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
