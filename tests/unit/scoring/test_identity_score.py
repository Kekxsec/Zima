# tests/unit/scoring/test_identity_score.py
from unittest.mock import MagicMock

from backend.app.scoring.calculators.identity_score import calculate_identity_score


def _make_signal(
    severity: str, status: str = "open", category: str = "identity_security"
) -> MagicMock:
    s = MagicMock()
    s.severity = severity
    s.status = status
    s.category = category
    s.signal_type = "email_breached"
    return s


def test_score_is_100_with_no_signals() -> None:
    score, count = calculate_identity_score([])
    assert score == 100
    assert count == 0


def test_critical_signal_deducts_30() -> None:
    score, _ = calculate_identity_score([_make_signal("critical")])
    assert score == 70


def test_high_signal_deducts_20() -> None:
    score, _ = calculate_identity_score([_make_signal("high")])
    assert score == 80


def test_score_never_goes_below_zero() -> None:
    signals = [_make_signal("critical")] * 10
    score, _ = calculate_identity_score(signals)
    assert score == 0


def test_only_open_signals_are_counted() -> None:
    signals = [
        _make_signal("critical", status="open"),
        _make_signal("critical", status="resolved"),
        _make_signal("critical", status="suppressed"),
    ]
    score, count = calculate_identity_score(signals)
    assert score == 70  # Only one critical deducted
    assert count == 1


def test_only_identity_category_signals_counted() -> None:
    signals = [
        _make_signal("critical", category="identity_security"),
        _make_signal("critical", category="device_security"),
    ]
    score, count = calculate_identity_score(signals)
    assert score == 70  # Only identity_security deducted
    assert count == 1


def test_inventory_signal_types_do_not_count_even_if_misclassified() -> None:
    signal = _make_signal("critical", category="identity_security")
    signal.signal_type = "username_exposure"

    score, count = calculate_identity_score([signal])

    assert score == 100
    assert count == 0
