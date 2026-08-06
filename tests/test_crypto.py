from storage.crypto import ENC_PREFIX, ContentCrypto


def test_crypto_disabled_is_passthrough():
    crypto = ContentCrypto(None)
    assert crypto.enabled is False
    assert crypto.encrypt("hello") == "hello"
    assert crypto.decrypt("hello") == "hello"


def test_crypto_empty_key_is_disabled():
    crypto = ContentCrypto("   ")
    assert crypto.enabled is False
    assert crypto.encrypt("x") == "x"


def test_crypto_roundtrip_with_passphrase():
    crypto = ContentCrypto("my-shared-secret")
    assert crypto.enabled is True
    stored = crypto.encrypt("paste body\nline2")
    assert stored.startswith(ENC_PREFIX)
    assert crypto.decrypt(stored) == "paste body\nline2"


def test_crypto_reads_legacy_plaintext_when_key_set():
    crypto = ContentCrypto("key")
    assert crypto.decrypt("legacy plaintext paste") == "legacy plaintext paste"


def test_crypto_missing_key_cannot_decrypt_ciphertext():
    encrypted = ContentCrypto("key-a").encrypt("secret")
    plain = ContentCrypto(None)
    try:
        plain.decrypt(encrypted)
        raised = False
    except ValueError:
        raised = True
    assert raised
