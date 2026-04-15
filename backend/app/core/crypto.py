# backend/app/core/crypto.py
"""
Application-level envelope encryption for sensitive fields.

Provides encrypt_field() / decrypt_field() for column-level encryption and
blind_index() for equality lookups on encrypted data.

Encryption scheme:
    - AES-256-GCM (authenticated encryption)
    - 12-byte random nonce per record
    - Master key loaded from settings (hex-encoded, 32 bytes)
    - Stored format: base64(nonce ‖ ciphertext ‖ tag)

Blind index scheme:
    - HMAC-SHA256 keyed with a separate derivation of the master key
    - Output: hex-encoded 32-byte digest
    - Suitable for equality checks, NOT range queries

Usage:
    from backend.app.core.crypto import encrypt_field, decrypt_field, blind_index

    encrypted = encrypt_field("user@example.com")
    plaintext = decrypt_field(encrypted)
    index     = blind_index("user@example.com")
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.app.core.logging import get_logger

logger = get_logger(__name__)

_NONCE_LENGTH = 12  # 96-bit nonce — recommended for AES-GCM
_KEY_LENGTH = 32  # 256-bit key
_BLIND_INDEX_CONTEXT = b"zima-blind-index-v1"


class CryptoError(Exception):
    """Raised when encryption or decryption fails."""


@lru_cache(maxsize=1)
def _get_master_key() -> bytes:
    """Load and validate the master encryption key from settings.

    Returns raw 32-byte key. Raises CryptoError if missing or invalid.
    """
    from backend.app.core.config import settings

    raw = settings.field_encryption_key
    if raw is None:
        raise CryptoError(
            "FIELD_ENCRYPTION_KEY is not configured. "
            'Generate with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    key_hex = raw.get_secret_value()
    try:
        key_bytes = bytes.fromhex(key_hex)
    except ValueError as exc:
        raise CryptoError(
            "FIELD_ENCRYPTION_KEY must be a valid hex string (64 hex chars = 32 bytes)"
        ) from exc
    if len(key_bytes) != _KEY_LENGTH:
        raise CryptoError(
            f"FIELD_ENCRYPTION_KEY must be exactly {_KEY_LENGTH} bytes "
            f"({_KEY_LENGTH * 2} hex chars), got {len(key_bytes)}"
        )
    return key_bytes


def _derive_blind_key(master: bytes) -> bytes:
    """Derive a separate key for blind indexes using HKDF-like construction."""
    return hashlib.sha256(_BLIND_INDEX_CONTEXT + master).digest()


def encrypt_field(plaintext: str) -> str:
    """Encrypt a string field. Returns base64-encoded nonce+ciphertext+tag."""
    if not plaintext:
        return ""
    master = _get_master_key()
    nonce = os.urandom(_NONCE_LENGTH)
    aesgcm = AESGCM(master)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a base64-encoded field. Returns the original plaintext."""
    if not ciphertext:
        return ""
    master = _get_master_key()
    raw = base64.b64decode(ciphertext)
    if len(raw) < _NONCE_LENGTH + 1:
        raise CryptoError("Ciphertext too short to contain nonce + data")
    nonce = raw[:_NONCE_LENGTH]
    ct = raw[_NONCE_LENGTH:]
    aesgcm = AESGCM(master)
    try:
        plaintext_bytes = aesgcm.decrypt(nonce, ct, None)
    except Exception as exc:
        raise CryptoError("Decryption failed — wrong key or corrupted data") from exc
    return str(plaintext_bytes.decode("utf-8"))


def blind_index(value: str) -> str:
    """Compute a deterministic blind index for equality lookups.

    Returns a 64-char hex string (HMAC-SHA256).
    """
    if not value:
        return ""
    master = _get_master_key()
    blind_key = _derive_blind_key(master)
    return hmac.new(blind_key, value.encode("utf-8"), hashlib.sha256).hexdigest()


def is_encryption_configured() -> bool:
    """Check whether field encryption is available without raising."""
    from backend.app.core.config import settings

    if settings.field_encryption_key is None:
        return False
    try:
        _get_master_key()
        return True
    except CryptoError:
        return False
