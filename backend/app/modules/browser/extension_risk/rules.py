# backend/app/modules/browser/extension_risk/rules.py
from backend.app.core.enums import Severity


def crxcavator_severity(total_risk: int) -> Severity:
    """Map CRXcavator total risk score to Zima severity.

    Thresholds from CRXcavator documentation:
      ≤ 377 → LOW
      378–478 → MEDIUM
      > 478 → HIGH
    """
    if total_risk <= 377:
        return Severity.LOW
    if total_risk <= 478:
        return Severity.MEDIUM
    return Severity.HIGH
