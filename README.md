<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".github/assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset=".github/assets/banner-light.svg">
    <img alt="nordz0r/nopaste — self-hosted pastebin" src=".github/assets/banner-light.svg" width="100%">
  </picture>
</p>

<p align="center"><b>Русский</b> · <a href="README.en.md">English</a></p>

<p align="center">
  <img src="docs/hero.png" alt="Nopaste — self-hosted pastebin" width="800">
</p>

<p align="center">
  <strong>Self-hosted pastebin для текста, логов, заметок и конфигов.</strong><br>
  Быстро. Приватно. Анонимно по умолчанию. Один контейнер.
</p>

<p align="center">

[![CI](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml/badge.svg)](https://github.com/nordz0r/nopaste/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/nordz0r/nopaste?style=social)](https://github.com/nordz0r/nopaste/stargazers)
[![Docker Hub](https://img.shields.io/docker/v/nordz0r/nopaste?sort=semver&label=docker&logo=docker)](https://hub.docker.com/r/nordz0r/nopaste)
[![GHCR](https://img.shields.io/badge/ghcr-nordz0r%2Fnopaste-blue?logo=github)](https://github.com/nordz0r/nopaste/pkgs/container/nopaste)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](./pyproject.toml)

</p>


```bash
docker compose up -d
# → http://localhost:8000
```

Для локальной пробы по умолчанию `DEBUG=true`. В продакшене обязательно задайте `DEBUG=false` и уникальный `COOKIE_SIGNING_SECRET`.

Если Nopaste полезен — [поставьте звезду](https://github.com/nordz0r/nopaste). Это лучший способ помочь другим его найти.

## Зачем Nopaste

Большинство pastebin — либо публичный SaaS, либо тяжёлые комбайны. Nopaste — один контейнер, который можно запустить дома, на VPS или за своим reverse proxy.

- **Анонимно по умолчанию** — регистрация не нужна ни для создания, ни для чтения
- **Шаринг по ID** или по короткой ссылке Shlink (опционально)
- **Якоря строк** (`#L12`, `#L12-L20`) и копирование в один клик
- **RAW** (`/raw/<id>`) для curl, CI и редакторов
- **Подсветка синтаксиса**, а также Markdown / Mermaid
- **SQLite по умолчанию**, PostgreSQL при необходимости
- **Опциональное шифрование at-rest** (`PASTE_ENCRYPTION_KEY`)
- **Опциональные аккаунты через OIDC** — личные закладки; владельцы правят свои пасты; staff/admin — любые
- **Закладки / избранное** и список паст за 7 дней с постраничной навигацией
- **WebMCP-инструменты**: AI-агенты могут создавать и читать пасты на странице
- **Интерфейс RU/EN** по `Accept-Language`
- **Feedback** в подвале открывает предзаполненный issue в GitHub
- **Без индексации поисковиками** (`robots.txt` + `noindex`)
- Поддержка **preview / Instant View в Telegram** для страниц паст

| | Nopaste | PrivateBin | haste-server |
|---|:---:|:---:|:---:|
| Один Docker-образ | ✓ | ✓ | ✓ |
| Zero-knowledge / шифрование на клиенте | — | ✓ | — |
| Опциональное шифрование на сервере | ✓ | — | — |
| Markdown + Mermaid | ✓ | — | — |
| Якоря строк `#L12-L20` | ✓ | — | — |
| SQLite *или* Postgres | ✓ | ✓ | ✓ |
| Опциональные аккаунты (OIDC) | ✓ | — | — |
| Короткие ссылки Shlink | ✓ | — | — |
| Интерфейс RU / EN | ✓ | — | — |

## Быстрый старт

```bash
# Опубликованный образ (SQLite, данные в volume)
docker compose up -d

# Локальная сборка
docker compose -f docker-compose.local.yml up --build -d

# Приложение + Postgres
DATABASE_URL=postgresql+psycopg://nopaste:nopaste@postgres:5432/nopaste \
  docker compose --profile postgres up -d
```

Из исходников:

```bash
uv sync --frozen --extra test --group dev
PYTHONPATH=src uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Откройте http://localhost:8000

```bash
# Сырое содержимое
curl -fsSL "http://localhost:8000/raw/<paste_id>"
```

Настройка Telegram preview и Instant View: [docs/telegram-instant-view.md](docs/telegram-instant-view.md).

Образы:

| Реестр | Образ |
|--------|-------|
| Docker Hub | `nordz0r/nopaste:latest` |
| GHCR | `ghcr.io/nordz0r/nopaste:latest` |
| Rolling `main` | `nordz0r/nopaste:main` |

## Возможности

| | |
|---|---|
| Редактор | Ctrl/⌘+Enter — сохранить, подписанная cookie с недавними пастами |
| Просмотр | Подсветка строк, переключатель Markdown, кнопка RAW `</>` |
| Ссылки | Копирование URL страницы или slug Shlink; клик по номеру строки копирует `#Ln` |
| Аккаунты | Опциональный вход через OIDC · закладки · правка/удаление · список за 7 дней по страницам |
| Агенты | WebMCP-инструменты (`document.modelContext`): создание со строгим vanity slug, просмотр коротких/share-ссылок, чтение паст |
| Хранилище | SQLAlchemy + Alembic · SQLite или PostgreSQL |
| Эксплуатация | `/health/live`, `/health/ready`, rate limit в памяти, allowlist для docs |

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

## Конфигурация

Настройки читаются из окружения / `.env` (см. `.env.example`).

| Переменная | Описание |
|------------|----------|
| `APP_PORT` | Порт (по умолчанию `8000`) |
| `DEBUG` | Debug-режим FastAPI |
| `DATABASE_PATH` | Путь к SQLite, если URL/Postgres не заданы |
| `DATABASE_URL` | URL SQLAlchemy (`sqlite+…` или `postgresql+psycopg://…`) |
| `POSTGRES_*` | Отдельные учётные данные Postgres (используются, если URL пуст) |
| `PASTE_ENCRYPTION_KEY` | **Опционально.** Ключ Fernet или passphrase — шифрует тела паст при хранении |
| `COOKIE_SIGNING_SECRET` | HMAC-секрет cookie с недавними пастами. При `DEBUG=false` обязательно уникальное значение. |
| `TRUSTED_PROXY_IPS` | IP/CIDR прокси через запятую, которым разрешено передавать `X-Forwarded-For`. Пусто — заголовок игнорируется. |
| `FORWARDED_ALLOW_IPS` | Соответствующее значение uvicorn `--forwarded-allow-ips`. Держите синхронно с `TRUSTED_PROXY_IPS`. |
| `MAX_PASTE_SIZE_BYTES` | Максимальный размер пасты |
| `MAX_RECENT_PASTES` | Лимит истории в cookie |
| `RATE_LIMIT_ENABLED` / `RATE_LIMIT_PER_MINUTE` | Лимит на создание/обновление |
| `SHRINK_URL` / `SHRINK_TOKEN` | Базовый URL Shlink + API-ключ (нужны оба) |
| `PUBLIC_BASE_URL` | Базовый URL для canonical / Open Graph |
| `UI_DESIGN` | Дизайн шаблонов в `templates/designs/<name>/` |
| `GITHUB_REPO` | `owner/name` для кнопки Feedback в подвале (пусто — скрыта) |
| `DOCS_ALLOWLIST` | Список CIDR/IP для `/docs` (пусто — открыто) |
| `APP_VERSION` | Версия в интерфейсе (задают релизные образы) |
| `OIDC_DISCOVERY_URL` | **Опционально.** URL discovery-документа OIDC — включает вход |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | Учётные данные OIDC-клиента (для входа нужны оба) |
| `OIDC_SCOPES` / `OIDC_REDIRECT_URI` | Запрашиваемые scope и зарегистрированный callback URL |
| `SESSION_SECRET_KEY` | Секрет подписи cookie сессии (по умолчанию берётся `COOKIE_SIGNING_SECRET`) |
| `SESSION_COOKIE_NAME` / `SESSION_MAX_AGE_SECONDS` | Имя и время жизни cookie сессии |
| `YANDEX_METRIKA_ID` | **Опционально.** ID вашего счётчика Яндекс.Метрики (пусто — без тега аналитики) |

### Шифрование (опционально)

- **Выключено** (по умолчанию): тела паст хранятся открытым текстом.
- **Включено**: задайте `PASTE_ENCRYPTION_KEY`. Новые записи сохраняются как `enc:v1:…`. Старые незашифрованные строки остаются читаемыми.
- Если потерять ключ, зашифрованные пасты станет невозможно прочитать.

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

### Аккаунты (опционально)

Nopaste полностью работает **анонимно** — вход не нужен ни для создания, ни для чтения
пасты. Аккаунты опциональны и по умолчанию выключены.

Задайте `OIDC_DISCOVERY_URL`, `OIDC_CLIENT_ID` и `OIDC_CLIENT_SECRET`, чтобы включить
вход через любой стандартный OpenID Connect провайдер (Keycloak, Authentik, Nextcloud,
Google, …). После входа пользователи получают:

- **Закладки / избранное** — личный список сохранённых паст
- **Правку и удаление** своих паст; `role=staff` или `role=admin` могут править любую пасту
- **Список недавних паст за 7 дней** с постраничной навигацией

Анонимное владение только что созданными пастами по-прежнему работает через подписанную
cookie `user_pastes`, независимо от аккаунтов.

## Релизы

Релизы выпускаются автоматически из Conventional Commits в `main`:

| Префикс | Повышение версии |
|---------|------------------|
| `feat:` | minor |
| `fix:` / `perf:` | patch |

Процесс:

1. `release.yml` запускает [python-semantic-release](https://python-semantic-release.readthedocs.io/) — обновляет `pyproject.toml` и `CHANGELOG.md`, ставит тег `vX.Y.Z`, создаёт GitHub Release.
2. Тот же workflow публикует версионированные образы (`1.13.1`, `v1.13.1`, `1.13`, `latest`) в Docker Hub и GHCR.
3. `dockerhub.yml` дополнительно публикует rolling-теги `main` и `sha-*`. `latest` он никогда не перезаписывает.

См. [CHANGELOG.md](./CHANGELOG.md) или changelog в подвале приложения.

## Разработка

```text
src/
  main.py           маршруты FastAPI
  config.py         pydantic-settings
  auth.py           вход через OIDC + хелперы сессии
  cookies.py        кодирование/декодирование подписанных cookie
  storage/          модели, репозиторий, шифрование, engine
  i18n/             каталоги en/ru
  highlighting.py   подсветка / markdown
  list_paging.py    постраничная навигация по 7 дням
  templates/        дизайны Jinja2
  static/           CSS, шрифты, картинки, JS (app.js, webmcp.js, sw.js)
alembic/            миграции
tests/              pytest
.github/workflows/  CI, Docker, semantic-release
```

```bash
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run ruff format src tests
uv run alembic upgrade head
```

## Лицензия

[MIT](./LICENSE) © nordz0r
