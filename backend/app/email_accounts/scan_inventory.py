import re
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from backend.app.core.logging import get_logger
from backend.app.db.models.email_accounts import DiscoveredAccountSourceType
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.signals.schemas import SignalCreate

SCAN_DISCOVERY_UPLOAD_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
logger = get_logger(__name__)

_PROVIDER_TO_SOURCE_TYPE = {
    "tool_holehe": DiscoveredAccountSourceType.HOLEHE,
    "tool_maigret": DiscoveredAccountSourceType.MAIGRET,
}

_SOURCE_TYPE_CONFIDENCE = {
    DiscoveredAccountSourceType.HOLEHE: 70,
    DiscoveredAccountSourceType.MAIGRET: 60,
}


async def build_account_upsert_payload(
    signal: SignalCreate,
    service_registry_repo: ServiceRegistryRepository,
) -> dict[str, Any] | None:
    source_type = _PROVIDER_TO_SOURCE_TYPE.get(signal.provider)
    if source_type is None:
        logger.info(
            "scan_inventory.unsupported_provider_skipped",
            provider=signal.provider,
            source_ref=signal.source_ref,
        )
        return None

    evidence = signal.evidence if isinstance(signal.evidence, dict) else {}
    platform = str(evidence.get("platform", "") or "").strip()
    if not platform:
        return None

    profile_url = _clean_url(evidence.get("profile_url"))
    sender_domain = _extract_domain(profile_url)
    registry_entry = None
    if sender_domain:
        registry_entry = await service_registry_repo.find_by_domain(sender_domain)

    normalized_service_name = _normalize_service_name(platform)
    if registry_entry is None and normalized_service_name:
        registry_entry = await service_registry_repo.get_by_name(
            normalized_service_name
        )

    service_name = (
        registry_entry.service_name
        if registry_entry is not None
        else normalized_service_name or sender_domain or platform.lower()
    )
    display_name = (
        registry_entry.display_name if registry_entry is not None else platform
    )
    login_url = (
        registry_entry.login_url
        if registry_entry is not None and registry_entry.login_url
        else _service_homepage(profile_url)
    )
    password_reset_url = (
        registry_entry.password_reset_url if registry_entry is not None else None
    )
    if (
        not sender_domain
        and registry_entry is not None
        and registry_entry.common_domains
    ):
        sender_domain = str(registry_entry.common_domains[0])
    if not sender_domain:
        sender_domain = service_name

    observed_at = datetime.now(UTC)
    return {
        "user_id": signal.user_id,
        "upload_id": SCAN_DISCOVERY_UPLOAD_ID,
        "service_name": service_name,
        "display_name": display_name,
        "email_used": signal.entity_value,
        "source_type": source_type,
        "sender_domain": sender_domain,
        "login_url": login_url,
        "password_reset_url": password_reset_url,
        "first_seen_at": observed_at,
        "last_seen_at": observed_at,
        "email_count": 1,
        "confidence_score": _SOURCE_TYPE_CONFIDENCE.get(source_type, 0),
        "increment_email_count": False,
    }


def _normalize_service_name(platform: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", platform.lower())
    return normalized[:100]


def _clean_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate.startswith(("http://", "https://")):
        return None
    return candidate


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().strip()
    if not host:
        return None
    return host[4:] if host.startswith("www.") else host


def _service_homepage(profile_url: str | None) -> str | None:
    if not profile_url:
        return None
    parsed = urlparse(profile_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"
