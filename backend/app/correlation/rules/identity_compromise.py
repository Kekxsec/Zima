# backend/app/correlation/rules/identity_compromise.py
import hashlib
import uuid

from backend.app.core.enums import Confidence, Severity
from backend.app.correlation.engine import BaseCorrelationRule
from backend.app.correlation.models import Finding
from backend.app.signals.models import Signal


class HighIdentityCompromiseRisk(BaseCorrelationRule):
    """Fires when breach, credential, or stealer signals indicate identity compromise.

    Severity escalation:
    - CRITICAL: stealer_log_hit present, OR plaintext password_exposed
      (critical severity)
    - HIGH: email_breached or password_exposed (hash) without stealer
    """

    rule_name = "high_identity_compromise_risk"
    finding_type = "high_identity_compromise_risk"
    required_signal_types = ["email_breached", "password_exposed", "stealer_log_hit"]

    def evaluate(self, signals: list[Signal], user_id: uuid.UUID) -> Finding | None:
        breach_signals = [s for s in signals if s.signal_type == "email_breached"]
        password_signals = [s for s in signals if s.signal_type == "password_exposed"]
        stealer_signals = [s for s in signals if s.signal_type == "stealer_log_hit"]

        # Require at least one high-impact signal to fire
        high_breach = [
            s
            for s in breach_signals
            if s.severity in {Severity.CRITICAL.value, Severity.HIGH.value}
        ]
        has_stealer = bool(stealer_signals)
        has_plaintext_password = any(
            s.severity == Severity.CRITICAL.value for s in password_signals
        )
        has_hash_password = any(
            s.severity == Severity.HIGH.value for s in password_signals
        )

        if not high_breach and not has_stealer and not password_signals:
            return None

        all_contributing = [*high_breach, *password_signals, *stealer_signals]
        contributing_ids = sorted([str(s.id) for s in all_contributing])
        entity_ids = sorted({str(s.entity_id) for s in all_contributing})

        # Deterministic finding ID
        finding_id = (
            "fnd_"
            + hashlib.sha256(
                f"{self.rule_name}:{','.join(contributing_ids)}".encode()
            ).hexdigest()[:24]
        )

        # Severity escalation
        if has_stealer:
            severity = Severity.CRITICAL
            explanation = (
                f"Stealer malware infection detected ({len(stealer_signals)} "
                "signal(s)). Device is likely compromised and all credentials "
                "have been exfiltrated. "
                "Full credential rotation and possible device wipe required."
            )
        elif has_plaintext_password:
            severity = Severity.CRITICAL
            explanation = (
                f"Plaintext password exposed ({len(password_signals)} signal(s)). "
                "Credentials are directly usable by attackers. "
                "Immediate password rotation required."
            )
        else:
            severity = Severity.HIGH
            parts = []
            if high_breach:
                parts.append(f"{len(high_breach)} breach signal(s)")
            if has_hash_password:
                parts.append(f"{len(password_signals)} password hash signal(s)")
            explanation = (
                f"{', '.join(parts)} detected. "
                "Your credentials are likely exposed. "
                "Immediate rotation is required."
            )

        return Finding(
            finding_id=finding_id,
            finding_type=self.finding_type,
            user_id=user_id,
            severity=severity.value,
            confidence=Confidence.HIGH.value,
            title="High identity compromise risk detected",
            explanation=explanation,
            contributing_signal_ids=contributing_ids,
            affected_entity_ids=entity_ids,
            rule_name=self.rule_name,
        )


class UsernameReusePattern(BaseCorrelationRule):
    """Fires when the same username is found on 3 or more distinct platforms.

    Username reuse across platforms increases the risk of credential stuffing
    and cross-platform account correlation by attackers.
    """

    rule_name = "username_reuse_pattern"
    finding_type = "username_reuse_detected"
    required_signal_types = ["username_exposure"]

    _MIN_PLATFORMS = 3

    def evaluate(self, signals: list[Signal], user_id: uuid.UUID) -> Finding | None:
        exposure_signals = [s for s in signals if s.signal_type == "username_exposure"]

        # Collect distinct platforms from evidence
        platforms: set[str] = set()
        for s in exposure_signals:
            if isinstance(s.evidence, dict):
                platform = str(s.evidence.get("platform", "")).strip()
                if platform:
                    platforms.add(platform)

        if len(platforms) < self._MIN_PLATFORMS:
            return None

        contributing_ids = sorted([str(s.id) for s in exposure_signals])
        entity_ids = sorted({str(s.entity_id) for s in exposure_signals})

        finding_id = (
            "fnd_"
            + hashlib.sha256(
                f"{self.rule_name}:{','.join(contributing_ids)}".encode()
            ).hexdigest()[:24]
        )

        return Finding(
            finding_id=finding_id,
            finding_type=self.finding_type,
            user_id=user_id,
            severity=Severity.MEDIUM.value,
            confidence=Confidence.MEDIUM.value,
            title="Username reuse detected across multiple platforms",
            explanation=(
                f"Username found on {len(platforms)} platforms: "
                f"{', '.join(sorted(platforms))}. "
                "Username reuse enables attacker cross-platform correlation "
                "and increases credential stuffing risk."
            ),
            contributing_signal_ids=contributing_ids,
            affected_entity_ids=entity_ids,
            rule_name=self.rule_name,
        )
