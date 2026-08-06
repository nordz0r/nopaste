from __future__ import annotations

from typing import Any

from sqlalchemy import select

from storage.crypto import ContentCrypto
from storage.models import Paste
from storage.session import session_scope


class PasteRepository:
    """Application-facing paste storage API (backend-agnostic)."""

    def __init__(self, crypto: ContentCrypto | None = None) -> None:
        self._crypto = crypto or ContentCrypto(None)

    def save_paste(
        self, paste_id: str, content: str, short_url: str | None = None
    ) -> None:
        stored = self._crypto.encrypt(content)
        with session_scope() as session:
            paste = session.get(Paste, paste_id)
            if paste is None:
                session.add(Paste(id=paste_id, content=stored, short_url=short_url))
            else:
                paste.content = stored
                paste.short_url = short_url

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None:
        with session_scope() as session:
            paste = session.get(Paste, paste_id)
            if paste is None:
                return
            paste.short_url = short_url

    def get_paste(self, paste_id: str) -> dict[str, Any] | None:
        with session_scope() as session:
            paste = session.get(Paste, paste_id)
            if paste is None:
                return None
            try:
                content = self._crypto.decrypt(paste.content)
            except ValueError:
                return None
            return {
                "id": paste.id,
                "content": content,
                "created_at": paste.created_at,
                "short_url": paste.short_url,
            }

    def get_user_pastes(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        with session_scope() as session:
            rows = session.scalars(select(Paste).where(Paste.id.in_(ids))).all()
            by_id: dict[str, dict[str, Any]] = {}
            for p in rows:
                try:
                    content = self._crypto.decrypt(p.content)
                except ValueError:
                    continue
                by_id[p.id] = {
                    "id": p.id,
                    "content": content,
                    "created_at": p.created_at,
                    "short_url": p.short_url,
                }
            return [by_id[i] for i in ids if i in by_id]

    def close(self) -> None:
        return None


def create_repository(
    database_url: str,
    *,
    echo: bool = False,
    encryption_key: str | None = None,
) -> PasteRepository:
    from storage.session import init_db

    init_db(database_url, echo=echo)
    return PasteRepository(crypto=ContentCrypto(encryption_key))
