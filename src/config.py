from pydantic import Field, computed_field
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
    UI_DESIGN: str = Field(
        default="default",
        description="Active UI design name. Designs provide a base.html under src/templates/designs/<name>/ .",
    )

    # Stored as raw string so that pydantic-settings never attempts to json-decode
    # the value from .env (empty strings and "1.2.3.4,10.0.0.0/8" would otherwise break).
    DOCS_ALLOWLIST_RAW: str = Field(
        default="",
        description="Raw DOCS_ALLOWLIST value (comma-separated). See DOCS_ALLOWLIST computed property.",
        alias="DOCS_ALLOWLIST",
        validation_alias="DOCS_ALLOWLIST",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DOCS_ALLOWLIST(self) -> list[str]:
        """Final parsed allowlist for docs access control."""
        raw = (self.DOCS_ALLOWLIST_RAW or "").strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
