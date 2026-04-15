# backend/app/jobs/runner.py
import asyncio
import uuid
from typing import TypedDict

from backend.app.active.modules import ACTIVE_MODULES
from backend.app.active.specs import ModuleSpec
from backend.app.core.enums import Tier
from backend.app.core.logging import get_logger
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.email_accounts.scan_inventory import build_account_upsert_payload
from backend.app.jobs.context import ScanExecutionContext
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.models import ProviderPermissionContext
from backend.app.providers.base.policy import evaluate_provider_policy
from backend.app.tiers.loader import get_enabled_domains

logger = get_logger(__name__)

# Hard cap per module per asset — prevents a single stalled provider from
# blocking the entire scan indefinitely. Individual providers have their own
# shorter timeouts; this is a belt-and-suspenders safety net.
_MODULE_ASSET_TIMEOUT_SECONDS = 120


def _policy_allows_module(spec: ModuleSpec, ctx: ScanExecutionContext | None) -> bool:
    """Apply evaluate_provider_policy at the module (orchestrator) level.

    Builds a PermissionContext from the scan context (or a safe default) and
    checks whether the module's canonical name is blocked by an explicit deny
    list or prefix rule.  Credential presence is NOT checked here — that is
    each provider's responsibility via run_provider().  This gate only enforces
    explicit orchestrator-level deny rules (e.g. regional restrictions, scan-
    type exclusions).
    """
    if ctx is not None:
        perm_ctx = ctx.to_permission_context()
    else:
        perm_ctx = ProviderPermissionContext(scan_type="full", tier="core", region=None)

    decision = evaluate_provider_policy(
        provider_name=spec.service_class.module_name,
        has_credentials=True,  # credential check delegated to providers
        context=perm_ctx,
    )
    if not decision.allowed:
        logger.info(
            "runner.module_policy_denied",
            module=spec.service_class.module_name,
            reason=decision.reason,
        )
    return decision.allowed


def _get_runnable_specs(tier: Tier) -> list[ModuleSpec]:
    """Return specs eligible to run for the given tier.

    A spec is runnable when its domain is enabled for the tier (per tier
    YAML) AND its status is "active". Deferred specs are always excluded.
    Policy enforcement (deny lists, prefix rules) is applied per-asset in
    _run_module via _policy_allows_module.
    """
    enabled = set(get_enabled_domains(tier))
    return [s for s in ACTIVE_MODULES if s.domain in enabled and s.status == "active"]


class RunResult(TypedDict):
    signals_created: int
    domains_run: list[str]


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
    ) -> RunResult:
        """
        Runs all enabled module domains for this user's tier.
        Returns a summary dict with 'signals_created' and 'domains_run'.
        ctx, if provided, receives module-level events for scan history.
        """
        runnable = _get_runnable_specs(tier)
        signals_created = 0
        domains_seen: list[str] = []
        domains_run: list[str] = []

        for spec in runnable:
            if spec.domain not in domains_seen:
                domains_seen.append(spec.domain)
                if ctx is not None:
                    ctx.record_event("stage_started", stage=f"domain:{spec.domain}")

            # Orchestrator-level policy gate: explicit deny lists / prefix rules.
            # Credential presence is not checked here — that is each provider's
            # responsibility via run_provider() inside the module service.
            if not _policy_allows_module(spec, ctx):
                continue

            module = spec.service_class()
            count = await self._run_module(
                module,
                user_id,
                target_email_asset_ids=target_email_asset_ids,
                ctx=ctx,
            )
            signals_created += count

            if spec.domain not in domains_run:
                domains_run.append(spec.domain)

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
                    outcome = await asyncio.wait_for(
                        module.run(
                            user_id=user_id,
                            asset_id=asset.id,
                            asset_value=asset.value,
                            ctx=ctx,
                        ),
                        timeout=_MODULE_ASSET_TIMEOUT_SECONDS,
                    )
                    # Persist account-discovery signals via account_repo
                    for signal in outcome.account_signals:
                        account_payload = await build_account_upsert_payload(
                            signal,
                            self.service_registry_repo,
                        )
                        if account_payload is not None:
                            await self.account_repo.upsert(**account_payload)
                    # Persist regular signals via signal_repo (budget-gated)
                    asset_signals = 0
                    for signal in outcome.signals:
                        # Enforce per-provider and total signal budgets
                        if ctx is not None and not ctx.record_signal_emitted(
                            module.module_name
                        ):
                            logger.warning(
                                "runner.signal_budget_exceeded",
                                module=module.module_name,
                                asset_id=str(asset.id),
                            )
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
