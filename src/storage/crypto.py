"""Optional at-rest encryption for paste body content.

If ``PASTE_ENCRYPTION_KEY`` is unset/empty, content is stored as plaintext.
When set, new writes use ``enc:v1:`` + Fernet ciphertext. Legacy plaintext
rows remain readable after enabling the key.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

ENC_PREFIX = "enc:v1:"


def _fernet_from_secret(secret: str) -> Fernet:
    """Build Fernet from raw secret or accept a pre-made Fernet url-safe key."""
    raw = secret.strip().encode("utf-8")
    # Try as-is (url-safe base64 32-byte key)
    try:
        return Fernet(raw)
    except (ValueError, Exception):
        pass
    # Derive 32-byte key from arbitrary passphrase
    digest = hashlib.sha256(raw).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


class ContentCrypto:
    def __init__(self, key: str | None) -> None:
        self._key = (key or "").strip() or None
        self._fernet: Fernet | None = None
        if self._key:
            self._fernet = _fernet_from_secret(self._key)

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        if not self._fernet:
            return plaintext
        token = self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
        return f"{ENC_PREFIX}{token}"

    def decrypt(self, stored: str) -> str:
        if not stored.startswith(ENC_PREFIX):
            return stored  # legacy plaintext
        if not self._fernet:
            logger.error(
                "Encrypted paste content found but PASTE_ENCRYPTION_KEY is not set"
            )
            raise ValueError("PASTE_ENCRYPTION_KEY required to read encrypted content")
        token = stored[len(ENC_PREFIX) :].encode("ascii")
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except InvalidToken as exc:
            logger.error("Failed to decrypt paste content (wrong key?)")
            raise ValueError("Failed to decrypt paste content") from exc
