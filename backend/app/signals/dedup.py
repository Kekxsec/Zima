# backend/app/signals/dedup.py
import hashlib
import uuid


def compute_signal_id(
    user_id: uuid.UUID,
    signal_type: str,
    entity_id: uuid.UUID,
    source_ref: str | None = None,
) -> str:
    """
    Deterministic signal ID. Same inputs always produce the same ID.
    This means the same real-world condition detected on consecutive scans
    produces one row (upserted), not duplicate rows.

    source_ref distinguishes multiple signals of the same type on the same
    entity — e.g. two different breach names, or two different platforms.
    When omitted, falls back to one signal per (user, signal_type, asset).
    """
    key = f"{user_id}:{signal_type}:{entity_id}"
    if source_ref:
        key += f":{source_ref}"
    return "sig_" + hashlib.sha256(key.encode()).hexdigest()[:24]
