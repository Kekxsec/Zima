# backend/app/jobs/orchestrator.py
import uuid
from datetime import UTC, datetime

from backend.app.core.enums import ScanStatus, Tier
from backend.app.core.logging import get_logger
from backend.app.correlation.engine import CorrelationEngine
from backend.app.correlation.rules.identity_compromise import HighIdentityCompromiseRisk
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.discovered_accounts import DiscoveredAccountRepository
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.scans import ScanRepository
from backend.app.db.repositories.scores import ScoreRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.email.service import EmailService
from backend.app.jobs.runner import ModuleRunner
from backend.app.remediation.engine import RemediationEngine
from backend.app.scoring.calculators.identity_score import (
    SCORER_VERSION,
    calculate_identity_score,
)
from backend.app.signals.models import Signal

logger = get_logger(__name__)

# Stateless engines — safe to instantiate once at module level
_correlation_engine = CorrelationEngine(rules=[HighIdentityCompromiseRisk()])
_remediation_engine = RemediationEngine()
_email_service = EmailService()


async def run_scan_task(
    user_id: uuid.UUID,
    scan_id: uuid.UUID,
    tier: Tier,
    target_email_asset_ids: list[str] | None = None,
) -> None:
    """
    Background task entry point for a full scan cycle.

    IMPORTANT: Creates its own AsyncSession. Never called with a session parameter.
    Receives only serialisable values: UUIDs and enums.

    Sequence:
    1. Mark scan RUNNING
    2. Run module runner against verified assets for this tier
    3. Run correlation engine against open signals
    4. Calculate and append scores (never overwrite)
    5. Send email notifications for new high/critical signals
    6. Mark scan COMPLETED

    On any unhandled exception, marks scan FAILED and logs the error.
    """
    async with AsyncSessionLocal() as session:
        scan_repo = ScanRepository(session)
        signal_repo = SignalRepository(session)
        finding_repo = FindingRepository(session)
        score_repo = ScoreRepository(session)
        asset_repo = AssetRepository(session)
        account_repo = DiscoveredAccountRepository(session)
        service_registry_repo = ServiceRegistryRepository(session)

        await scan_repo.update_status(
            scan_id=scan_id,
            status=ScanStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        await session.commit()

        try:
            # ── Step 1: Run modules ─────────────────────────────────────────
            runner = ModuleRunner(
                asset_repo=asset_repo,
                signal_repo=signal_repo,
                account_repo=account_repo,
                service_registry_repo=service_registry_repo,
            )
            run_result = await runner.run_for_user(
                user_id=user_id,
                tier=tier,
                target_email_asset_ids=target_email_asset_ids,
            )
            await session.commit()

            # ── Step 2: Correlate ──────────────────────────────────────────
            signals = await signal_repo.get_open_for_user(user_id, limit=1000)
            findings = _correlation_engine.run(user_id=user_id, signals=signals)
            for finding in findings:
                await finding_repo.upsert(finding)
            await session.commit()

            # ── Step 3: Score (append-only — never overwrite) ──────────────
            identity_score, signal_count = calculate_identity_score(signals)
            await score_repo.insert(
                user_id=user_id,
                domain="identity",
                score=identity_score,
                signal_count=signal_count,
                scan_id=scan_id,
                scorer_version=SCORER_VERSION,
            )
            await session.commit()

            # ── Step 4: Notify for new unnotified high/critical signals ─────
            await _send_new_signal_notifications(
                user_id=user_id,
                signals=signals,
                asset_repo=asset_repo,
                signal_repo=signal_repo,
            )

            # ── Step 5: Mark completed ─────────────────────────────────────
            await scan_repo.update_status(
                scan_id=scan_id,
                status=ScanStatus.COMPLETED,
                completed_at=datetime.now(UTC),
                signals_created=int(run_result["signals_created"]),
                findings_created=len(findings),
                domains_run=list(run_result["domains_run"]),
            )
            await session.commit()

            logger.info(
                "scan.completed",
                scan_id=str(scan_id),
                user_id=str(user_id),
                signals=run_result["signals_created"],
                findings=len(findings),
                identity_score=identity_score,
            )

        except Exception as exc:
            logger.error(
                "scan.failed",
                scan_id=str(scan_id),
                user_id=str(user_id),
                error=str(exc),
                exc_info=True,
            )
            try:
                await scan_repo.update_status(
                    scan_id=scan_id,
                    status=ScanStatus.FAILED,
                    completed_at=datetime.now(UTC),
                    error_detail=str(exc)[:1024],
                )
                await session.commit()
            except Exception as inner_exc:
                logger.error("scan.failed_to_mark_failed", error=str(inner_exc))


async def _send_new_signal_notifications(
    user_id: uuid.UUID,
    signals: list[Signal],
    asset_repo: AssetRepository,
    signal_repo: SignalRepository,
) -> None:
    """
    Sends breach alert emails for signals that have not yet been notified.
    Uses signal.notified_at IS NULL to determine which signals are new.
    Caps at 3 emails per scan to prevent flooding.
    Updates notified_at on each signal after sending.
    """
    unnotified_high = [
        s
        for s in signals
        if s.severity in ("critical", "high")
        and s.signal_type == "email_breached"
        and s.notified_at is None
    ][:3]  # Hard cap at 3 notifications per scan

    if not unnotified_high:
        return

    primary_asset = await asset_repo.get_primary_email(user_id)
    if not primary_asset:
        return

    for signal in unnotified_high:
        evidence = signal.evidence or {}
        await _email_service.send_breach_alert(
            to_email=primary_asset.value,
            monitored_email=signal.entity_value,
            breach_title=evidence.get("breach_name", "Unknown breach"),
            breach_date=evidence.get("breach_date", "Unknown date"),
            data_classes=evidence.get("data_classes", []),
        )
        # Mark as notified so this signal is not emailed again on the next scan
        signal.notified_at = datetime.now(UTC)

    # Flush immediately so notified_at is persisted regardless of whether the
    # caller's Step 5 commit succeeds.
    await signal_repo.session.flush()
