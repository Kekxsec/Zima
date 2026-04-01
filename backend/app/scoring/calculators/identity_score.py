# backend/app/scoring/calculators/identity_score.py
from backend.app.signals.models import Signal

SCORER_VERSION = "1.0"

SEVERITY_WEIGHTS: dict[str, int] = {
    "critical": 30,
    "high": 20,
    "medium": 10,
    "low": 5,
    "info": 1,
}

INVENTORY_SIGNAL_TYPES: frozenset[str] = frozenset(
    {"account_discovered", "username_exposure"}
)


def calculate_identity_score(signals: list[Signal]) -> tuple[int, int]:
    """
    Returns (score, signal_count).
    Score: 0 (worst) to 100 (best).
    Deducts points for each open identity_security signal weighted by severity.
    Never returns below 0.
    """
    open_signals = [
        s
        for s in signals
        if s.status == "open"
        and s.category == "identity_security"
        and s.signal_type not in INVENTORY_SIGNAL_TYPES
    ]
    deduction = sum(SEVERITY_WEIGHTS.get(s.severity, 0) for s in open_signals)
    return max(0, 100 - deduction), len(open_signals)
