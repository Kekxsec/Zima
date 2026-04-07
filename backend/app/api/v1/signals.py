# backend/app/api/v1/signals.py
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.rate_limit import limiter
from backend.app.db.models.audit import AuditEventType
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.signals import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])
_EXCLUDED_SIGNAL_TYPES = ["account_discovered", "username_exposure"]


class SuppressRequest(BaseModel):
    reason: str | None = Field(None, max_length=256)


@router.get("")
async def get_signals(
    filter_status: Literal["open", "suppressed"] = Query(default="open"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Returns signals for the authenticated user.

    filter_status: open (default) or suppressed.
    """
    signal_repo = SignalRepository(db)
    signals = await signal_repo.get_for_user_by_status(
        user_id=current_user.id,
        status=filter_status,
        limit=limit,
        offset=offset,
        exclude_signal_types=_EXCLUDED_SIGNAL_TYPES,
    )
    total = await signal_repo.count_for_user_by_status(
        user_id=current_user.id,
        status=filter_status,
        exclude_signal_types=_EXCLUDED_SIGNAL_TYPES,
    )

    return {
        "signals": [
            {
                "signal_id": s.signal_id,
                "signal_type": s.signal_type,
                "category": s.category,
                "entity_type": s.entity_type,
                "entity_value": s.entity_value,
                "severity": s.severity,
                "confidence": s.confidence,
                "source": s.source,
                "provider": s.provider,
                "summary": s.summary,
                "details": s.details,
                "evidence": s.evidence,
                "tags": s.tags,
                "recommended_action": s.recommended_action,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in signals
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "filter_status": filter_status,
    }


@router.patch("/{signal_id}/suppress", status_code=200)
@limiter.limit("30/minute")
async def suppress_signal(
    request: Request,
    signal_id: str,
    body: SuppressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Suppresses an open signal."""
    signal_repo = SignalRepository(db)
    updated = await signal_repo.suppress(user_id=current_user.id, signal_id=signal_id)
    if not updated:
        raise HTTPException(
            status_code=404, detail="Signal not found or not in open status"
        )

    audit_repo = AuditRepository(db)
    await audit_repo.log(
        event_type=AuditEventType.SIGNAL_SUPPRESSED,
        user_id=current_user.id,
        metadata={"signal_id": signal_id, "reason": body.reason},
    )
    await db.commit()
    return {"status": "suppressed", "signal_id": signal_id}
