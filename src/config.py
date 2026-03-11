from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables with validation."""

    APP_PORT: int = Field(
        default=8000, description="Port on which the FastAPI application runs."
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode.")
    DATABASE_PATH: str = Field(
        default="/tmp/pastes.db", description="Path to the SQLite database file."
    )
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
