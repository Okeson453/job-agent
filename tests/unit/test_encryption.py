"""Unit tests for field-level encryption."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "t")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")
os.environ.setdefault("ENCRYPTION_KEY", "QUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUE=")

from src.security.encryption import decrypt, encrypt, reset_encryption_cache


class TestEncryption:
    def setup_method(self) -> None:
        reset_encryption_cache()

    def test_roundtrip(self) -> None:
        plain = "sensitive-session-token-abc123"
        blob = encrypt(plain)
        assert blob != plain
        assert decrypt(blob) == plain

    def test_empty(self) -> None:
        assert encrypt("") == ""
        assert decrypt("") == ""

    def test_different_ciphertexts(self) -> None:
        # Random nonce → different blobs for same plaintext.
        a = encrypt("same")
        b = encrypt("same")
        assert a != b
        assert decrypt(a) == decrypt(b) == "same"

    def test_tamper_raises(self) -> None:
        blob = encrypt("secret")
        # Flip a character in the middle of the base64 blob.
        chars = list(blob)
        mid = len(chars) // 2
        chars[mid] = "A" if chars[mid] != "A" else "B"
        tampered = "".join(chars)
        import pytest

        with pytest.raises(Exception):
            decrypt(tampered)
