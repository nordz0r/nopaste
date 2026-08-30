"""Small, stateless OIDC helpers for the optional Nextcloud login."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from config import settings


def _secret() -> bytes:
    return (settings.SESSION_SECRET_KEY or settings.COOKIE_SIGNING_SECRET).encode()


def _sign(value: str) -> str:
    return hmac.new(_secret(), value.encode(), hashlib.sha256).hexdigest()


def encode_payload(payload: dict[str, Any]) -> str:
    raw = (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )
    return f"{raw}.{_sign(raw)}"


def decode_payload(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    raw, dot, signature = value.partition(".")
    if not dot or not hmac.compare_digest(signature, _sign(raw)):
        return None
    try:
        data = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        payload = json.loads(data)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def make_session(user: dict[str, Any]) -> str:
    return encode_payload(
        {**user, "exp": int(time.time()) + settings.SESSION_MAX_AGE_SECONDS}
    )


def load_session(value: str | None) -> dict[str, Any] | None:
    payload = decode_payload(value)
    if not payload or _is_expired(payload) or not payload.get("sub"):
        return None
    return payload


def make_state(return_to: str, verifier: str) -> str:
    safe_return_to = (
        return_to
        if return_to.startswith("/") and not return_to.startswith("//")
        else "/"
    )
    return encode_payload(
        {
            "return_to": safe_return_to,
            "verifier": verifier,
            "exp": int(time.time()) + 600,
        }
    )


def load_state(value: str | None) -> dict[str, Any] | None:
    """Load a signed, unexpired OIDC state payload.

    OIDC state is not a user session and intentionally has no ``sub`` claim.
    """
    payload = decode_payload(value)
    if not payload or _is_expired(payload):
        return None
    verifier = payload.get("verifier")
    if not isinstance(verifier, str) or not verifier:
        return None
    return payload


def _is_expired(payload: dict[str, Any]) -> bool:
    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return True
    return expires_at < int(time.time())


def oidc_enabled() -> bool:
    return bool(settings.OIDC_CLIENT_ID and settings.OIDC_CLIENT_SECRET)


async def discovery() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(settings.OIDC_DISCOVERY_URL)
        response.raise_for_status()
        return response.json()


def pkce_verifier() -> str:
    return secrets.token_urlsafe(48)


def pkce_challenge(verifier: str) -> str:
    return (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )


async def exchange_code(code: str, verifier: str, redirect_uri: str) -> dict[str, Any]:
    metadata = await discovery()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            metadata["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.OIDC_CLIENT_ID,
                "client_secret": settings.OIDC_CLIENT_SECRET,
                "code_verifier": verifier,
            },
        )
        response.raise_for_status()
        return response.json()


async def userinfo(access_token: str) -> dict[str, Any]:
    metadata = await discovery()
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            metadata["userinfo_endpoint"],
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def authorization_url(
    metadata: dict[str, Any], state: str, challenge: str, redirect_uri: str
) -> str:
    return (
        metadata["authorization_endpoint"]
        + "?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": settings.OIDC_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "scope": settings.OIDC_SCOPES,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
    )
