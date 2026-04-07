← [[MVP Master|Stage Progress]]

# Stage 5 — Correlation, Scoring, and Remediation

**Exit condition:** Open signals for a user are correlated into findings, scored, and mapped to remediation playbooks. Correlation is deterministic — identical signal inputs always produce identical finding IDs. Scores are versioned and appended, never overwritten. All tests pass.

---

## 5.1 Correlation Engine

```python
# correlation/engine.py
from abc import ABC, abstractmethod
import uuid
from backend.app.signals.models import Signal
from backend.app.correlation.models import Finding
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class BaseCorrelationRule(ABC):
    rule_name: str
    finding_type: str
    required_signal_types: list[str]

    @abstractmethod
    def evaluate(
        self, signals: list[Signal], user_id: uuid.UUID
    ) -> Finding | None:
        """
        Given open signals for one user, return a Finding if conditions
        are met, or None if they are not.
        Must be deterministic — same input always produces same finding_id.
        Must have no side effects.
        """
        ...


class CorrelationEngine:
    def __init__(self, rules: list[BaseCorrelationRule]) -> None:
        self.rules = rules

    def run(self, user_id: uuid.UUID, signals: list[Signal]) -> list[Finding]:
        open_signals = [s for s in signals if s.status == "open"]
        findings: list[Finding] = []

        for rule in self.rules:
            relevant = [
                s for s in open_signals
                if s.signal_type in rule.required_signal_types
            ]
            if not relevant:
                continue

            try:
                finding = rule.evaluate(relevant, user_id)
            except Exception as e:
                logger.error(
                    "correlation.rule_error",
                    rule=rule.rule_name,
                    error=str(e),
                )
                continue

            if finding:
                findings.append(finding)
                logger.info(
                    "correlation.finding_produced",
                    rule=rule.rule_name,
                    finding_type=finding.finding_type,
                    user_id=str(user_id),
                )

        return findings
```

---

## 5.2 First Correlation Rule

```python
# correlation/rules/identity_compromise.py
import hashlib
import uuid
from backend.app.correlation.engine import BaseCorrelationRule
from backend.app.signals.models import Signal
from backend.app.correlation.models import Finding
from backend.app.core.enums import Severity, Confidence

class HighIdentityCompromiseRisk(BaseCorrelationRule):
    rule_name = "high_identity_compromise_risk"
    finding_type = "high_identity_compromise_risk"
    required_signal_types = ["email_breached"]

    def evaluate(
        self, signals: list[Signal], user_id: uuid.UUID
    ) -> Finding | None:
        high_severity = [
            s for s in signals
            if s.signal_type == "email_breached"
            and s.severity in ("critical", "high")
        ]

        if not high_severity:
            return None

        contributing_ids = sorted([str(s.id) for s in high_severity])
        entity_ids = sorted(list({str(s.entity_id) for s in high_severity}))

        # Deterministic ID: same rule + same sorted contributing signals = same ID
        # This ensures identical signal sets always produce the same finding_id
        # enabling the upsert in FindingRepository to work correctly
        finding_id = "fnd_" + hashlib.sha256(
            f"{self.rule_name}:{','.join(contributing_ids)}".encode()
        ).hexdigest()[:24]

        return Finding(
            finding_id=finding_id,
            finding_type=self.finding_type,
            user_id=user_id,
            severity=Severity.HIGH.value,
            confidence=Confidence.HIGH.value,
            title="High identity compromise risk detected",
            explanation=(
                f"{len(high_severity)} high or critical severity breach signal(s) detected. "
                f"Your credentials are likely exposed. Immediate rotation is required."
            ),
            contributing_signal_ids=contributing_ids,
            affected_entity_ids=entity_ids,
            rule_name=self.rule_name,
        )
```

---

## 5.3 Scoring

```python
# scoring/calculators/identity_score.py
from backend.app.signals.models import Signal

SCORER_VERSION = "1.0"

SEVERITY_WEIGHTS: dict[str, int] = {
    "critical": 30,
    "high":     20,
    "medium":   10,
    "low":       5,
    "info":      1,
}

def calculate_identity_score(signals: list[Signal]) -> tuple[int, int]:
    """
    Returns (score, signal_count).
    Score: 0 (worst) to 100 (best).
    Deducts points for each open identity_security signal weighted by severity.
    Never returns below 0.
    """
    open_signals = [
        s for s in signals
        if s.status == "open" and s.category == "identity_security"
    ]
    deduction = sum(SEVERITY_WEIGHTS.get(s.severity, 0) for s in open_signals)
    return max(0, 100 - deduction), len(open_signals)
```

---

## 5.4 Remediation Engine

```python
# remediation/engine.py
from backend.app.signals.models import Signal
from backend.app.correlation.models import Finding

SIGNAL_TO_PLAYBOOK: dict[str, str] = {
    "email_breached":           "rotate_credentials",
    "mfa_missing":              "enable_mfa",
    "password_reuse_detected":  "rotate_credentials",
    "sms_mfa_only":             "upgrade_mfa",
}

FINDING_TO_PLAYBOOKS: dict[str, list[str]] = {
    "high_identity_compromise_risk": ["rotate_credentials", "enable_mfa"],
}

class RemediationEngine:
    def get_tasks_for_signals(self, signals: list[Signal]) -> list[dict]:
        tasks: list[dict] = []
        seen: set[str] = set()
        for signal in signals:
            if signal.status != "open":
                continue
            playbook = SIGNAL_TO_PLAYBOOK.get(signal.signal_type)
            if playbook and playbook not in seen:
                seen.add(playbook)
                tasks.append({
                    "playbook": playbook,
                    "trigger": signal.signal_type,
                    "priority": signal.severity,
                    "entity_value": signal.entity_value,
                })
        return tasks

    def get_tasks_for_findings(self, findings: list[Finding]) -> list[dict]:
        tasks: list[dict] = []
        seen: set[str] = set()
        for finding in findings:
            if finding.status != "open":
                continue
            for playbook in FINDING_TO_PLAYBOOKS.get(finding.finding_type, []):
                if playbook not in seen:
                    seen.add(playbook)
                    tasks.append({
                        "playbook": playbook,
                        "trigger": finding.finding_type,
                        "priority": finding.severity,
                    })
        return tasks
```

---

## 5.5 Stage 5 Tests

```python
# tests/unit/correlation/test_rules.py
import uuid
from unittest.mock import MagicMock

import pytest

from backend.app.correlation.engine import CorrelationEngine
from backend.app.correlation.rules.identity_compromise import HighIdentityCompromiseRisk
from backend.app.core.enums import Severity


def _make_signal(severity: str, signal_type: str = "email_breached", status: str = "open") -> MagicMock:
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
```

```python
# tests/unit/scoring/test_identity_score.py
from unittest.mock import MagicMock

from backend.app.scoring.calculators.identity_score import calculate_identity_score


def _make_signal(severity: str, status: str = "open", category: str = "identity_security") -> MagicMock:
    s = MagicMock()
    s.severity = severity
    s.status = status
    s.category = category
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
```

```python
# tests/unit/test_remediation.py
from unittest.mock import MagicMock

from backend.app.remediation.engine import RemediationEngine


def _make_signal(signal_type: str, status: str = "open", severity: str = "high") -> MagicMock:
    s = MagicMock()
    s.signal_type = signal_type
    s.status = status
    s.severity = severity
    s.entity_value = "test@example.com"
    return s


def _make_finding(finding_type: str, status: str = "open", severity: str = "high") -> MagicMock:
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
    tasks = engine.get_tasks_for_signals([_make_signal("email_breached", status="resolved")])
    assert tasks == []


def test_finding_maps_to_correct_playbooks() -> None:
    engine = RemediationEngine()
    tasks = engine.get_tasks_for_findings([_make_finding("high_identity_compromise_risk")])
    playbooks = [t["playbook"] for t in tasks]
    assert "rotate_credentials" in playbooks
    assert "enable_mfa" in playbooks
```

**Stage 5 Verification:**
```bash
uv run pytest tests/unit/correlation/ tests/unit/scoring/ tests/unit/test_remediation.py -v
uv run python scripts/check_imports.py
```
