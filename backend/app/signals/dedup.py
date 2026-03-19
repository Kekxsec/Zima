# backend/app/signals/dedup.py
import hashlib
import uuid


def compute_signal_id(
    user_id: uuid.UUID,
    signal_type: str,
    entity_id: uuid.UUID,
) -> str:
    """
    Deterministic signal ID. Same three inputs always produce the same ID.
    This means the same real-world condition detected on consecutive scans
    produces one row (upserted), not duplicate rows.
    """
    key = f"{user_id}:{signal_type}:{entity_id}"
    return "sig_" + hashlib.sha256(key.encode()).hexdigest()[:24]
