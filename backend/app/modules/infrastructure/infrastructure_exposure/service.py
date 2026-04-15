# backend/app/modules/infrastructure/infrastructure_exposure/service.py
"""Infrastructure exposure module — powered by LeakIX.

Checks whether domains derived from the user's verified email address have
exposed services or data leaks indexed by LeakIX.

Only operates against DOMAIN assets. The caller is responsible for deriving
the domain from a verified email and creating a DOMAIN asset first.

Signal types emitted:
  - exposed_service_found     — LeakIX has indexed an exposed/leaking service
  - exposed_service_no_auth   — exposed service carries the 'no-auth' tag
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from backend.app.core.config import settings
from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.base.runner import run_provider
from backend.app.providers.threat_intel.leakix.client import LeakIXProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)

_PROVIDER_NAME = "leakix"

# Protocols that indicate a high-value data store — used for severity escalation.
_HIGH_VALUE_PROTOCOLS = frozenset(
    {"elasticsearch", "mongodb", "mysql", "postgresql", "redis", "cassandra", "couchdb"}
)

# Results older than this many days are treated as potentially stale.
_STALE_THRESHOLD_DAYS = 90


class InfrastructureExposureService(BaseModuleService):
    """Searches LeakIX for exposed services and data leaks on user-owned domains.

    Runs against DOMAIN assets. Emits signals for each confirmed exposure.
    """

    module_name = "infrastructure_exposure"
    module_domain = "infrastructure"
    required_entity_types = [EntityType.DOMAIN]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: ScanExecutionContext | None = None,
    ) -> ModuleOutcome:
        signals: list[SignalCreate] = []

        if not settings.leakix_api_key:
            logger.debug(
                "infrastructure_exposure.skipped",
                reason="LEAKIX_API_KEY not configured",
            )
            return ModuleOutcome(signals=signals)

        api_key = settings.leakix_api_key.get_secret_value()
        provider = LeakIXProvider(api_key=api_key)

        result = await run_provider(
            provider_name=_PROVIDER_NAME,
            call=lambda: provider.domain_leak_search(asset_value),
            has_credentials=True,
            user_id=user_id,
            entity_type="domain",
            entity_value=asset_value,
            ctx=ctx,
            check_quota=True,
        )

        if not result.success:
            return ModuleOutcome(signals=signals)

        for finding in result.findings:
            if not isinstance(finding, dict):
                continue

            new_signals = self._build_signals(
                finding=finding,
                user_id=user_id,
                asset_id=asset_id,
                asset_value=asset_value,
            )
            signals.extend(new_signals)

        logger.info(
            "infrastructure_exposure.completed",
            user_id=str(user_id),
            domain=asset_value,
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)

    # ------------------------------------------------------------------
    # Signal construction
    # ------------------------------------------------------------------

    def _build_signals(
        self,
        finding: ProviderFinding,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
    ) -> ModuleOutcome:
        signals: list[SignalCreate] = []

        # ProviderFinding is a TypedDict (= dict at runtime); LeakIX mapper
        # stores provider-specific fields in `raw`.  Cast once to Any so that
        # the rich nested access below remains readable without per-line ignores.
        _f: dict[str, Any] = finding  # type: ignore[assignment]

        host = _f.get("host", asset_value)
        port = _f.get("port", "")
        protocol = _f.get("protocol", "unknown")
        summary_text = _f.get("summary", "")
        time_str = _f.get("time", "")
        no_auth = _f.get("no_auth", False)
        dataset_rows = int(_f.get("dataset_rows") or 0)
        tags = _f.get("tags") or []

        # Determine staleness
        is_stale = _is_stale(time_str)
        confidence = Confidence.LOW if is_stale else Confidence.HIGH

        location = f"{host}:{port}" if port else host

        # ── exposed_service_found ─────────────────────────────────────────
        severity = _compute_severity(
            protocol=protocol,
            dataset_rows=dataset_rows,
            no_auth=no_auth,
            is_stale=is_stale,
        )

        signals.append(
            SignalCreate(
                signal_type="exposed_service_found",
                category="infrastructure_security",
                entity_type=EntityType.DOMAIN,
                entity_id=asset_id,
                entity_value=asset_value,
                user_id=user_id,
                severity=severity,
                confidence=confidence,
                source=self.module_name,
                provider=_PROVIDER_NAME,
                summary=(
                    f"Exposed {protocol} service found on {location} — {summary_text}"
                ),
                details=(
                    f"LeakIX has indexed an exposed {protocol} service at {location}. "
                    f"{'Data exposure confirmed: ' + str(dataset_rows) + ' rows. ' if dataset_rows else ''}"  # noqa: E501
                    f"{'(Result may be stale — last seen >90 days ago.) ' if is_stale else ''}"  # noqa: E501
                    f"Tags: {', '.join(tags) if tags else 'none'}."
                ),
                evidence={
                    "ip": _f.get("ip"),
                    "host": host,
                    "port": port,
                    "protocol": protocol,
                    "summary": summary_text,
                    "time": time_str,
                    "dataset_rows": dataset_rows,
                    "dataset_size_bytes": _f.get("dataset_size_bytes"),
                    "dataset_collections": _f.get("dataset_collections"),
                    "no_auth": no_auth,
                    "tags": tags,
                    "is_stale": is_stale,
                    "country": _f.get("country"),
                    "as_name": _f.get("as_name"),
                    "ssl_enabled": _f.get("ssl_enabled"),
                },
                tags=["infrastructure_exposure", "leakix", protocol, "exposed_service"],
                recommended_action=(
                    "Immediately restrict access to this service. "
                    "Apply authentication, firewall rules, or take the service offline "
                    "if it should not be publicly accessible. "
                    "Review whether any data has been exfiltrated."
                ),
                source_ref=f"leakix:{host}:{port}",
            )
        )

        # ── exposed_service_no_auth (additional signal when no-auth tag is set) ─
        if no_auth:
            signals.append(
                SignalCreate(
                    signal_type="exposed_service_no_auth",
                    category="infrastructure_security",
                    entity_type=EntityType.DOMAIN,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.HIGH,
                    confidence=confidence,
                    source=self.module_name,
                    provider=_PROVIDER_NAME,
                    summary=f"Unauthenticated {protocol} service exposed on {location}",
                    details=(
                        f"The {protocol} service at {location} has no authentication — "
                        "anyone on the internet can read or write to it."
                    ),
                    evidence={
                        "ip": _f.get("ip"),
                        "host": host,
                        "port": port,
                        "protocol": protocol,
                        "tags": tags,
                        "country": _f.get("country"),
                        "as_name": _f.get("as_name"),
                        "ssl_enabled": _f.get("ssl_enabled"),
                    },
                    tags=["infrastructure_exposure", "leakix", protocol, "no_auth"],
                    recommended_action=(
                        "Enable authentication on this service immediately. "
                        "Rotate any credentials that may have been exposed. "
                        "Consider restricting access via firewall or VPN."
                    ),
                    source_ref=f"leakix:{host}:{port}:no_auth",
                )
            )

        return ModuleOutcome(signals=signals)


# ------------------------------------------------------------------
# Module-level helpers (severity rules — assigned here, never in provider)
# ------------------------------------------------------------------


def _compute_severity(
    protocol: str,
    dataset_rows: int,
    no_auth: bool,
    is_stale: bool,
) -> Severity:
    """Assign severity based on the signal contract rules from the research doc.

    Critical: high-value protocol with large dataset (>100k rows) or no-auth
    High:     no-auth on any exposed service
    Medium:   exposed service with smaller dataset or other protocol
    Low:      stale result (>90 days old) — confidence already downgraded
    """
    if is_stale:
        return Severity.LOW

    is_high_value = protocol.lower() in _HIGH_VALUE_PROTOCOLS

    if no_auth and is_high_value:
        return Severity.CRITICAL
    if dataset_rows > 100_000 and is_high_value:
        return Severity.CRITICAL
    if no_auth:
        return Severity.HIGH
    if is_high_value and dataset_rows > 0:
        return Severity.HIGH
    return Severity.MEDIUM


def _is_stale(time_str: str) -> bool:
    """Return True if the LeakIX result timestamp is older than 90 days."""
    if not time_str:
        return False
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            result_time = datetime.strptime(time_str, fmt).replace(tzinfo=UTC)
            age_days = (datetime.now(UTC) - result_time).days
            return age_days > _STALE_THRESHOLD_DAYS
        except ValueError:
            continue
    return False
