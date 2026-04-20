# backend/app/jobs/orchestrator.py
import uuid
from datetime import UTC, datetime

from backend.app.core.config import settings
from backend.app.core.enums import ScanStatus, Tier
from backend.app.core.logging import get_logger
from backend.app.correlation.engine import CorrelationEngine
from backend.app.correlation.rules.identity_compromise import HighIdentityCompromiseRisk
from backend.app.db.models.email_accounts import DiscoveredAccount
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
from backend.app.email_accounts.interpretation import (
    InterpretationStats,
    interpret_accounts_with_stats,
)
from backend.app.email_accounts.schemas import DiscoveredAccountDraft
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
    post_import_upload_id: uuid.UUID | None = None,
    review_all_discovered_accounts: bool = False,
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
    5. Optionally run post-import account identity review (Ollama)
    6. Mark scan COMPLETED
    7. Send email notifications for new high/critical signals

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

            # ── Step 5: Optional account identity review (Ollama) ──────────
            post_import_reviewed = 0
            post_import_updated = 0
            post_import_ollama_attempted = 0
            post_import_ollama_succeeded = 0
            post_import_ollama_failed = 0
            post_import_review_scope = "none"
            if review_all_discovered_accounts or post_import_upload_id is not None:
                ctx.record_event("stage_started", stage="post_import_identity_review")
                try:
                    async with session.begin_nested():
                        if review_all_discovered_accounts:
                            post_import_review_scope = "all_discovered_accounts"
                            (
                                post_import_reviewed,
                                post_import_updated,
                                post_import_stats,
                            ) = await _run_full_identity_review(
                                user_id=user_id,
                                account_repo=account_repo,
                            )
                        else:
                            post_import_review_scope = "upload_only"
                            (
                                post_import_reviewed,
                                post_import_updated,
                                post_import_stats,
                            ) = await _run_post_import_identity_review(
                                user_id=user_id,
                                upload_id=post_import_upload_id,
                                account_repo=account_repo,
                            )
                    post_import_event: dict[str, str | int] = {
                        "scope": post_import_review_scope,
                        "reviewed_count": post_import_reviewed,
                        "updated_count": post_import_updated,
                        "candidates_attempted": post_import_stats[
                            "candidates_attempted"
                        ],
                        "lookup_resolved": post_import_stats["lookup_resolved"],
                        "embedding_resolved": post_import_stats["embedding_resolved"],
                        "ollama_batches": post_import_stats["ollama_batches"],
                    }
                    if post_import_upload_id is not None:
                        post_import_event["upload_id"] = str(post_import_upload_id)
                    post_import_ollama_attempted = post_import_stats["ollama_queued"]
                    post_import_ollama_succeeded = post_import_stats["ollama_succeeded"]
                    post_import_ollama_failed = post_import_stats["ollama_failed"]
                    post_import_event["ollama_attempted"] = post_import_ollama_attempted
                    post_import_event["ollama_succeeded"] = post_import_ollama_succeeded
                    post_import_event["ollama_failed"] = post_import_ollama_failed
                    ctx.record_event(
                        "post_import_identity_review_completed",
                        **post_import_event,
                    )
                except Exception as exc:
                    logger.warning(
                        "scan.post_import_identity_review_failed",
                        scan_id=str(scan_id),
                        user_id=str(user_id),
                        upload_id=(
                            str(post_import_upload_id)
                            if post_import_upload_id is not None
                            else None
                        ),
                        scope=post_import_review_scope,
                        error=str(exc),
                        exc_info=True,
                    )
                    failed_event: dict[str, str] = {
                        "scope": post_import_review_scope,
                        "error": str(exc)[:512],
                    }
                    if post_import_upload_id is not None:
                        failed_event["upload_id"] = str(post_import_upload_id)
                    ctx.record_event(
                        "post_import_identity_review_failed",
                        **failed_event,
                    )

            # ── Step 5b: Dedupe accounts by domain ────────────────────────
            try:
                async with session.begin_nested():
                    deduped = await account_repo.merge_duplicates_by_domain(
                        user_id=user_id
                    )
                if deduped > 0:
                    ctx.record_event("account_dedupe_completed", deleted=deduped)
            except Exception as exc:
                logger.warning(
                    "scan.account_dedupe_failed",
                    scan_id=str(scan_id),
                    user_id=str(user_id),
                    error=str(exc),
                )

            # ── Step 5c: Backfill login URLs from service registry ─────────
            try:
                async with session.begin_nested():
                    url_filled = await account_repo.backfill_urls_from_registry(
                        user_id=user_id,
                        registry_repo=service_registry_repo,
                    )
                if url_filled > 0:
                    ctx.record_event(
                        "account_url_backfill_completed", updated=url_filled
                    )
            except Exception as exc:
                logger.warning(
                    "scan.account_url_backfill_failed",
                    scan_id=str(scan_id),
                    user_id=str(user_id),
                    error=str(exc),
                )

            # ── Step 5d: Classify accounts ─────────────────────────────────
            try:
                async with session.begin_nested():
                    classified = await account_repo.classify_accounts(
                        user_id=user_id,
                        registry_repo=service_registry_repo,
                    )
                if classified > 0:
                    ctx.record_event(
                        "account_classification_completed", updated=classified
                    )
            except Exception as exc:
                logger.warning(
                    "scan.account_classification_failed",
                    scan_id=str(scan_id),
                    user_id=str(user_id),
                    error=str(exc),
                )

            # ── Step 6: Mark completed ─────────────────────────────────────
            ctx.record_event(
                "scan_completed",
                signals_created=int(run_result["signals_created"]),
                findings_created=len(findings),
                identity_score=identity_score,
                post_import_reviewed=post_import_reviewed,
                post_import_updated=post_import_updated,
                post_import_ollama_attempted=post_import_ollama_attempted,
                post_import_ollama_succeeded=post_import_ollama_succeeded,
                post_import_ollama_failed=post_import_ollama_failed,
                post_import_review_scope=post_import_review_scope,
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

            # ── Step 7: Process outbox (best-effort send) ──────────────────
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
                post_import_reviewed=post_import_reviewed,
                post_import_updated=post_import_updated,
                post_import_ollama_attempted=post_import_ollama_attempted,
                post_import_ollama_succeeded=post_import_ollama_succeeded,
                post_import_ollama_failed=post_import_ollama_failed,
                post_import_review_scope=post_import_review_scope,
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


def _empty_interpretation_stats() -> InterpretationStats:
    return {
        "total_drafts": 0,
        "candidates_attempted": 0,
        "lookup_resolved": 0,
        "embedding_resolved": 0,
        "ollama_queued": 0,
        "ollama_batches": 0,
        "ollama_succeeded": 0,
        "ollama_failed": 0,
    }


async def _run_identity_review_for_accounts(
    *,
    user_id: uuid.UUID,
    accounts: list[DiscoveredAccount],
    account_repo: DiscoveredAccountRepository,
) -> tuple[int, int, InterpretationStats]:
    if not accounts:
        return 0, 0, _empty_interpretation_stats()

    drafts = [
        DiscoveredAccountDraft(
            service_name=account.service_name,
            display_name=account.display_name,
            email_used=account.email_used,
            source_type=account.source_type,
            sender_domain=account.sender_domain,
            login_url=account.login_url,
            password_reset_url=account.password_reset_url,
            unsubscribe_url=account.unsubscribe_url,
            first_seen_at=account.first_seen_at,
            last_seen_at=account.last_seen_at,
            email_count=account.email_count,
            confidence_score=account.confidence_score,
        )
        for account in accounts
    ]
    subjects_map = {
        account.sender_domain: [] for account in accounts if account.sender_domain
    }
    reviewed, stats = await interpret_accounts_with_stats(
        drafts,
        subjects_map,
        review_all=True,
        max_candidates=0,
        force_ollama=False,
        batch_size=settings.ollama_post_import_max_candidates,
    )

    updated_count = 0
    for account, updated_draft in zip(accounts, reviewed, strict=True):
        if (
            updated_draft.service_name == account.service_name
            and updated_draft.display_name == account.display_name
        ):
            continue
        before_service = account.service_name
        before_display = account.display_name
        updated = await account_repo.update_identity_fields(
            account_id=account.id,
            user_id=user_id,
            service_name=updated_draft.service_name,
            display_name=updated_draft.display_name,
        )
        if updated is None:
            continue
        if (
            updated.service_name != before_service
            or updated.display_name != before_display
        ):
            updated_count += 1

    return len(accounts), updated_count, stats


async def _run_full_identity_review(
    *,
    user_id: uuid.UUID,
    account_repo: DiscoveredAccountRepository,
) -> tuple[int, int, InterpretationStats]:
    """
    Run Ollama identity review across all discovered accounts for the user.
    """
    accounts = await account_repo.list_all_for_user(user_id=user_id)
    return await _run_identity_review_for_accounts(
        user_id=user_id,
        accounts=accounts,
        account_repo=account_repo,
    )


async def _run_post_import_identity_review(
    *,
    user_id: uuid.UUID,
    upload_id: uuid.UUID | None,
    account_repo: DiscoveredAccountRepository,
) -> tuple[int, int, InterpretationStats]:
    """
    Run line-by-line Ollama identity review on accounts from one upload.

    Returns (reviewed_count, updated_count, stats).
    """
    if upload_id is None:
        return 0, 0, _empty_interpretation_stats()

    accounts = await account_repo.list_for_upload(user_id=user_id, upload_id=upload_id)
    return await _run_identity_review_for_accounts(
        user_id=user_id,
        accounts=accounts,
        account_repo=account_repo,
    )


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
