# backend/app/email_accounts/priority.py
"""
Priority scoring for discovered accounts.

Pure function — no I/O. Takes category + source_type + breach flag,
returns an AccountPriority with tier (1–4), a label, a human-readable
reason, and a sort_key for ordering exports.

Priority tiers
--------------
P1 CRITICAL  — Financial/payment account AND found in a breach.
               Reset credentials immediately.
P2 HIGH      — Financial account (not breached) OR any breached account
               OR card used (receipt) OR security alert received.
               Reset within the week.
P3 MEDIUM    — Account confirmed in inbox (account_confirmation /
               password_reset) but not financial and not breached.
               Review and secure.
P4 LOW       — Newsletter, unclassified, or other weak signals.
               Audit / decide to delete.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.db.models.email_accounts import DiscoveredAccountSourceType

# Categories where payment details are very likely stored
_FINANCIAL_CATEGORIES: frozenset[str] = frozenset(
    {"finance", "ecommerce", "travel", "food"}
)

_HIGH_SIGNAL_SOURCES: frozenset[str] = frozenset(
    {
        DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION,
        DiscoveredAccountSourceType.PASSWORD_RESET,
        DiscoveredAccountSourceType.SECURITY_ALERT,
    }
)


@dataclass(frozen=True)
class AccountPriority:
    tier: int  # 1 = highest
    label: str  # "P1 CRITICAL"
    reason: str  # one-line explanation shown in export notes
    sort_key: tuple[int, int]  # primary sort for export


def score(
    category: str | None,
    source_type: str,
    is_breached: bool,
) -> AccountPriority:
    """
    Score a single discovered account.

    Args:
        category:    Service registry category (e.g. "finance", "developer").
                     None for unrecognised domains.
        source_type: DiscoveredAccountSourceType value from mbox classification.
        is_breached: True if the user's email has at least one open breach signal
                     attributed to this same email address.
    """
    is_financial = (category or "") in _FINANCIAL_CATEGORIES
    is_receipt = source_type == DiscoveredAccountSourceType.RECEIPT
    is_security_alert = source_type == DiscoveredAccountSourceType.SECURITY_ALERT
    is_high_signal = source_type in _HIGH_SIGNAL_SOURCES

    # P1 — worst case: money + breach
    if is_financial and is_breached:
        return AccountPriority(
            tier=1,
            label="P1 CRITICAL",
            reason=(
                "Financial/payment account with email found in a breach — "
                "reset credentials immediately and check for unauthorised transactions."
            ),
            sort_key=(1, 0),
        )

    # P2 — financial (not breached) or breached (any category)
    if is_financial:
        return AccountPriority(
            tier=2,
            label="P2 HIGH",
            reason="Financial or payment account — ensure a strong, unique password.",
            sort_key=(2, 0),
        )

    if is_breached:
        return AccountPriority(
            tier=2,
            label="P2 HIGH",
            reason=(
                "Email found in a data breach associated with this account — "
                "rotate password and enable MFA."
            ),
            sort_key=(2, 1),
        )

    # Card was used — payment details on file even if not "finance" category
    if is_receipt:
        return AccountPriority(
            tier=2,
            label="P2 HIGH",
            reason=(
                "Payment receipt found — card details likely stored. Verify and "
                "secure."
            ),
            sort_key=(2, 2),
        )

    # Suspicious access attempt logged
    if is_security_alert:
        return AccountPriority(
            tier=2,
            label="P2 HIGH",
            reason="Security alert received for this account — review recent activity.",
            sort_key=(2, 3),
        )

    # P3 — confirmed account, lower risk
    if is_high_signal:
        return AccountPriority(
            tier=3,
            label="P3 MEDIUM",
            reason=(
                "Account confirmed in inbox — review, ensure unique password, "
                "enable MFA."
            ),
            sort_key=(3, 0),
        )

    # P4 — weak signal only
    return AccountPriority(
        tier=4,
        label="P4 LOW",
        reason="Low-signal relationship (newsletter or unclassified). Audit or delete.",
        sort_key=(4, 0),
    )
