# backend/app/core/enums.py
from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SignalStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    STALE = "stale"


class FindingStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class Tier(StrEnum):
    CORE = "core"
    PLUS = "plus"
    PRO = "pro"
    BUSINESS = "business"


_TIER_ALIASES: dict[str, Tier] = {
    "shield": Tier.PLUS,
}


def parse_tier(value: str) -> Tier:
    """Parse persisted tier values, including legacy aliases."""
    alias = _TIER_ALIASES.get(value)
    if alias is not None:
        return alias
    return Tier(value)


class EntityType(StrEnum):
    EMAIL = "email"
    USERNAME = "username"
    DOMAIN = "domain"
    ACCOUNT = "account"
    DEVICE = "device"
    PHONE_NUMBER = "phone_number"
    IP = "ip"
    URL = "url"


class ScanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
