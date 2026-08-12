from __future__ import annotations

from urllib.parse import quote_plus

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
        description="SQLite file path when DATABASE_URL is not set.",
    )
    DATABASE_URL: str | None = Field(
        default=None,
        description=(
            "SQLAlchemy URL. Examples: sqlite:////data/pastes.db , "
            "postgresql+psycopg://user:pass@host:5432/db"
        ),
    )
    DATABASE_BACKEND: str | None = Field(
        default=None,
        description="Optional backend hint: sqlite | postgres (validated against URL).",
    )
    POSTGRES_HOST: str | None = Field(default=None)
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_DB: str | None = Field(default=None)
    POSTGRES_USER: str | None = Field(default=None)
    POSTGRES_PASSWORD: str | None = Field(default=None)
    POSTGRES_SSLMODE: str = Field(default="disable")
    PASTE_ENCRYPTION_KEY: str | None = Field(
        default=None,
        description=(
            "Optional shared key for encrypting paste bodies at rest. "
            "When unset/empty, content is stored as plaintext. "
            "Fernet key or any passphrase (SHA-256 derived)."
        ),
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
        description="Base URL of the Shlink URL shortener (e.g. https://example.com).",
    )
    SHRINK_TOKEN: str | None = Field(
        default=None,
        description="Shlink API key used to authenticate URL shortening requests.",
    )
    PUBLIC_BASE_URL: str | None = Field(
        default=None,
        description="Public base URL for canonical/Open Graph metadata.",
    )
    UI_DESIGN: str = Field(
        default="default",
        description="Active UI design name under templates/designs/<name>/.",
    )
    GITHUB_REPO: str = Field(
        default="nordz0r/nopaste",
        description=(
            "owner/name used for the footer Feedback button "
            "(opens a prefilled GitHub issue). Empty disables the button."
        ),
    )
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enable in-memory rate limiting on mutating endpoints.",
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="Max requests per minute per IP for mutating endpoints.",
    )
    DOCS_ALLOWLIST_RAW: str = Field(
        default="",
        description="Raw DOCS_ALLOWLIST value (comma-separated).",
        alias="DOCS_ALLOWLIST",
        validation_alias="DOCS_ALLOWLIST",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DOCS_ALLOWLIST(self) -> list[str]:
        raw = (self.DOCS_ALLOWLIST_RAW or "").strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def shrink_enabled(self) -> bool:
        return bool(
            (self.SHRINK_URL or "").strip() and (self.SHRINK_TOKEN or "").strip()
        )

    def resolve_database_url(self) -> str:
        """Return SQLAlchemy database URL (sqlite or postgresql+psycopg)."""
        explicit = (self.DATABASE_URL or "").strip()
        if explicit:
            url = explicit
            if url.startswith("postgresql://") and "+psycopg" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url

        host = (self.POSTGRES_HOST or "").strip()
        dbname = (self.POSTGRES_DB or "").strip()
        user = (self.POSTGRES_USER or "").strip()
        if host and dbname and user:
            password = self.POSTGRES_PASSWORD or ""
            return (
                f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(password)}"
                f"@{host}:{self.POSTGRES_PORT}/{quote_plus(dbname)}"
                f"?sslmode={self.POSTGRES_SSLMODE}"
            )

        path = self.DATABASE_PATH or "/tmp/pastes.db"
        if path == ":memory:":
            return "sqlite+pysqlite:///:memory:"
        # Absolute path form for SQLAlchemy
        if path.startswith("/"):
            return f"sqlite+pysqlite:///{path}"
        return f"sqlite+pysqlite:///{path}"

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
