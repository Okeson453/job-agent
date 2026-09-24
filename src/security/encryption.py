"""Field-level AES-GCM encrypt/decrypt helpers.

Keyed off ENCRYPTION_KEY from the secret store. Used for any model field
marked sensitive (session tokens, stored credentials). Ciphertext is
base64-encoded so it can live in text columns.
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.security.secrets import get_secret

_NONCE_SIZE = 12  # AES-GCM standard nonce length
_KEY_SIZE = 32  # 256-bit key


@lru_cache(maxsize=1)
def _get_aesgcm() -> AESGCM:
    raw = get_secret("ENCRYPTION_KEY")
    # Accept either a 32-byte raw key or a base64-encoded 32-byte key.
    try:
        key = base64.b64decode(raw)
    except Exception:
        key = raw.encode("utf-8")
    if len(key) != _KEY_SIZE:
        raise ValueError(
            f"ENCRYPTION_KEY must decode to exactly {_KEY_SIZE} bytes "
            f"(got {len(key)}). Use a base64-encoded 32-byte key."
        )
    return AESGCM(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a UTF-8 string and return a base64-encoded ciphertext blob.

    Format: base64(nonce || ciphertext_with_tag)
    """
    if not plaintext:
        return ""
    aesgcm = _get_aesgcm()
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def decrypt(blob: str) -> str:
    """Decrypt a blob produced by encrypt(). Raises on tampering or bad key."""
    if not blob:
        return ""
    raw = base64.b64decode(blob)
    if len(raw) < _NONCE_SIZE + 16:
        raise ValueError("Ciphertext too short to be valid AES-GCM output")
    nonce = raw[:_NONCE_SIZE]
    ciphertext = raw[_NONCE_SIZE:]
    aesgcm = _get_aesgcm()
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def reset_encryption_cache() -> None:
    """Clear the cached AESGCM instance. Intended for tests only."""
    _get_aesgcm.cache_clear()
