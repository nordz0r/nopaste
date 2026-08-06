# syntax=docker/dockerfile:1.7
# Multi-stage build: uv installs into a venv, slim alpine runtime.

ARG UV_VERSION=0.12.2
ARG PYTHON_IMAGE=python:3.12-alpine

# ---- base-builder: uv + lockfiles (shared cache layer) ----
FROM ${PYTHON_IMAGE} AS base-builder
ARG UV_VERSION
COPY --from=ghcr.io/astral-sh/uv:${UV_VERSION} /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

# ---- prod-builder ----
FROM base-builder AS prod-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --compile-bytecode

# ---- test-builder ----
FROM base-builder AS test-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra test --no-install-project --compile-bytecode

# ---- test-runtime ----
FROM ${PYTHON_IMAGE} AS test-runtime
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

# ---- prod-runtime ----
FROM ${PYTHON_IMAGE} AS runtime
ARG APP_VERSION=""
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION="${APP_VERSION}" \
    TZ=Europe/Moscow \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/app/.venv/bin:$PATH"

RUN apk upgrade --clean-protected --no-cache \
    && apk add --no-cache dumb-init tzdata \
    && addgroup -g 1001 -S sam \
    && adduser -u 1001 -S -G sam sam \
    && mkdir -p /app /data \
    && chown sam:sam /app /data

WORKDIR /app

COPY --from=prod-builder --chown=sam:sam /app/.venv .venv
COPY --chown=sam:sam pyproject.toml CHANGELOG.md alembic.ini ./
COPY --chown=sam:sam alembic ./alembic
COPY --chown=sam:sam src ./

USER sam
EXPOSE 8000

# K8s/compose: SIGTERM + zombie reaping
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
