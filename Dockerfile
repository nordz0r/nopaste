# Финальный образ
FROM gitlab.dellin.ru:5005/docker/origin/python:3.11-slim

ENV APP_HOME=/app \
    USER_NAME=sam \
    PIP_INDEX_URL=https://nexus.bia-tech.ru/repository/pypi.org/simple/ \
    UV_INDEX_URL=https://nexus.bia-tech.ru/repository/pypi.org/simple/ \
    UV_CACHE_DIR=/app/.cache \
    UV_NO_CACHE=1 \
    UV_SYSTEM_PYTHON=1

RUN sed -i 's|^URIs: http://deb.debian.org/debian$|URIs: https://nexus.bia-tech.ru/repository/debian-bookworm|' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|^URIs: http://deb.debian.org/debian-security$|URIs: https://nexus.bia-tech.ru/repository/debian-bookworm-security|' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
        libffi-dev \
        libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости Python от имени root
RUN pip install --no-cache-dir uv

# Создаем группу и пользователя с системными правами
RUN addgroup --system $USER_NAME && adduser --system --ingroup $USER_NAME $USER_NAME

WORKDIR $APP_HOME

RUN chown -R $USER_NAME:$USER_NAME $APP_HOME

# Копируем pyproject.toml
COPY --chown=$USER_NAME:$USER_NAME pyproject.toml .

# Создаем виртуальную среду в $APP_HOME и устанавливаем зависимости
RUN uv pip install -r pyproject.toml

# Копируем исходники
COPY --chown=$USER_NAME:$USER_NAME src .

# Переключаемся на пользователя sam один раз
USER $USER_NAME

# Открываем порт
EXPOSE 8000

# Команда для запуска приложения с использованием интерпретатора из .venv
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
