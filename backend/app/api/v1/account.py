# backend/app/api/v1/account.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.db.models.audit import AuditEvent
from backend.app.db.repositories.audit import AuditRepository

router = APIRouter(prefix="/account", tags=["account"])


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


# GDPR deletion and data export endpoints — implemented in Stage 7
