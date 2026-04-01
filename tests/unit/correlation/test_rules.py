# tests/unit/correlation/test_rules.py
import uuid
from unittest.mock import MagicMock

from backend.app.correlation.engine import CorrelationEngine
from backend.app.correlation.rules.identity_compromise import HighIdentityCompromiseRisk


def _make_signal(
    severity: str, signal_type: str = "email_breached", status: str = "open"
) -> MagicMock:
    s = MagicMock()
    s.signal_type = signal_type
    s.severity = severity
    s.status = status
    s.id = uuid.uuid4()
    s.entity_id = uuid.uuid4()
    return s


def test_rule_fires_with_high_severity_breach_signal() -> None:
    rule = HighIdentityCompromiseRisk()
    signals = [_make_signal("high")]
    user_id = uuid.uuid4()
    finding = rule.evaluate(signals, user_id)
    assert finding is not None
    assert finding.finding_type == "high_identity_compromise_risk"


def test_rule_fires_with_critical_severity_breach_signal() -> None:
    rule = HighIdentityCompromiseRisk()
    finding = rule.evaluate([_make_signal("critical")], uuid.uuid4())
    assert finding is not None


def test_rule_does_not_fire_with_low_severity_only() -> None:
    rule = HighIdentityCompromiseRisk()
    finding = rule.evaluate([_make_signal("low")], uuid.uuid4())
    assert finding is None


def test_rule_does_not_fire_with_empty_signal_list() -> None:
    rule = HighIdentityCompromiseRisk()
    finding = rule.evaluate([], uuid.uuid4())
    assert finding is None


def test_same_input_always_produces_same_finding_id() -> None:
    """Determinism: identical signal inputs must always produce the same finding_id."""
    rule = HighIdentityCompromiseRisk()
    uid = uuid.uuid4()
    s = _make_signal("high")
    f1 = rule.evaluate([s], uid)
    f2 = rule.evaluate([s], uid)
    assert f1 is not None and f2 is not None
    assert f1.finding_id == f2.finding_id


def test_engine_skips_domains_with_no_matching_signals() -> None:
    engine = CorrelationEngine(rules=[HighIdentityCompromiseRisk()])
    uid = uuid.uuid4()
    # Only mfa_missing signals — rule requires email_breached
    signals = [_make_signal("high", signal_type="mfa_missing")]
    findings = engine.run(user_id=uid, signals=signals)
    assert findings == []


def test_engine_ignores_resolved_signals() -> None:
    engine = CorrelationEngine(rules=[HighIdentityCompromiseRisk()])
    uid = uuid.uuid4()
    resolved = _make_signal("high", status="resolved")
    findings = engine.run(user_id=uid, signals=[resolved])
    assert findings == []
