import os


class Settings:
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    # Добавьте другие переменные конфигурации по необходимости


settings = Settings()
