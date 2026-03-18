# backend/app/auth/utils.py
"""Auth utilities (JWT encode/decode) — implemented in Stage 2."""


def decode_access_token(token: str) -> dict[str, object]:
    """Decode and validate a JWT access token. Raises ValueError on failure."""
    raise NotImplementedError("Implemented in Stage 2")
