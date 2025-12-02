import sqlite3
from typing import List, Optional

class Database:
    """Encapsulates SQLite operations for paste storage."""

    def __init__(self, db_path: str = "pastes.db") -> None:
        """Initialize the database connection and ensure schema exists."""
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
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

    def save_paste(self, paste_id: str, content: str) -> None:
        """Insert a new paste or replace an existing one with the same id."""
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO pastes (id, content) VALUES (?, ?)",
                (paste_id, content),
            )

    def get_paste(self, paste_id: str) -> Optional[dict]:
        """Retrieve a paste by its id."""
        cur = self.conn.execute(
            "SELECT id, content, created_at FROM pastes WHERE id = ?",
            (paste_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_user_pastes(self, ids: List[str]) -> List[dict]:
        """Retrieve multiple pastes given a list of ids."""
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        query = f"SELECT id, content, created_at FROM pastes WHERE id IN ({placeholders})"
        cur = self.conn.execute(query, ids)
        return [dict(row) for row in cur.fetchall()]