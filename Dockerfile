# syntax=docker/dockerfile:1.7
# Multi-stage: uv builds a venv, alpine runtime stays small.

FROM python:3.12-alpine AS base-builder
COPY --from=ghcr.io/astral-sh/uv:0.12.2 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

FROM base-builder AS prod-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --compile-bytecode

FROM base-builder AS test-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra test --no-install-project --compile-bytecode

FROM python:3.12-alpine AS test-runtime
ARG APP_VERSION=""
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION="${APP_VERSION}" \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

WORKDIR /app
COPY --from=test-builder /app/.venv .venv
COPY pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY tests ./tests

CMD ["pytest", "-q"]

FROM python:3.12-alpine AS runtime
ARG APP_VERSION=""
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION="${APP_VERSION}" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/app/.venv/bin:$PATH"

RUN apk add --no-cache dumb-init \
    && adduser -D -H -u 1000 app \
    && mkdir -p /app /data \
    && chown app:app /app /data

WORKDIR /app

COPY --from=prod-builder --chown=app:app /app/.venv .venv
COPY --chown=app:app pyproject.toml CHANGELOG.md alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app src ./

USER app
EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
