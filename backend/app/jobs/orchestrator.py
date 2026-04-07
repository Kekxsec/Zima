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
from backend.app.db.repositories.notification_outbox import NotificationOutboxRepository
from backend.app.db.repositories.scan_events import ScanEventRepository
from backend.app.db.repositories.scans import ScanRepository
from backend.app.db.repositories.scores import ScoreRepository
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.email.service import EmailService
from backend.app.jobs.context import ScanExecutionContext
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

# Maximum breach alert emails written to the outbox per scan cycle.
_MAX_OUTBOX_ENQUEUE_PER_SCAN: int = 3


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
        event_repo = ScanEventRepository(session)
        outbox_repo = NotificationOutboxRepository(session)

        ctx = ScanExecutionContext(
            scan_id=scan_id,
            user_id=user_id,
            tier=tier.value,
        )

        await scan_repo.update_status(
            scan_id=scan_id,
            status=ScanStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        ctx.record_event("scan_started", tier=tier.value)
        await session.commit()

        try:
            # ── Step 1: Run modules ─────────────────────────────────────────
            ctx.record_event("stage_started", stage="modules")
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
                ctx=ctx,
            )
            ctx.record_event(
                "signals_upserted",
                count=int(run_result["signals_created"]),
                domains=list(run_result["domains_run"]),
                **ctx.summary(),
            )
            await event_repo.bulk_record(scan_id, user_id, ctx.drain_events())
            await session.commit()

            # ── Step 2: Correlate ──────────────────────────────────────────
            ctx.record_event("stage_started", stage="correlation")
            signals = await signal_repo.get_open_for_user(user_id, limit=1000)
            findings = _correlation_engine.run(user_id=user_id, signals=signals)
            for finding in findings:
                await finding_repo.upsert(finding)
            await session.commit()

            # ── Step 3: Score (append-only — never overwrite) ──────────────
            ctx.record_event("stage_started", stage="scoring")
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

            # ── Step 4: Enqueue breach alert notifications (outbox) ────────
            # Write outbox rows atomically with the scan commit so that a
            # downstream email failure never loses the intent to notify.
            # Rows are processed (sent) immediately after the commit below.
            ctx.record_event("stage_started", stage="notifications")
            enqueued = await _enqueue_signal_notifications(
                user_id=user_id,
                signals=signals,
                asset_repo=asset_repo,
                outbox_repo=outbox_repo,
            )
            if enqueued > 0:
                ctx.record_event("notification_enqueued", count=enqueued)

            # ── Step 5: Mark completed ─────────────────────────────────────
            ctx.record_event(
                "scan_completed",
                signals_created=int(run_result["signals_created"]),
                findings_created=len(findings),
                identity_score=identity_score,
            )
            await event_repo.bulk_record(scan_id, user_id, ctx.drain_events())
            await scan_repo.update_status(
                scan_id=scan_id,
                status=ScanStatus.COMPLETED,
                completed_at=datetime.now(UTC),
                signals_created=int(run_result["signals_created"]),
                findings_created=len(findings),
                domains_run=list(run_result["domains_run"]),
            )
            # Commit before sending — outbox rows are now durable.
            await session.commit()

            # ── Step 5b: Process outbox (best-effort send) ─────────────────
            # Failures here do not roll back the scan; rows stay pending
            # for retry on the next scan cycle.
            sent = await _process_notification_outbox(
                user_id=user_id,
                outbox_repo=outbox_repo,
                signal_repo=signal_repo,
            )
            if sent > 0:
                logger.info("scan.notifications_sent", scan_id=str(scan_id), count=sent)

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
                ctx.record_event("scan_failed", error=str(exc)[:512])
                await event_repo.bulk_record(scan_id, user_id, ctx.drain_events())
                await scan_repo.update_status(
                    scan_id=scan_id,
                    status=ScanStatus.FAILED,
                    completed_at=datetime.now(UTC),
                    error_detail=str(exc)[:1024],
                )
                await session.commit()
            except Exception as inner_exc:
                logger.error("scan.failed_to_mark_failed", error=str(inner_exc))


async def _enqueue_signal_notifications(
    user_id: uuid.UUID,
    signals: list[Signal],
    asset_repo: AssetRepository,
    outbox_repo: NotificationOutboxRepository,
) -> int:
    """
    Write pending outbox rows for unnotified high/critical breach signals.

    Rows are written within the caller's open transaction so they are
    committed atomically with the scan state.  Email delivery happens
    separately in _process_notification_outbox().

    Caps at _MAX_OUTBOX_ENQUEUE_PER_SCAN rows per scan to prevent flooding.
    Returns the number of rows enqueued.
    """
    unnotified_high = [
        s
        for s in signals
        if s.severity in ("critical", "high")
        and s.signal_type == "email_breached"
        and s.notified_at is None
    ][:_MAX_OUTBOX_ENQUEUE_PER_SCAN]

    if not unnotified_high:
        return 0

    primary_asset = await asset_repo.get_primary_email(user_id)
    if not primary_asset:
        return 0

    enqueued = 0
    for signal in unnotified_high:
        evidence = signal.evidence or {}
        await outbox_repo.enqueue(
            user_id=user_id,
            signal_id=signal.signal_id,
            to_email=primary_asset.value,
            monitored_email=signal.entity_value or "",
            template="breach_alert",
            payload={
                "breach_title": evidence.get("breach_name", "Unknown breach"),
                "breach_date": evidence.get("breach_date", "Unknown date"),
                "data_classes": evidence.get("data_classes", []),
            },
        )
        enqueued += 1

    return enqueued


async def _process_notification_outbox(
    user_id: uuid.UUID,
    outbox_repo: NotificationOutboxRepository,
    signal_repo: SignalRepository,
) -> int:
    """
    Send emails for pending outbox rows and mark them sent.

    Failures are recorded per-row (attempt_count incremented, status set to
    failed after MAX_OUTBOX_ATTEMPTS).  A failed send never rolls back the
    scan or prevents other rows from being processed.

    Returns the number of successfully sent notifications.
    """
    pending = await outbox_repo.get_pending_for_user(
        user_id=user_id, limit=_MAX_OUTBOX_ENQUEUE_PER_SCAN
    )
    if not pending:
        return 0

    sent = 0
    for row in pending:
        try:
            payload = row.payload or {}
            await _email_service.send_breach_alert(
                to_email=row.to_email,
                monitored_email=row.monitored_email,
                breach_title=payload.get("breach_title", "Unknown breach"),
                breach_date=payload.get("breach_date", "Unknown date"),
                data_classes=payload.get("data_classes", []),
            )
            await outbox_repo.mark_sent(row.id)

            # Mark the originating signal as notified so it is not re-queued
            # on the next scan cycle.
            if row.signal_id is not None:
                await signal_repo.mark_notified(str(row.signal_id))

            await signal_repo.session.commit()
            sent += 1

        except Exception as exc:
            await signal_repo.session.rollback()
            logger.error(
                "scan.notification_send_failed",
                outbox_id=str(row.id),
                error=str(exc),
            )
            try:
                await outbox_repo.increment_attempt(row.id)
                await signal_repo.session.commit()
            except Exception as persist_exc:
                await signal_repo.session.rollback()
                logger.error(
                    "scan.notification_failure_persist_failed",
                    outbox_id=str(row.id),
                    error=str(persist_exc),
                )

    return sent
