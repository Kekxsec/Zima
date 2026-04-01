# backend/app/modules/identity/account_discovery/service.py
"""
AccountDiscoveryModule — emits signals from discovered accounts.

For each unique (service_name, email_used) pair found in the mbox,
this module creates an ACCOUNT_DISCOVERED signal so the correlation engine
and scoring system can act on it.
"""

import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.db.models.email_accounts import DiscoveredAccount
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


def build_signal(
    user_id: uuid.UUID,
    asset_id: uuid.UUID,
    email_value: str,
    account: DiscoveredAccount,
) -> SignalCreate:
    """
    Build a SignalCreate for a single discovered account.
    Severity is INFO — discovery is informational, not a threat indicator.
    """
    return SignalCreate(
        signal_type="account_discovered",
        category="identity_inventory",
        entity_type=EntityType.EMAIL,
        entity_id=asset_id,
        entity_value=email_value,
        user_id=user_id,
        severity=Severity.INFO,
        confidence=Confidence.HIGH,
        source="account_discovery",
        provider="mbox_parser",
        summary=f"Account discovered at {account.display_name}",
        details=(
            f"Email address {account.email_used} appears to have an account at "
            f"{account.display_name} ({account.sender_domain}). "
            "Detected via "
            f"{account.source_type} email ({account.email_count} message(s))."
        ),
        evidence={
            "service_name": account.service_name,
            "display_name": account.display_name,
            "email_used": account.email_used,
            "source_type": account.source_type,
            "sender_domain": account.sender_domain,
            "email_count": account.email_count,
        },
        tags=["identity", "account_inventory", account.source_type],
        recommended_action=(
            "Review this account. If you no longer use it, consider deleting it "
            "or rotating its password and enabling MFA."
        ),
        source_ref=f"mbox_account_discovery:{account.service_name}",
    )
