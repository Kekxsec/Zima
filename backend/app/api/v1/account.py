# backend/app/api/v1/account.py
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.logging import get_logger
from backend.app.db.models.audit import AuditEvent
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.scans import ScanRepository
from backend.app.db.repositories.scores import ScoreRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.db.repositories.users import UserRepository
from backend.app.db.session import AsyncSessionLocal

router = APIRouter(prefix="/account", tags=["account"])
logger = get_logger(__name__)


@router.get("")
async def get_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Return the authenticated user's basic profile and declared assets."""
    asset_repo = AssetRepository(db)
    assets = await asset_repo.get_all_for_user(current_user.id)

    return {
        "user": {
            "user_id": str(current_user.id),
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        },
        "assets": [
            {
                "asset_id": str(asset.id),
                "user_id": str(asset.user_id),
                "entity_type": asset.entity_type,
                "value": asset.value,
                "is_primary": asset.is_primary,
                "is_verified": asset.is_verified,
                "created_at": asset.created_at,
                "updated_at": asset.updated_at,
            }
            for asset in assets
        ],
    }


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Returns the authenticated user's own activity log."""
    audit_repo = AuditRepository(db)
    events: list[AuditEvent] = await audit_repo.get_for_user(
        user_id=current_user.id,
        limit=min(limit, 100),
        offset=offset,
    )
    return {"events": events, "limit": limit, "offset": offset}


@router.delete("", status_code=202)
async def delete_account(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Initiates account deletion.
    - Immediately soft-deletes the user (prevents further sign-in)
    - Schedules hard deletion of personal data in background
    Returns immediately — deletion runs asynchronously.
    """
    user_repo = UserRepository(db)
    await user_repo.soft_delete(current_user.id)
    await db.commit()

    background_tasks.add_task(
        _delete_user_personal_data,
        user_id=current_user.id,
    )

    return {
        "message": (
            "Account deletion initiated. Your data will be removed within 24 hours."
        )
    }


async def _delete_user_personal_data(user_id: uuid.UUID) -> None:
    """
    Hard-deletes all personal data for a user.
    Runs in a background task with its own session (Rule 3).
    Order matters — delete child records before parents.
    """
    logger.info("gdpr.deletion_started", user_id=str(user_id))

    async with AsyncSessionLocal() as session:
        asset_repo = AssetRepository(session)
        score_repo = ScoreRepository(session)
        finding_repo = FindingRepository(session)
        signal_repo = SignalRepository(session)
        scan_repo = ScanRepository(session)
        token_repo = AuthTokenRepository(session)
        user_repo = UserRepository(session)

        # Collect email addresses before deleting assets (needed for AuthToken cleanup)
        assets = await asset_repo.get_all_for_user(user_id)
        email_values = [a.value for a in assets if a.entity_type == "email"]

        # Delete in dependency order
        await score_repo.delete_all_for_user(user_id)
        await finding_repo.delete_all_for_user(user_id)
        await signal_repo.delete_all_for_user(user_id)
        await scan_repo.delete_all_for_user(user_id)
        await asset_repo.delete_all_for_user(user_id)

        # Delete auth tokens by email address
        for email in email_values:
            await token_repo.invalidate_all_for_email(email)

        # Null out PII on User row — keep row for billing/audit referential integrity
        await user_repo.scrub_pii(user_id)
        await session.commit()

    logger.info("gdpr.deletion_completed", user_id=str(user_id))


@router.get("/export")
async def export_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Returns all data Zima holds about the authenticated user.
    Fulfils GDPR Article 15 right of access.
    """
    asset_repo = AssetRepository(db)
    signal_repo = SignalRepository(db)
    finding_repo = FindingRepository(db)
    score_repo = ScoreRepository(db)

    assets = await asset_repo.get_all_for_user(current_user.id)
    signals = await signal_repo.get_all_for_user(current_user.id)
    findings = await finding_repo.get_all_for_user(current_user.id)
    scores = await score_repo.get_all_for_user(current_user.id)

    return {
        "user": {
            "id": str(current_user.id),
            "tier": current_user.tier,
            "last_sign_in_at": current_user.last_sign_in_at,
            "created_at": current_user.created_at,
        },
        "assets": [
            {
                "id": str(a.id),
                "entity_type": a.entity_type,
                "value": a.value,
                "is_primary": a.is_primary,
                "is_verified": a.is_verified,
                "verified_at": a.verified_at,
                "created_at": a.created_at,
            }
            for a in assets
        ],
        "signals": [
            {
                "id": str(s.id),
                "signal_type": s.signal_type,
                "category": s.category,
                "severity": s.severity,
                "summary": s.summary,
                "source": s.source,
                "status": s.status,
                "created_at": s.created_at,
            }
            for s in signals
        ],
        "findings": [
            {
                "id": str(f.id),
                "finding_type": f.finding_type,
                "severity": f.severity,
                "title": f.title,
                "status": f.status,
                "created_at": f.created_at,
            }
            for f in findings
        ],
        "scores": [
            {
                "id": str(sc.id),
                "domain": sc.domain,
                "score": sc.score,
                "calculated_at": sc.calculated_at,
            }
            for sc in scores
        ],
    }
