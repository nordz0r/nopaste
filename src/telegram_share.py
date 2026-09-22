"""Telegram Instant View share URL helpers."""

from __future__ import annotations

import logging
import re
from urllib.parse import quote, urlsplit, urlunsplit

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


def resolve_telegram_public_base_url(
    telegram_base: str | None = None,
) -> str:
    """Public origin Telegram should fetch (Share / IV url=).

    Uses TELEGRAM_PUBLIC_BASE_URL when set (e.g. https://paste.bynord.dev so
    WebpageBot can reach CF while UI stays on PUBLIC_BASE_URL). Empty returns "".
    """
    raw = (
        telegram_base
        if telegram_base is not None
        else settings.TELEGRAM_PUBLIC_BASE_URL
    )
    value = (raw or "").strip().rstrip("/")
    if not value:
        return ""
    hostname = urlsplit(value).hostname
    if hostname in {None, "0.0.0.0", "::"}:
        logger.warning("Ignoring invalid TELEGRAM_PUBLIC_BASE_URL value")
        return ""
    return value


def telegram_share_paste_url(
    canonical_url: str,
    *,
    telegram_base: str | None = None,
) -> str:
    """Paste URL used inside Telegram Share / t.me/iv.

    Rewrites the origin to TELEGRAM_PUBLIC_BASE_URL when configured; otherwise
    returns canonical_url unchanged (fallback to PUBLIC_BASE_URL / request host).
    """
    base = resolve_telegram_public_base_url(telegram_base)
    if not base:
        return canonical_url
    parts = urlsplit(canonical_url)
    base_parts = urlsplit(base)
    return urlunsplit(
        (
            base_parts.scheme or parts.scheme or "https",
            base_parts.netloc,
            parts.path or "/",
            parts.query,
            "",
        )
    )


def build_telegram_share_href(
    canonical_url: str,
    iv_rhash: str | None = None,
    *,
    telegram_base: str | None = None,
) -> str:
    """Build the Telegram share button href for a paste.

    Without TELEGRAM_IV_RHASH, share the Telegram-facing paste URL (preview +
    public IV only after Telegram approves a domain template).

    With rhash, share a t.me/iv?url=…&rhash=… target so Instant View works for
    recipients immediately using that private template.

    TELEGRAM_PUBLIC_BASE_URL (when set) replaces the origin of the shared paste
    URL without changing UI canonical / PUBLIC_BASE_URL.
    """
    paste_url = telegram_share_paste_url(canonical_url, telegram_base=telegram_base)
    target = paste_url
    rhash = normalize_telegram_iv_rhash(
        iv_rhash if iv_rhash is not None else settings.TELEGRAM_IV_RHASH
    )
    if rhash:
        target = f"https://t.me/iv?url={quote(paste_url, safe='')}&rhash={quote(rhash, safe='')}"
    return f"https://t.me/share/url?url={quote(target, safe='/')}"
