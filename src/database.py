"""Paste storage backends: SQLite (local/tests) and PostgreSQL (production)."""

from __future__ import annotations

import sqlite3
import threading
from typing import Any, Protocol


class DatabaseBackend(Protocol):
    def save_paste(
        self, paste_id: str, content: str, short_url: str | None = None
    ) -> None: ...

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None: ...

    def get_paste(self, paste_id: str) -> dict | None: ...

    def get_user_pastes(self, ids: list[str]) -> list[dict]: ...

    def close(self) -> None: ...


class SqliteDatabase:
    """SQLite storage used for local development and tests."""

    def __init__(self, db_path: str = "pastes.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        with self.conn:
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS pastes (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    short_url TEXT
                )"""
            )
        try:
            self.conn.execute("ALTER TABLE pastes ADD COLUMN short_url TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def save_paste(
        self, paste_id: str, content: str, short_url: str | None = None
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO pastes (id, content, short_url) VALUES (?, ?, ?)",
                (paste_id, content, short_url),
            )

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE pastes SET short_url = ? WHERE id = ?",
                (short_url, paste_id),
            )

    def get_paste(self, paste_id: str) -> dict | None:
        cur = self.conn.execute(
            "SELECT id, content, created_at, short_url FROM pastes WHERE id = ?",
            (paste_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_user_pastes(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []

        placeholders = ",".join("?" for _ in ids)
        query = (
            f"SELECT id, content, created_at FROM pastes WHERE id IN ({placeholders})"
        )
        cur = self.conn.execute(query, ids)
        rows = [dict(row) for row in cur.fetchall()]
        order_map = {paste_id: index for index, paste_id in enumerate(ids)}
        rows.sort(key=lambda row: order_map.get(str(row["id"]), len(ids)))
        return rows

    def close(self) -> None:
        self.conn.close()


class PostgresDatabase:
    """PostgreSQL storage for durable production pastes."""

    def __init__(self, conninfo: str) -> None:
        import psycopg
        from psycopg.rows import dict_row

        self._psycopg = psycopg
        self._dict_row = dict_row
        self._conninfo = conninfo
        self._lock = threading.Lock()
        self.conn = psycopg.connect(conninfo, row_factory=dict_row, autocommit=False)
        self.init_db()

    def init_db(self) -> None:
        with self._lock:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pastes (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        short_url TEXT
                    )
                    """
                )
            self.conn.commit()

    def save_paste(
        self, paste_id: str, content: str, short_url: str | None = None
    ) -> None:
        with self._lock:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pastes (id, content, short_url)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        short_url = EXCLUDED.short_url
                    """,
                    (paste_id, content, short_url),
                )
            self.conn.commit()

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None:
        with self._lock:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE pastes SET short_url = %s WHERE id = %s",
                    (short_url, paste_id),
                )
            self.conn.commit()

    def get_paste(self, paste_id: str) -> dict | None:
        with self._lock:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT id, content, created_at, short_url FROM pastes WHERE id = %s",
                    (paste_id,),
                )
                row = cur.fetchone()
        return dict(row) if row else None

    def get_user_pastes(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []

        with self._lock:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT id, content, created_at FROM pastes WHERE id = ANY(%s)",
                    (ids,),
                )
                rows = [dict(row) for row in cur.fetchall()]
        order_map = {paste_id: index for index, paste_id in enumerate(ids)}
        rows.sort(key=lambda row: order_map.get(str(row["id"]), len(ids)))
        return rows

    def close(self) -> None:
        with self._lock:
            self.conn.close()


class Database:
    """Facade that selects SQLite or PostgreSQL from connection settings.

    Compatibility:
    - ``Database(path)`` or ``Database(db_path=path)`` → SQLite (tests/local).
    - ``Database(database_url=...)`` → PostgreSQL.
    - ``Database(conninfo=...)`` → PostgreSQL.
    """

    def __init__(
        self,
        db_path: str | None = None,
        *,
        database_url: str | None = None,
        conninfo: str | None = None,
    ) -> None:
        postgres_dsn = (database_url or conninfo or "").strip()
        if postgres_dsn:
            self._backend: DatabaseBackend = PostgresDatabase(postgres_dsn)
            self.backend_name = "postgres"
            self.db_path = None
            self.conn = self._backend.conn  # type: ignore[attr-defined]
            return

        path = db_path if db_path is not None else "pastes.db"
        self._backend = SqliteDatabase(path)
        self.backend_name = "sqlite"
        self.db_path = path
        self.conn = self._backend.conn  # type: ignore[attr-defined]

    def save_paste(
        self, paste_id: str, content: str, short_url: str | None = None
    ) -> None:
        self._backend.save_paste(paste_id, content, short_url)

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None:
        self._backend.update_paste_short_url(paste_id, short_url)

    def get_paste(self, paste_id: str) -> dict | None:
        return self._backend.get_paste(paste_id)

    def get_user_pastes(self, ids: list[str]) -> list[dict]:
        return self._backend.get_user_pastes(ids)

    def close(self) -> None:
        self._backend.close()


def build_postgres_conninfo(
    *,
    host: str,
    port: int | str = 5432,
    dbname: str,
    user: str,
    password: str,
    sslmode: str = "disable",
) -> str:
    """Build a libpq connection string from discrete settings."""
    from urllib.parse import quote_plus

    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{quote_plus(dbname)}?sslmode={sslmode}"
    )


def create_database_from_settings(settings: Any) -> Database:
    """Create Database from application settings object."""
    database_url = (getattr(settings, "DATABASE_URL", None) or "").strip()
    if database_url:
        return Database(database_url=database_url)

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
        return Database(database_url=conninfo)

    return Database(getattr(settings, "DATABASE_PATH", "pastes.db"))
