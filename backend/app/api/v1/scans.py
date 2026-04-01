# backend/app/api/v1/scans.py
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.enums import EntityType, ScanStatus, Tier
from backend.app.core.rate_limit import limiter
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.scans import ScanRepository
from backend.app.jobs.models import Scan
from backend.app.jobs.orchestrator import run_scan_task

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("/", status_code=202)
@limiter.limit("5/hour")
async def trigger_scan(
    request: Request,  # Required by slowapi for rate limiting
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Queues a scan for the authenticated user.
    Returns immediately with scan_id. Client polls GET /scans/{scan_id} for completion.
    Background task creates its own database session — no session is passed to it.
    """
    asset_repo = AssetRepository(db)
    verified_email_assets = await asset_repo.get_verified_for_user(
        user_id=current_user.id,
        entity_type=EntityType.EMAIL,
    )
    target_emails = sorted({str(asset.value) for asset in verified_email_assets})
    target_email_asset_ids = [str(asset.id) for asset in verified_email_assets]

    scan_repo = ScanRepository(db)
    scan = await scan_repo.create(
        user_id=current_user.id,
        tier=Tier(current_user.tier),
        target_emails=target_emails,
    )
    await db.commit()

    # Pass only serialisable values — never a session or db object
    background_tasks.add_task(
        run_scan_task,
        user_id=current_user.id,
        scan_id=scan.id,
        tier=Tier(current_user.tier),
        target_email_asset_ids=target_email_asset_ids,
    )

    return {
        "scan_id": str(scan.id),
        "status": ScanStatus.PENDING.value,
        "target_emails": target_emails,
    }


@router.get("/")
async def get_scan_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    scan_repo = ScanRepository(db)
    scans = await scan_repo.get_history_for_user(
        user_id=current_user.id,
        limit=min(limit, 50),
        offset=offset,
    )
    return {
        "scans": [_scan_to_dict(s) for s in scans],
        "limit": limit,
        "offset": offset,
    }


@router.get("/{scan_id}")
async def get_scan_status(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Returns current status of a scan. Also detects and marks stale scans.
    Poll this endpoint after triggering a scan to check for completion.
    """
    try:
        scan_uuid = uuid.UUID(scan_id)
    except ValueError as err:
        raise HTTPException(status_code=422, detail="Invalid scan ID format") from err

    scan_repo = ScanRepository(db)
    scan = await scan_repo.get_by_id_for_user(
        scan_id=scan_uuid,
        user_id=current_user.id,
    )
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Detect and mark stale scans on read — prevents stuck RUNNING status.
    # Uses a conditional UPDATE (WHERE status=RUNNING AND started_at < threshold)
    # so it is race-free: if the background task finishes concurrently, its
    # COMPLETED update wins and this matches zero rows.
    if scan.status == ScanStatus.RUNNING.value and scan.started_at:
        marked = await scan_repo.mark_stale_if_running(scan_uuid)
        if marked:
            await db.commit()
            refreshed = await scan_repo.get_by_id_for_user(
                scan_id=scan_uuid, user_id=current_user.id
            )
            if refreshed:
                scan = refreshed

    return _scan_to_dict(scan)


def _scan_to_dict(scan: Scan) -> dict[str, object]:
    return {
        "id": str(scan.id),
        "status": scan.status,
        "tier": scan.tier,
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "signals_created": scan.signals_created,
        "findings_created": scan.findings_created,
        "domains_run": scan.domains_run,
        "target_emails": scan.target_emails,
        "error_detail": scan.error_detail,
        "created_at": scan.created_at.isoformat(),
    }
