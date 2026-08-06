from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(database_url: str, *, echo: bool = False) -> Engine:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(
        database_url, echo=echo, future=True, connect_args=connect_args
    )

    if database_url.startswith("sqlite"):

        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _SessionLocal = sessionmaker(
        bind=_engine, autoflush=False, autocommit=False, future=True
    )
    return _engine


def init_db(database_url: str, *, echo: bool = False) -> Engine:
    """Create engine and apply schema (Alembic upgrade head when available).

    Always ends with metadata.create_all so tests and first boot stay reliable
    even if Alembic is unavailable or the revision graph is empty.
    """
    engine = get_engine(database_url, echo=echo)
    try:
        from pathlib import Path

        from alembic import command
        from alembic.config import Config

        here = Path(__file__).resolve()
        # Repo layout: <root>/src/storage/session.py → parents[2] = root
        # Docker layout: /app/storage/session.py → parents[1] = /app
        candidates = [
            here.parents[2] / "alembic.ini",
            here.parents[1] / "alembic.ini",
            Path("/app/alembic.ini"),
        ]
        for ini in candidates:
            if ini.is_file():
                cfg = Config(str(ini))
                cfg.set_main_option("sqlalchemy.url", database_url)
                command.upgrade(cfg, "head")
                break
    except Exception:
        # Fallback for missing alembic tree / env issues
        pass

    from storage.models import Base

    Base.metadata.create_all(bind=engine)
    return engine


def dispose_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError("Database engine is not initialized")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
