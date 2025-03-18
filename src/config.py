import os


class Settings:
    APP_PORT: int = int(os.getenv("APP_PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    # Sonar trigger
    SECRET_KEY: "postgresql://user:password@localhost/dbname"
    SECRET_KEY: "some_secret_key"


settings = Settings()
