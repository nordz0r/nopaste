from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables with validation."""

    APP_PORT: int = Field(
        default=8000, description="Port on which the FastAPI application runs."
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode.")
    DATABASE_PATH: str = Field(
        default="/tmp/pastes.db",
        description="Path to the SQLite database file (used when Postgres is not configured).",
    )
    DATABASE_URL: str | None = Field(
        default=None,
        description=(
            "PostgreSQL connection URL (e.g. postgresql://user:pass@host:5432/db). "
            "When set, takes precedence over DATABASE_PATH and discrete POSTGRES_* vars."
        ),
    )
    POSTGRES_HOST: str | None = Field(
        default=None,
        description="PostgreSQL host. Used with POSTGRES_DB/USER/PASSWORD when DATABASE_URL is empty.",
    )
    POSTGRES_PORT: int = Field(
        default=5432, description="PostgreSQL port for discrete connection settings."
    )
    POSTGRES_DB: str | None = Field(
        default=None,
        description="PostgreSQL database name for discrete connection settings.",
    )
    POSTGRES_USER: str | None = Field(
        default=None, description="PostgreSQL user for discrete connection settings."
    )
    POSTGRES_PASSWORD: str | None = Field(
        default=None,
        description="PostgreSQL password for discrete connection settings.",
    )
    POSTGRES_SSLMODE: str = Field(
        default="disable",
        description="libpq sslmode when building a DSN from discrete POSTGRES_* settings.",
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
