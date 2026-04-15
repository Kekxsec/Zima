# backend/app/modules/base/outcome.py
"""Module execution contract — return type for all module run() methods.

ModuleOutcome separates regular signals (persisted via signal_repo.upsert)
from account-discovery signals (persisted via account_repo.upsert), removing
the implicit signal-type routing that previously lived inside the runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.signals.schemas import SignalCreate


@dataclass
class ModuleOutcome:
    """Return type for all module ``run()`` methods.

    Attributes
    ----------
    signals:
        Regular findings persisted via ``signal_repo.upsert()``.
    account_signals:
        Account-discovery findings persisted via ``account_repo.upsert()``.
        These are NOT written to the signals table.
    """

    signals: list[SignalCreate] = field(default_factory=list)
    account_signals: list[SignalCreate] = field(default_factory=list)
