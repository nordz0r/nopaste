# ---- base-builder ----
FROM python:3.12-alpine AS base-builder

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./

# ---- prod-builder ----
FROM base-builder AS prod-builder
RUN uv sync --frozen --no-dev --no-install-project --compile-bytecode

# ---- test-builder ----
FROM base-builder AS test-builder
RUN uv sync --frozen --extra test --no-install-project --compile-bytecode

# ---- test-runtime ----
FROM python:3.12-alpine AS test-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

WORKDIR /app

COPY --from=test-builder /app/.venv .venv
COPY ./src ./src
COPY ./tests ./tests

CMD ["pytest"]

# ---- prod-runtime ----
FROM python:3.12-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/app/.venv/bin:$PATH"

RUN apk upgrade --clean-protected --no-cache && \
    apk add --no-cache dumb-init tzdata && \
    addgroup -g 1001 -S sam && \
    adduser -u 1001 -S -G sam sam && \
    mkdir -p /app /data && chown sam:sam /app /data

WORKDIR /app

COPY --from=prod-builder --chown=sam:sam /app/.venv .venv
COPY --chown=sam:sam ./src ./

USER sam
EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
