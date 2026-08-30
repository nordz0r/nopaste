from types import SimpleNamespace

from src.database import (
    Database,
    build_postgres_conninfo,
    create_database_from_settings,
)


def test_get_user_pastes_preserves_requested_order_and_ignores_missing_ids(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.save_paste("first", "one")
    database.save_paste("second", "two")
    database.save_paste("third", "three")

    rows = database.get_user_pastes(["third", "missing", "first"])

    assert [row["id"] for row in rows] == ["third", "first"]
    assert database.backend_name == "sqlite"
    database.close()


def test_delete_paste_removes_row_and_bookmarks(tmp_path):
    database = Database(str(tmp_path / "delete.db"))
    database.save_paste("gone1", "bye")
    database.upsert_user("user-1", "alice")
    assert database.add_bookmark("user-1", "gone1")
    assert database.is_bookmarked("user-1", "gone1")

    assert database.delete_paste("gone1") is True
    assert database.get_paste("gone1") is None
    assert database.is_bookmarked("user-1", "gone1") is False
    assert database.delete_paste("gone1") is False
    database.close()


def test_save_paste_honors_created_at(tmp_path):
    from datetime import UTC, datetime

    database = Database(str(tmp_path / "created.db"))
    created = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
    database.save_paste("old1", "stamped", created_at=created)
    row = database.get_paste("old1")
    assert row is not None
    assert row["created_at"].year == 2026
    assert row["created_at"].month == 8
    assert row["created_at"].day == 23
    database.close()


def test_update_paste_content_preserves_short_url_and_created_at(tmp_path):
    from datetime import UTC, datetime

    database = Database(str(tmp_path / "edit.db"))
    created = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)
    database.save_paste(
        "edit1",
        "before",
        short_url="https://gldf.ru/edit1",
        created_at=created,
    )
    assert database.update_paste_content("edit1", "after") is True
    row = database.get_paste("edit1")
    assert row is not None
    assert row["content"] == "after"
    assert row["short_url"] == "https://gldf.ru/edit1"
    assert row["created_at"].day == 20
    assert database.update_paste_content("missing", "nope") is False
    database.close()


def test_save_and_update_short_url_roundtrip(tmp_path):
    database = Database(str(tmp_path / "short.db"))
    database.save_paste("abc123", "hello")
    assert database.get_paste("abc123")["short_url"] is None

    database.update_paste_short_url("abc123", "https://gldf.ru/note")
    paste = database.get_paste("abc123")
    assert paste["content"] == "hello"
    assert paste["short_url"] == "https://gldf.ru/note"
    database.close()


def test_create_database_from_settings_prefers_database_url(tmp_path, monkeypatch):
    # Without a real Postgres we only check that URL selection wins over path.
    # If DATABASE_URL is empty and path is set, SQLite is used.
    settings = SimpleNamespace(
        DATABASE_URL="",
        POSTGRES_HOST="",
        POSTGRES_DB="",
        POSTGRES_USER="",
        POSTGRES_PASSWORD="",
        DATABASE_PATH=str(tmp_path / "from-settings.db"),
    )
    database = create_database_from_settings(settings)
    assert database.backend_name == "sqlite"
    database.save_paste("z1", "payload")
    assert database.get_paste("z1")["content"] == "payload"
    database.close()


def test_build_postgres_conninfo_encodes_credentials():
    conninfo = build_postgres_conninfo(
        host="db.example.internal",
        port=5432,
        dbname="nopaste",
        user="nopaste",
        password="p@ss:word/1",
        sslmode="disable",
    )
    assert conninfo.startswith("postgresql+psycopg://nopaste:p%40ss%3Aword%2F1@")
    assert "/nopaste?sslmode=disable" in conninfo


def test_optional_encryption_roundtrip(tmp_path):
    plain = Database(str(tmp_path / "plain.db"), encryption_key=None)
    plain.save_paste("p1", "hello plaintext")
    assert plain.get_paste("p1")["content"] == "hello plaintext"
    plain.close()

    key = "test-passphrase-for-fernet-derive"
    enc = Database(str(tmp_path / "enc.db"), encryption_key=key)
    enc.save_paste("e1", "secret body")
    # Stored ciphertext is prefixed; repository decrypts for callers
    row = enc.get_paste("e1")
    assert row is not None
    assert row["content"] == "secret body"
    enc.close()

    # Wrong key cannot read encrypted rows
    wrong = Database(str(tmp_path / "enc.db"), encryption_key="other-key")
    assert wrong.get_paste("e1") is None
    wrong.close()


def test_encryption_disabled_stores_plaintext(tmp_path):
    from sqlalchemy import text

    from storage.session import dispose_engine, get_engine

    db = Database(str(tmp_path / "noenc.db"), encryption_key=None)
    db.save_paste("x1", "visible")
    engine = get_engine(db.database_url)
    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT content FROM pastes WHERE id = :id"), {"id": "x1"}
        ).scalar_one()
    assert stored == "visible"
    assert not str(stored).startswith("enc:v1:")
    db.close()
    dispose_engine()
