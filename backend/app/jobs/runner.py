# backend/app/jobs/runner.py
import asyncio
import uuid

from backend.app.core.enums import Tier
from backend.app.core.logging import get_logger
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.email_accounts.scan_inventory import (
    build_account_upsert_payload,
    is_scan_account_signal,
)
from backend.app.jobs.context import ScanExecutionContext
from backend.app.modules.base.service import BaseModuleService
from backend.app.modules.browser.browser_configuration.service import (
    BrowserConfigurationService,
)
from backend.app.modules.browser.extension_risk.service import ExtensionRiskService
from backend.app.modules.device.device_inventory.service import DeviceInventoryService
from backend.app.modules.device.firewall_status.service import FirewallStatusService
from backend.app.modules.device.os_security.service import OsSecurityService
from backend.app.modules.device.patch_status.service import PatchStatusService
from backend.app.modules.device.software_inventory.service import (
    SoftwareInventoryService,
)
from backend.app.modules.device.software_vulnerability.service import (
    SoftwareVulnerabilityService,
)
from backend.app.modules.domain.dns_intelligence.service import (
    DomainDNSIntelligenceService,
)
from backend.app.modules.domain.domain_reputation.service import (
    DomainReputationService,
)
from backend.app.modules.identity.account_enumeration_risk.service import (
    AccountEnumerationRiskService,
)
from backend.app.modules.identity.account_inventory.service import (
    AccountInventoryService,
)
from backend.app.modules.identity.alias_correlation.service import (
    AliasCorrelationService,
)
from backend.app.modules.identity.breach_monitor.service import BreachMonitorService
from backend.app.modules.identity.credential_exposure.service import (
    CredentialExposureService,
)
from backend.app.modules.identity.darkweb_identity_monitor.service import (
    DarkwebIdentityMonitorService,
)
from backend.app.modules.identity.email_reputation.service import (
    EmailReputationService,
)
from backend.app.modules.identity.maigret_scan.service import MaigretScanService
from backend.app.modules.identity.phone_exposure.service import PhoneExposureService
from backend.app.modules.identity.public_profile_scan.service import (
    PublicProfileScanService,
)
from backend.app.modules.identity.stealer_log_exposure.service import (
    StealerLogExposureService,
)
from backend.app.modules.identity.username_exposure.service import (
    UsernameExposureService,
)
from backend.app.modules.infrastructure.infrastructure_exposure.service import (
    InfrastructureExposureService,
)
from backend.app.tiers.loader import get_enabled_domains

logger = get_logger(__name__)

# Module registry — add new module classes here as they are built.
# Key: domain name matching tiers/config/*.yaml enabled_domains values.
# Value: list of module service classes for that domain.
# Hard cap per module per asset — prevents a single stalled provider from
# blocking the entire scan indefinitely. Individual providers have their own
# shorter timeouts; this is a belt-and-suspenders safety net.
_MODULE_ASSET_TIMEOUT_SECONDS = 120

DOMAIN_MODULES: dict[str, list[type[BaseModuleService]]] = {
    "identity": [
        BreachMonitorService,
        StealerLogExposureService,
        CredentialExposureService,
        UsernameExposureService,
        MaigretScanService,
        PhoneExposureService,
        AccountInventoryService,
        AccountEnumerationRiskService,
        AliasCorrelationService,
        DarkwebIdentityMonitorService,
        PublicProfileScanService,
        EmailReputationService,
    ],
    "browser": [
        BrowserConfigurationService,
        ExtensionRiskService,
    ],
    "device": [
        OsSecurityService,
        PatchStatusService,
        SoftwareVulnerabilityService,
        FirewallStatusService,
        DeviceInventoryService,
        SoftwareInventoryService,
    ],
    "infrastructure": [
        InfrastructureExposureService,
    ],
    "domain": [
        DomainDNSIntelligenceService,
        DomainReputationService,
    ],
}


class ModuleRunner:
    def __init__(
        self,
        asset_repo: AssetRepository,
        signal_repo: SignalRepository,
        account_repo: DiscoveredAccountRepository,
        service_registry_repo: ServiceRegistryRepository,
    ) -> None:
        self.asset_repo = asset_repo
        self.signal_repo = signal_repo
        self.account_repo = account_repo
        self.service_registry_repo = service_registry_repo

    async def run_for_user(
        self,
        user_id: uuid.UUID,
        tier: Tier,
        target_email_asset_ids: list[str] | None = None,
        ctx: ScanExecutionContext | None = None,
    ) -> dict[str, int | list[str]]:
        """
        Runs all enabled module domains for this user's tier.
        Returns a summary dict with 'signals_created' and 'domains_run'.
        ctx, if provided, receives module-level events for scan history.
        """
        enabled_domains = get_enabled_domains(tier)
        signals_created = 0
        domains_run: list[str] = []

        for domain in enabled_domains:
            module_classes = DOMAIN_MODULES.get(domain, [])
            if not module_classes:
                continue

            if ctx is not None:
                ctx.record_event("stage_started", stage=f"domain:{domain}")

            for module_class in module_classes:
                module = module_class()
                count = await self._run_module(
                    module,
                    user_id,
                    target_email_asset_ids=target_email_asset_ids,
                    ctx=ctx,
                )
                signals_created += count

            domains_run.append(domain)

        return {"signals_created": signals_created, "domains_run": domains_run}

    async def _run_module(
        self,
        module: BaseModuleService,
        user_id: uuid.UUID,
        target_email_asset_ids: list[str] | None = None,
        ctx: ScanExecutionContext | None = None,
    ) -> int:
        """
        Runs one module against all verified assets matching its required entity types.
        Upserts returned signals into the database.
        Catches and logs individual asset failures without stopping the run.
        Returns the total number of signals upserted.
        ctx, if provided, receives provider-outcome events for scan history.
        """
        count = 0
        allowed_email_asset_ids = set(target_email_asset_ids or [])
        for entity_type in module.required_entity_types:
            # CRITICAL: only verified assets are scanned — enforced here
            assets = await self.asset_repo.get_verified_for_user(
                user_id=user_id,
                entity_type=entity_type,
            )
            if entity_type == "email" and target_email_asset_ids is not None:
                assets = [a for a in assets if str(a.id) in allowed_email_asset_ids]
            for asset in assets:
                try:
                    signals = await asyncio.wait_for(
                        module.run(
                            user_id=user_id,
                            asset_id=asset.id,
                            asset_value=asset.value,
                            ctx=ctx,
                        ),
                        timeout=_MODULE_ASSET_TIMEOUT_SECONDS,
                    )
                    asset_signals = 0
                    for signal in signals:
                        if is_scan_account_signal(signal):
                            account_payload = await build_account_upsert_payload(
                                signal,
                                self.service_registry_repo,
                            )
                            if account_payload is not None:
                                await self.account_repo.upsert(**account_payload)
                            continue
                        # Enforce per-provider and total signal budgets
                        if ctx is not None and not ctx.record_signal_emitted(
                            module.module_name
                        ):
                            logger.warning(
                                "runner.signal_budget_exceeded",
                                module=module.module_name,
                                asset_id=str(asset.id),
                            )
                            if ctx is not None:
                                ctx.record_event(
                                    "budget_exceeded",
                                    module=module.module_name,
                                    asset_id=str(asset.id),
                                )
                            continue
                        await self.signal_repo.upsert(signal)
                        count += 1
                        asset_signals += 1
                    if ctx is not None:
                        ctx.record_event(
                            "provider_succeeded",
                            module=module.module_name,
                            asset_id=str(asset.id),
                            signals=asset_signals,
                        )
                except TimeoutError:
                    logger.error(
                        "runner.module_asset_timeout",
                        module=module.module_name,
                        asset_id=str(asset.id),
                        timeout=_MODULE_ASSET_TIMEOUT_SECONDS,
                    )
                    if ctx is not None:
                        ctx.record_event(
                            "provider_failed",
                            module=module.module_name,
                            asset_id=str(asset.id),
                            reason="timeout",
                        )
                except Exception as exc:
                    logger.error(
                        "runner.module_asset_error",
                        module=module.module_name,
                        asset_id=str(asset.id),
                        error=str(exc),
                    )
                    if ctx is not None:
                        ctx.record_event(
                            "provider_failed",
                            module=module.module_name,
                            asset_id=str(asset.id),
                            reason=str(exc)[:256],
                        )
        return count
