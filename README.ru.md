# Nopaste

[![CI](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml/badge.svg)](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml)
[![Docker Hub](https://img.shields.io/docker/v/nordz0r/nopaste?label=docker&logo=docker)](https://hub.docker.com/r/nordz0r/nopaste)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](./pyproject.toml)

Self-hosted pastebin для текста, логов, заметок и конфигов. FastAPI + Jinja2, SQLite или PostgreSQL, опционально Shlink и шифрование at-rest.

> 🇬🇧 [English README](./README.md)

## Возможности

- Создание паст и шаринг по ID или короткой ссылке
- Якоря строк (`#L12`, `#L12-L20`) и кнопки копирования
- Список недавних паст через подписанную cookie
- Подсветка синтаксиса + Markdown / Mermaid
- SQLite (по умолчанию) или PostgreSQL (SQLAlchemy + Alembic)
- **Опциональное** шифрование тел паст при наличии `PASTE_ENCRYPTION_KEY`
- RU/EN строки UI по `Accept-Language` / языку браузера
- Health: `/health/live`, `/health/ready`
- Образ Docker `nordz0r/nopaste` и Compose-профили

## Архитектура

```mermaid
flowchart LR
  Browser -->|HTTP| App[Nopaste FastAPI]
  App --> Templates[Jinja2 + static]
  App --> Storage[SQLAlchemy repository]
  Storage --> SQLite[(SQLite)]
  Storage --> PG[(PostgreSQL)]
  App -.->|опционально| Shlink[Shlink API]
  App -.->|опционально| Crypto[Fernet encrypt]
  Crypto -.-> Storage
```

## Быстрый старт

```bash
uv sync --frozen --extra test --group dev
PYTHONPATH=src uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
# или
uv run python src/main.py
```

Приложение: http://localhost:8000

```bash
docker compose up -d
docker compose -f docker-compose.local.yml up --build -d

# Профиль Postgres
DATABASE_URL=postgresql+psycopg://nopaste:nopaste@postgres:5432/nopaste \
  docker compose --profile postgres up -d
```

## Конфигурация

Переменные окружения / `.env` (см. `.env.example`).

| Переменная | Описание |
|------------|----------|
| `APP_PORT` | Порт (по умолчанию `8000`) |
| `DEBUG` | Debug-режим FastAPI |
| `DATABASE_PATH` | Путь SQLite, если URL/Postgres не заданы |
| `DATABASE_URL` | URL SQLAlchemy |
| `POSTGRES_*` | Дискретные credentials Postgres |
| `PASTE_ENCRYPTION_KEY` | **Опционально.** Если задана — шифрование тел at-rest (Fernet). Пусто = plaintext. |
| `COOKIE_SIGNING_SECRET` | HMAC для cookie recent pastes |
| `MAX_PASTE_SIZE_BYTES` | Макс. размер пасты |
| `MAX_RECENT_PASTES` | Лимит истории в cookie |
| `SHRINK_URL` / `SHRINK_TOKEN` | Shlink (нужны оба) |
| `PUBLIC_BASE_URL` | Базовый URL для OG/canonical |
| `UI_DESIGN` | Дизайн в `templates/designs/<name>/` |
| `DOCS_ALLOWLIST` | CIDR/IP для `/docs` |
| `APP_VERSION` | Версия в UI |

### Шифрование (опционально)

- **Выкл** (по умолчанию): plaintext, ключ не нужен.
- **Вкл**: задайте `PASTE_ENCRYPTION_KEY` (ключ Fernet или произвольная passphrase).
- Новые записи: `enc:v1:…`. Старый plaintext читается и после включения ключа.
- Потеря ключа = невозможность расшифровать; храните ключ как секрет.

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

## Структура

```text
src/
  main.py           маршруты FastAPI
  config.py         настройки
  storage/          модели, repository, crypto
  i18n/             каталоги en/ru
  templates/        Jinja2
  static/           CSS, шрифты, изображения
alembic/            миграции
tests/              pytest
```

## Тесты и линт

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
uv run alembic upgrade head
```

Raw:

```bash
curl -fsSL 'http://localhost:8000/raw/<paste_id>'
```

## CI/CD

- `ci.yml` — lint + unit tests
- `dockerhub.yml` — публикация образа
- `release.yml` — semantic-release

Conventional Commits: `feat:` / `fix:` / `docs:` / `ci:` / `chore:`.
