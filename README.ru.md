# Nopaste

<p align="center">
  <img src="docs/hero.png" alt="Nopaste — self-hosted pastebin" width="800">
</p>

<p align="center">

[![CI](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml/badge.svg)](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/nordz0r/nopaste?style=social)](https://github.com/nordz0r/nopaste/stargazers)
[![Docker Hub](https://img.shields.io/docker/v/nordz0r/nopaste?sort=semver&label=docker&logo=docker)](https://hub.docker.com/r/nordz0r/nopaste)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

</p>

Self-hosted pastebin для текста, логов, заметок и конфигов. Быстро, без аккаунтов.

Если Nopaste полезен — [поставьте звезду](https://github.com/nordz0r/nopaste). Это лучший способ помочь проекту.

> 🇬🇧 [English README](./README.md)

```bash
docker compose up -d
# → http://localhost:8000
```

## Зачем

Публичные pastebin — чужой SaaS. Nopaste — один контейнер: дома, на VPS или за своим прокси.

- Шаринг по ID или короткой ссылке Shlink
- Якоря строк (`#L12`, `#L12-L20`) и кнопки копирования
- **RAW** (`/raw/<id>`) для curl, CI и редакторов
- Подсветка синтаксиса + Markdown / Mermaid
- SQLite по умолчанию, PostgreSQL при необходимости
- Опциональное шифрование at-rest (`PASTE_ENCRYPTION_KEY`)
- RU/EN UI по `Accept-Language`
- **Feedback** в подвале открывает предзаполненный issue в GitHub
- Без индексации (`robots.txt` + `noindex`)
- Preview и Instant View для Telegram

## Быстрый старт

```bash
docker compose up -d
docker compose -f docker-compose.local.yml up --build -d

DATABASE_URL=postgresql+psycopg://nopaste:nopaste@postgres:5432/nopaste \
  docker compose --profile postgres up -d
```

Из исходников:

```bash
uv sync --frozen --extra test --group dev
PYTHONPATH=src uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

```bash
curl -fsSL "http://localhost:8000/raw/<paste_id>"
```

Настройка Telegram preview и Instant View: [docs/telegram-instant-view.md](docs/telegram-instant-view.md).

Образы: `nordz0r/nopaste:latest`, `ghcr.io/nordz0r/nopaste:latest`, rolling `nordz0r/nopaste:main`.

## Конфигурация

Переменные окружения / `.env` (см. `.env.example`).

| Переменная | Описание |
|------------|----------|
| `APP_PORT` | Порт (по умолчанию `8000`) |
| `DEBUG` | Debug-режим FastAPI |
| `DATABASE_PATH` | Путь SQLite, если URL/Postgres не заданы |
| `DATABASE_URL` | URL SQLAlchemy |
| `POSTGRES_*` | Дискретные credentials Postgres |
| `PASTE_ENCRYPTION_KEY` | **Опционально.** Fernet или passphrase — шифрование тел |
| `COOKIE_SIGNING_SECRET` | HMAC для cookie истории. Смените в проде. |
| `MAX_PASTE_SIZE_BYTES` | Макс. размер paste |
| `MAX_RECENT_PASTES` | Лимит истории в cookie |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | Лимит на создание/обновление |
| `SHRINK_URL` / `SHRINK_TOKEN` | Shlink (нужны оба) |
| `PUBLIC_BASE_URL` | Базовый URL для OG/canonical |
| `UI_DESIGN` | Дизайн в `templates/designs/<name>/` |
| `DOCS_ALLOWLIST` | CIDR/IP для `/docs` |
| `APP_VERSION` | Версия в UI |

## Релизы

С `main` по Conventional Commits: `feat:` → minor, `fix:` → patch.

- `release.yml` — semantic-release (CHANGELOG, тег `vX.Y.Z`, GitHub Release) и версионированные образы
- `dockerhub.yml` — rolling-теги `main` и `sha-*`, **не** перезаписывает `latest`

## Разработка

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
```

## Лицензия

[MIT](./LICENSE) © nordz0r
