# ---- builder ----
FROM python:3.12-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --compile-bytecode

# ---- runtime ----
FROM python:3.12-alpine

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
    mkdir -p /app && chown sam:sam /app

WORKDIR /app

COPY --from=builder --chown=sam:sam /app/.venv .venv
COPY --chown=sam:sam ./src ./

USER sam
EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
