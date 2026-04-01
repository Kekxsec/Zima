# backend/app/correlation/engine.py
import uuid
from abc import ABC, abstractmethod

from backend.app.core.logging import get_logger
from backend.app.correlation.models import Finding
from backend.app.signals.models import Signal

logger = get_logger(__name__)


class BaseCorrelationRule(ABC):
    rule_name: str
    finding_type: str
    required_signal_types: list[str]

    @abstractmethod
    def evaluate(self, signals: list[Signal], user_id: uuid.UUID) -> Finding | None:
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
                s for s in open_signals if s.signal_type in rule.required_signal_types
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
