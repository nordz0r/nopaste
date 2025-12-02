import os
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application configuration loaded from environment variables with validation."""
    APP_PORT: int = Field(
        default=8000,
        env="APP_PORT",
        description="Port on which the FastAPI application runs."
    )
    DEBUG: bool = Field(
        default=False,
        env="DEBUG",
        description="Enable debug mode."
    )
    DATABASE_PATH: str = Field(
        default="/tmp/pastes.db",
        env="DATABASE_PATH",
        description="Path to the SQLite database file."
    )

    class Config:
        """Pydantic configuration."""
        case_sensitive = False
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
