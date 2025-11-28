# Базовый образ
FROM gitlab.dellin.ru:5005/soclist/sam/python/sam-python/python:3.12-alpine

# Переменные по умолчанию
ENV APP_HOME=/app \
    USER_NAME=sam

# Копируем файл с зависимостями
COPY --chown=$USER_NAME:$USER_NAME pyproject.toml uv.lock ./

# Создаем виртуальную среду в $APP_HOME и устанавливаем зависимости
RUN uv sync --frozen

# Копируем исходники
COPY --chown=$USER_NAME:$USER_NAME ./src $APP_HOME

# Открываем порт
EXPOSE 8000

USER $USER_NAME

# Запуск приложения
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
