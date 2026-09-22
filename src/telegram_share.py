"""Telegram Instant View share URL helpers."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote

from config import settings

logger = logging.getLogger(__name__)


def normalize_telegram_iv_rhash(raw: str | None) -> str:
    """Return a safe Instant View rhash or empty string if unset/invalid."""
    value = (raw or "").strip()
    if not value:
        return ""
    # Telegram rhash values are short opaque hex-like tokens from the IV editor.
    if not re.fullmatch(r"[A-Za-z0-9]{8,64}", value):
        logger.warning("Ignoring invalid TELEGRAM_IV_RHASH value")
        return ""
    return value


def build_telegram_share_href(canonical_url: str, iv_rhash: str | None = None) -> str:
    """Build the Telegram share button href for a paste.

    Without TELEGRAM_IV_RHASH, share the canonical /paste/<id> URL (preview +
    public IV only after Telegram approves a domain template).

    With rhash, share a t.me/iv?url=…&rhash=… target so Instant View works for
    recipients immediately using that private template.
    """
    target = canonical_url
    rhash = normalize_telegram_iv_rhash(
        iv_rhash if iv_rhash is not None else settings.TELEGRAM_IV_RHASH
    )
    if rhash:
        target = f"https://t.me/iv?url={quote(canonical_url, safe='')}&rhash={quote(rhash, safe='')}"
    return f"https://t.me/share/url?url={quote(target, safe='/')}"
