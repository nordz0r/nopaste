from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, text

from storage.crypto import ContentCrypto
from storage.models import Bookmark, Paste, User
from storage.session import session_scope


class PasteRepository:
    """Application-facing paste storage API (backend-agnostic)."""

    def __init__(self, crypto: ContentCrypto | None = None) -> None:
        self._crypto = crypto or ContentCrypto(None)

    def save_paste(self, paste_id: str, content: str, short_url: str | None = None, author_id: str | None = None) -> None:
        stored = self._crypto.encrypt(content)
        with session_scope() as session:
            paste = session.get(Paste, paste_id)
            if paste is None:
                session.add(Paste(id=paste_id, content=stored, short_url=short_url, author_id=author_id))
            else:
                paste.content, paste.short_url, paste.author_id = stored, short_url, author_id

    def update_paste_short_url(self, paste_id: str, short_url: str) -> None:
        with session_scope() as session:
            paste = session.get(Paste, paste_id)
            if paste is not None:
                paste.short_url = short_url

    def upsert_user(self, user_id: str, username: str, email: str | None = None, display_name: str | None = None) -> dict[str, Any]:
        with session_scope() as session:
            user = session.get(User, user_id)
            if user is None:
                user = User(id=user_id, username=username, email=email, display_name=display_name)
                session.add(user)
            else:
                user.username, user.email, user.display_name = username, email, display_name
                user.last_login_at = datetime.now(UTC)
            return {"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name}

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with session_scope() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            return {"id": user.id, "username": user.username, "email": user.email, "display_name": user.display_name}

    def get_bookmark_ids(self, user_id: str) -> set[str]:
        with session_scope() as session:
            return set(session.scalars(select(Bookmark.paste_id).where(Bookmark.user_id == user_id)).all())

    def get_owned_paste_ids(self, user_id: str) -> set[str]:
        with session_scope() as session:
            return set(session.scalars(select(Paste.id).where(Paste.author_id == user_id)).all())

    def import_bookmarks(self, user_id: str, paste_ids: list[str]) -> int:
        added = 0
        with session_scope() as session:
            existing = set(session.scalars(select(Bookmark.paste_id).where(Bookmark.user_id == user_id)).all())
            valid = set(session.scalars(select(Paste.id).where(Paste.id.in_(paste_ids))).all()) if paste_ids else set()
            for paste_id in valid - existing:
                session.add(Bookmark(user_id=user_id, paste_id=paste_id))
                added += 1
        return added

    def add_bookmark(self, user_id: str, paste_id: str) -> bool:
        with session_scope() as session:
            if session.get(Paste, paste_id) is None or session.get(Bookmark, (user_id, paste_id)) is not None:
                return False
            session.add(Bookmark(user_id=user_id, paste_id=paste_id))
            return True

    def remove_bookmark(self, user_id: str, paste_id: str) -> bool:
        with session_scope() as session:
            result = session.execute(delete(Bookmark).where(Bookmark.user_id == user_id, Bookmark.paste_id == paste_id))
            return bool(result.rowcount)

    def is_bookmarked(self, user_id: str, paste_id: str) -> bool:
        with session_scope() as session:
            return session.get(Bookmark, (user_id, paste_id)) is not None

    def _record(self, p: Paste) -> dict[str, Any] | None:
        try:
            content = self._crypto.decrypt(p.content)
        except ValueError:
            return None
        return {"id": p.id, "content": content, "created_at": p.created_at, "short_url": p.short_url, "author_id": p.author_id}

    def get_paste(self, paste_id: str) -> dict[str, Any] | None:
        with session_scope() as session:
            paste = session.get(Paste, paste_id)
            return self._record(paste) if paste else None

    def get_user_pastes(self, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        with session_scope() as session:
            rows = session.scalars(select(Paste).where(Paste.id.in_(ids))).all()
            by_id = {p.id: record for p in rows if (record := self._record(p)) is not None}
            return [by_id[i] for i in ids if i in by_id]

    def get_created_pastes(self, user_id: str) -> list[dict[str, Any]]:
        with session_scope() as session:
            rows = session.scalars(select(Paste).where(Paste.author_id == user_id).order_by(Paste.created_at.desc())).all()
            return [record for p in rows if (record := self._record(p)) is not None]

    def get_bookmarked_pastes(self, user_id: str) -> list[dict[str, Any]]:
        with session_scope() as session:
            rows = session.scalars(select(Paste).join(Bookmark, Bookmark.paste_id == Paste.id).where(Bookmark.user_id == user_id).order_by(Bookmark.created_at.desc())).all()
            return [record for p in rows if (record := self._record(p)) is not None]

    def ping(self) -> None:
        with session_scope() as session:
            session.execute(text("SELECT 1"))

    def close(self) -> None:
        return None


def create_repository(database_url: str, *, echo: bool = False, encryption_key: str | None = None) -> PasteRepository:
    from storage.session import init_db
    init_db(database_url, echo=echo)
    return PasteRepository(crypto=ContentCrypto(encryption_key))
