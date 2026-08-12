"""Signed recent-pastes cookie: encode, verify, normalize."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json

from config import settings


def parse_user_paste_ids(payload: str) -> list[str]:
    try:
        loaded_ids = json.loads(payload)
    except json.JSONDecodeError:
        return []

    if not isinstance(loaded_ids, list):
        return []

    return [
        paste_id for paste_id in loaded_ids if isinstance(paste_id, str) and paste_id
    ]


def order_recent_pastes(paste_ids: list[str]) -> list[str]:
    ordered_ids: list[str] = []
    seen: set[str] = set()

    for paste_id in reversed(paste_ids):
        if paste_id in seen:
            continue
        ordered_ids.append(paste_id)
        seen.add(paste_id)

    return ordered_ids


def normalize_recent_pastes(paste_ids: list[str]) -> list[str]:
    recent_ids = order_recent_pastes(paste_ids)
    capped_recent_ids = recent_ids[: settings.MAX_RECENT_PASTES]
    return list(reversed(capped_recent_ids))


def encode_cookie_payload(payload: str) -> str:
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def decode_cookie_payload(payload: str) -> str | None:
    padding = "=" * (-len(payload) % 4)
    try:
        raw_payload = base64.urlsafe_b64decode(f"{payload}{padding}")
        return raw_payload.decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None


def sign_cookie_value(value: str) -> str:
    return hmac.new(
        settings.COOKIE_SIGNING_SECRET.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def dump_user_pastes_cookie(paste_ids: list[str]) -> str:
    normalized_ids = normalize_recent_pastes(paste_ids)
    payload = json.dumps(normalized_ids, separators=(",", ":"))
    encoded_payload = encode_cookie_payload(payload)
    signature = sign_cookie_value(encoded_payload)
    return f"{encoded_payload}.{signature}"


def verify_signed_cookie_value(cookie_value: str) -> str | None:
    encoded_payload, separator, signature = cookie_value.partition(".")
    if not separator or not signature:
        return None

    expected_signature = sign_cookie_value(encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    return decode_cookie_payload(encoded_payload)


def load_user_pastes(cookie_value: str | None) -> list[str]:
    if not cookie_value:
        return []

    if "." in cookie_value:
        payload = verify_signed_cookie_value(cookie_value)
        if payload is None:
            return []
        return parse_user_paste_ids(payload)

    return parse_user_paste_ids(cookie_value)
