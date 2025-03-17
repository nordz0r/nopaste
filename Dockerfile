# Финальный образ
#FROM gitlab.dellin.ru:5005/docker/origin/python:3.11-slim
FROM gitlab.dellin.ru:5005/biaotzovik/devops/python:3.11-slim-pytest

#ENV \
#  PIP_INDEX_URL=https://nexus.bia-tech.ru/repository/pypi.org/simple/ \
#  UV_INDEX_URL=https://nexus.bia-tech.ru/repository/pypi.org/simple/
#
#RUN sed -i 's|^URIs: http://deb.debian.org/debian$|URIs: https://nexus.bia-tech.ru/repository/debian-bookworm|' /etc/apt/sources.list.d/debian.sources && \
#    sed -i 's|^URIs: http://deb.debian.org/debian-security$|URIs: https://nexus.bia-tech.ru/repository/debian-bookworm-security|' /etc/apt/sources.list.d/debian.sources && \
#    apt-get update && \
#    apt-get install -y --no-install-recommends \
#        build-essential \
#        libssl-dev \
#        libffi-dev \
#        libpq-dev && \
#    apt-get clean && \
#    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем pyproject.toml и src/
COPY pyproject.toml ./
COPY src/ .
COPY tests ./tests

# Устанавливаем зависимости и сам проект
RUN uv pip install --system --no-cache-dir .

# Открываем порт
EXPOSE 8000

# Команда для запуска приложения
CMD ["python", "-m", "main"]