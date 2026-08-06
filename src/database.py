import sqlite3


class Database:
    """Encapsulates SQLite operations for paste storage."""

    def __init__(self, db_path: str = "pastes.db") -> None:
        """Initialize the database connection and ensure schema exists."""
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        """Create the pastes table if it does not already exist."""
        with self.conn:
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS pastes (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        try:
            self.conn.execute("ALTER TABLE pastes ADD COLUMN short_url TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    def save_paste(
        self, paste_id: str, content: str, short_url: str | None = None
    ) -> None:
        """Insert a new paste or replace an existing one with the same id."""
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO pastes (id, content, short_url) VALUES (?, ?, ?)",
                (paste_id, content, short_url),
            )

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None:
        """Update short_url for an existing paste."""
        with self.conn:
            self.conn.execute(
                "UPDATE pastes SET short_url = ? WHERE id = ?",
                (short_url, paste_id),
            )

    def get_paste(self, paste_id: str) -> dict | None:
        """Retrieve a paste by its id."""
        cur = self.conn.execute(
            "SELECT id, content, created_at, short_url FROM pastes WHERE id = ?",
            (paste_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_user_pastes(self, ids: list[str]) -> list[dict]:
        """Retrieve multiple pastes given a list of ids."""
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
