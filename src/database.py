"""Backward-compatible Database facade used by tests and legacy imports.

Prefer ``storage.create_repository`` for new code.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from storage.crypto import ContentCrypto
from storage.repository import PasteRepository
from storage.session import dispose_engine, init_db


def build_postgres_conninfo(
    *,
    host: str,
    port: int | str = 5432,
    dbname: str,
    user: str,
    password: str,
    sslmode: str = "disable",
) -> str:
    return (
        f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{quote_plus(dbname)}?sslmode={sslmode}"
    )


class Database:
    """Thin wrapper around PasteRepository for existing call sites/tests."""

    def __init__(
        self,
        db_path: str | None = None,
        *,
        database_url: str | None = None,
        conninfo: str | None = None,
        encryption_key: str | None = None,
    ) -> None:
        url = (database_url or conninfo or "").strip()
        if not url:
            path = db_path if db_path is not None else "pastes.db"
            if path == ":memory:":
                url = "sqlite+pysqlite:///:memory:"
            elif str(path).startswith("/"):
                url = f"sqlite+pysqlite:///{path}"
            else:
                url = f"sqlite+pysqlite:///{path}"
        if url.startswith("postgresql://") and "+psycopg" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)

        # Isolate engines per Database instance for tests
        dispose_engine()
        init_db(url)
        self._repo = PasteRepository(crypto=ContentCrypto(encryption_key))
        self.backend_name = "postgres" if url.startswith("postgresql") else "sqlite"
        self.db_path = db_path
        self.database_url = url

    def save_paste(
        self, paste_id: str, content: str, short_url: str | None = None,
        author_id: str | None = None,
    ) -> None:
        self._repo.save_paste(paste_id, content, short_url, author_id)

    def upsert_user(self, user_id: str, username: str, email: str | None = None, display_name: str | None = None) -> dict[str, Any]:
        return self._repo.upsert_user(user_id, username, email, display_name)

    def add_bookmark(self, user_id: str, paste_id: str) -> bool:
        return self._repo.add_bookmark(user_id, paste_id)

    def remove_bookmark(self, user_id: str, paste_id: str) -> bool:
        return self._repo.remove_bookmark(user_id, paste_id)

    def is_bookmarked(self, user_id: str, paste_id: str) -> bool:
        return self._repo.is_bookmarked(user_id, paste_id)

    def get_created_pastes(self, user_id: str) -> list[dict[str, Any]]:
        return self._repo.get_created_pastes(user_id)

    def get_bookmarked_pastes(self, user_id: str) -> list[dict[str, Any]]:
        return self._repo.get_bookmarked_pastes(user_id)

    def get_paste_ids_for_user(self, user_id: str) -> set[str]:
        return {p["id"] for p in self.get_created_pastes(user_id)} | {p["id"] for p in self.get_bookmarked_pastes(user_id)}

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._repo.get_user(user_id)

    def import_bookmarks(self, user_id: str, paste_ids: list[str]) -> int:
        return self._repo.import_bookmarks(user_id, paste_ids)

    def get_bookmark_ids(self, user_id: str) -> set[str]:
        return self._repo.get_bookmark_ids(user_id)

    def get_owned_paste_ids(self, user_id: str) -> set[str]:
        return self._repo.get_owned_paste_ids(user_id)

    def delete_bookmark(self, user_id: str, paste_id: str) -> bool:
        return self._repo.remove_bookmark(user_id, paste_id)

    def user_exists(self, user_id: str) -> bool:
        return self.get_user(user_id) is not None

    def get_authored_pastes(self, user_id: str) -> list[dict[str, Any]]:
        return self.get_created_pastes(user_id)

    def add_favorite(self, user_id: str, paste_id: str) -> bool:
        return self.add_bookmark(user_id, paste_id)

    def remove_favorite(self, user_id: str, paste_id: str) -> bool:
        return self.remove_bookmark(user_id, paste_id)

    def is_favorite(self, user_id: str, paste_id: str) -> bool:
        return self.is_bookmarked(user_id, paste_id)

    def get_user_favorites(self, user_id: str) -> list[dict[str, Any]]:
        return self.get_bookmarked_pastes(user_id)

    def get_user_created_pastes(self, user_id: str) -> list[dict[str, Any]]:
        return self.get_created_pastes(user_id)

    def toggle_bookmark(self, user_id: str, paste_id: str) -> bool:
        if self.is_bookmarked(user_id, paste_id):
            self.remove_bookmark(user_id, paste_id)
            return False
        return self.add_bookmark(user_id, paste_id)

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None:
        self._repo.update_paste_short_url(paste_id, short_url)

    def get_paste(self, paste_id: str) -> dict[str, Any] | None:
        return self._repo.get_paste(paste_id)

    def get_user_pastes(self, ids: list[str]) -> list[dict[str, Any]]:
        return self._repo.get_user_pastes(ids)

    def ping(self) -> None:
        self._repo.ping()

    def close(self) -> None:
        dispose_engine()


def create_database_from_settings(settings: Any) -> Database:
    """Create Database from application settings object."""
    encryption_key = getattr(settings, "PASTE_ENCRYPTION_KEY", None)
    if hasattr(settings, "resolve_database_url"):
        url = settings.resolve_database_url()
        return Database(database_url=url, encryption_key=encryption_key)

    database_url = (getattr(settings, "DATABASE_URL", None) or "").strip()
    if database_url:
        return Database(database_url=database_url, encryption_key=encryption_key)

    host = (getattr(settings, "POSTGRES_HOST", None) or "").strip()
    dbname = (getattr(settings, "POSTGRES_DB", None) or "").strip()
    user = (getattr(settings, "POSTGRES_USER", None) or "").strip()
    password = getattr(settings, "POSTGRES_PASSWORD", None) or ""
    if host and dbname and user:
        port = getattr(settings, "POSTGRES_PORT", 5432) or 5432
        sslmode = (getattr(settings, "POSTGRES_SSLMODE", None) or "disable").strip()
        conninfo = build_postgres_conninfo(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            sslmode=sslmode,
        )
        return Database(database_url=conninfo, encryption_key=encryption_key)

    return Database(
        getattr(settings, "DATABASE_PATH", "pastes.db"),
        encryption_key=encryption_key,
    )
