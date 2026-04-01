# tests/unit/test_remediation.py
from unittest.mock import MagicMock

from backend.app.remediation.engine import RemediationEngine


def _make_signal(
    signal_type: str, status: str = "open", severity: str = "high"
) -> MagicMock:
    s = MagicMock()
    s.signal_type = signal_type
    s.status = status
    s.severity = severity
    s.entity_value = "test@example.com"
    return s


def _make_finding(
    finding_type: str, status: str = "open", severity: str = "high"
) -> MagicMock:
    f = MagicMock()
    f.finding_type = finding_type
    f.status = status
    f.severity = severity
    return f


def test_email_breached_maps_to_rotate_credentials() -> None:
    engine = RemediationEngine()
    tasks = engine.get_tasks_for_signals([_make_signal("email_breached")])
    playbooks = [t["playbook"] for t in tasks]
    assert "rotate_credentials" in playbooks


def test_deduplicates_same_playbook_across_multiple_signals() -> None:
    engine = RemediationEngine()
    signals = [
        _make_signal("email_breached"),
        _make_signal("password_reuse_detected"),
    ]
    tasks = engine.get_tasks_for_signals(signals)
    playbooks = [t["playbook"] for t in tasks]
    assert playbooks.count("rotate_credentials") == 1


def test_resolved_signals_are_excluded() -> None:
    engine = RemediationEngine()
    tasks = engine.get_tasks_for_signals(
        [_make_signal("email_breached", status="resolved")]
    )
    assert tasks == []


def test_finding_maps_to_correct_playbooks() -> None:
    engine = RemediationEngine()
    tasks = engine.get_tasks_for_findings(
        [_make_finding("high_identity_compromise_risk")]
    )
    playbooks = [t["playbook"] for t in tasks]
    assert "rotate_credentials" in playbooks
    assert "enable_mfa" in playbooks
