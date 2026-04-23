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
    COOKIE_SIGNING_SECRET: str = Field(
        default="local-development-cookie-secret",
        description="Secret used to sign browser cookies.",
    )
    MAX_PASTE_SIZE_BYTES: int = Field(
        default=100_000,
        description="Maximum accepted paste size in UTF-8 bytes.",
    )
    MAX_RECENT_PASTES: int = Field(
        default=50, description="Maximum number of recent pastes tracked in the cookie."
    )
    SHRINK_URL: str | None = Field(
        default=None,
        description="Base URL of the Shlink URL shortener (e.g. https://gldf.ru). If set together with SHRINK_TOKEN, paste links will be shortened.",
    )
    SHRINK_TOKEN: str | None = Field(
        default=None,
        description="Shlink API key used to authenticate URL shortening requests.",
    )
    PUBLIC_BASE_URL: str | None = Field(
        default=None,
        description="Public base URL used for canonical/share metadata when the app is served behind a proxy.",
    )
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
