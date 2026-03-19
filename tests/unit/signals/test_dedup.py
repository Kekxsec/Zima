# tests/unit/signals/test_dedup.py
import uuid

from backend.app.signals.dedup import compute_signal_id


def test_same_inputs_always_produce_same_signal_id() -> None:
    uid = uuid.uuid4()
    eid = uuid.uuid4()
    assert compute_signal_id(uid, "email_breached", eid) == compute_signal_id(
        uid, "email_breached", eid
    )


def test_different_entity_produces_different_signal_id() -> None:
    uid = uuid.uuid4()
    assert compute_signal_id(uid, "email_breached", uuid.uuid4()) != compute_signal_id(
        uid, "email_breached", uuid.uuid4()
    )


def test_different_signal_type_produces_different_signal_id() -> None:
    uid = uuid.uuid4()
    eid = uuid.uuid4()
    assert compute_signal_id(uid, "email_breached", eid) != compute_signal_id(
        uid, "mfa_missing", eid
    )


def test_signal_id_has_expected_prefix() -> None:
    result = compute_signal_id(uuid.uuid4(), "email_breached", uuid.uuid4())
    assert result.startswith("sig_")
