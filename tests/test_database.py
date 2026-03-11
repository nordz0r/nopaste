from src.database import Database


def test_get_user_pastes_preserves_requested_order_and_ignores_missing_ids(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.save_paste("first", "one")
    database.save_paste("second", "two")
    database.save_paste("third", "three")

    rows = database.get_user_pastes(["third", "missing", "first"])

    assert [row["id"] for row in rows] == ["third", "first"]
    database.conn.close()
