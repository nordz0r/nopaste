FROM python:3.12-alpine

ENV APP_HOME=/app \
    USER_NAME=sam \
    UV_CACHE_DIR=/app/.cache \
    UV_NO_CACHE=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/app/.venv/bin:$PATH"

# Обновляем репозитории apk на Nexus и устанавливаем системные зависимости
RUN apk upgrade --clean-protected --no-cache && \
    apk add --no-cache \
      dumb-init \
      tzdata && \
    pip install --upgrade pip uv --root-user-action=ignore && \
    addgroup -g 1001 -S $USER_NAME && \
    adduser -u 1001 -S -G $USER_NAME $USER_NAME && \
    mkdir -p $APP_HOME && \
    chown $USER_NAME:$USER_NAME $APP_HOME && \
    rm -rf /var/cache/apk/*

# Копируем файл с зависимостями
COPY --chown=$USER_NAME:$USER_NAME pyproject.toml uv.lock ./

# Создаем виртуальную среду в $APP_HOME и устанавливаем зависимости
RUN uv sync --frozen

# Копируем исходники
COPY --chown=$USER_NAME:$USER_NAME ./src $APP_HOME

# Устанавливаем рабочую директорию
WORKDIR $APP_HOME

# Переключаемся на непривилегированного пользователя
USER $USER_NAME

# Открываем порт
EXPOSE 8000

# Базовая команда
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
