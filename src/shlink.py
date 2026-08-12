"""Optional Shlink short-URL client."""

from __future__ import annotations

import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)


class SlugTakenError(Exception):
    """Raised when Shlink rejects a custom slug as already taken."""


async def shorten_url(long_url: str, custom_slug: str | None = None) -> str | None:
    """Create a short URL via Shlink. Returns None when shrink is disabled or fails.

    Raises SlugTakenError when custom_slug is already in use (HTTP 400/409 from Shlink).
    """
    if not settings.SHRINK_URL or not settings.SHRINK_TOKEN:
        return None
    try:
        payload: dict[str, str] = {"longUrl": long_url}
        if custom_slug:
            payload["customSlug"] = custom_slug
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.SHRINK_URL.rstrip('/')}/rest/v3/short-urls",
                json=payload,
                headers={"X-Api-Key": settings.SHRINK_TOKEN},
                timeout=5.0,
            )
            status_code = getattr(response, "status_code", None)
            if status_code in {400, 409} and custom_slug:
                body_text = (getattr(response, "text", None) or "").lower()
                if (
                    status_code == 409
                    or "slug" in body_text
                    or "unique" in body_text
                    or "already" in body_text
                ):
                    raise SlugTakenError(custom_slug)
            response.raise_for_status()
            short_url = response.json().get("shortUrl", "")
            if not isinstance(short_url, str) or not short_url.startswith(
                ("https://", "http://")
            ):
                logger.warning(
                    "Shlink returned unexpected shortUrl value: %r", short_url
                )
                return None
            return short_url
    except SlugTakenError:
        raise
    except (httpx.HTTPError, KeyError, ValueError):
        logger.warning("Failed to shorten URL: %s", long_url, exc_info=True)
        return None
