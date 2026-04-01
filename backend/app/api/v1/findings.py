# backend/app/api/v1/findings.py
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.rate_limit import limiter
from backend.app.db.models.audit import AuditEventType
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.signals import SignalRepository

router = APIRouter(prefix="/findings", tags=["findings"])


class SuppressRequest(BaseModel):
    reason: str | None = Field(None, max_length=256)


@router.get("/")
async def get_findings(
    filter_status: Literal["open", "suppressed", "resolved"] = Query(default="open"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Returns findings for the authenticated user.
    filter_status: "open" (default), "suppressed", or "resolved"
    """
    finding_repo = FindingRepository(db)
    signal_repo = SignalRepository(db)

    findings = await finding_repo.get_for_user_by_status(
        user_id=current_user.id,
        status=filter_status,
        limit=limit,
        offset=offset,
    )
    total = await finding_repo.count_for_user_by_status(
        user_id=current_user.id, status=filter_status
    )
    signal_count = await signal_repo.count_open_for_user(current_user.id)

    return {
        "findings": [
            {
                "finding_id": f.finding_id,
                "finding_type": f.finding_type,
                "severity": f.severity,
                "confidence": f.confidence,
                "title": f.title,
                "explanation": f.explanation,
                "rule_name": f.rule_name,
                "status": f.status,
                "contributing_signal_ids": f.contributing_signal_ids,
                "affected_entity_ids": f.affected_entity_ids,
                "created_at": f.created_at.isoformat(),
                "updated_at": f.updated_at.isoformat(),
            }
            for f in findings
        ],
        "signals_open": signal_count,
        "total": total,
        "limit": limit,
        "offset": offset,
        "filter_status": filter_status,
    }


@router.patch("/{finding_id}/suppress", status_code=200)
@limiter.limit("30/minute")
async def suppress_finding(
    request: Request,
    finding_id: str,
    body: SuppressRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Suppresses an open finding.

    It will not appear in the default open findings list.
    """
    finding_repo = FindingRepository(db)
    updated = await finding_repo.suppress(
        user_id=current_user.id, finding_id=finding_id
    )
    if not updated:
        raise HTTPException(
            status_code=404, detail="Finding not found or not in open status"
        )

    audit_repo = AuditRepository(db)
    await audit_repo.log(
        event_type=AuditEventType.FINDING_SUPPRESSED,
        user_id=current_user.id,
        metadata={"finding_id": finding_id, "reason": body.reason},
    )
    await db.commit()
    return {"status": "suppressed", "finding_id": finding_id}


@router.patch("/{finding_id}/unsuppress", status_code=200)
@limiter.limit("30/minute")
async def unsuppress_finding(
    request: Request,
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Restores a suppressed finding to open status."""
    finding_repo = FindingRepository(db)
    updated = await finding_repo.unsuppress(
        user_id=current_user.id, finding_id=finding_id
    )
    if not updated:
        raise HTTPException(
            status_code=404, detail="Finding not found or not in suppressed status"
        )

    audit_repo = AuditRepository(db)
    await audit_repo.log(
        event_type=AuditEventType.FINDING_UNSUPPRESSED,
        user_id=current_user.id,
        metadata={"finding_id": finding_id},
    )
    await db.commit()
    return {"status": "open", "finding_id": finding_id}


@router.patch("/{finding_id}/resolve", status_code=200)
@limiter.limit("30/minute")
async def resolve_finding(
    request: Request,
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Marks an open finding as resolved."""
    finding_repo = FindingRepository(db)
    updated = await finding_repo.resolve(user_id=current_user.id, finding_id=finding_id)
    if not updated:
        raise HTTPException(
            status_code=404, detail="Finding not found or not in open status"
        )

    audit_repo = AuditRepository(db)
    await audit_repo.log(
        event_type=AuditEventType.FINDING_RESOLVED,
        user_id=current_user.id,
        metadata={"finding_id": finding_id},
    )
    await db.commit()
    return {"status": "resolved", "finding_id": finding_id}


@router.patch("/{finding_id}/reopen", status_code=200)
@limiter.limit("30/minute")
async def reopen_finding(
    request: Request,
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Reopens a suppressed or resolved finding."""
    finding_repo = FindingRepository(db)
    updated = await finding_repo.reopen(user_id=current_user.id, finding_id=finding_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Finding not found or already open")

    audit_repo = AuditRepository(db)
    await audit_repo.log(
        event_type=AuditEventType.FINDING_REOPENED,
        user_id=current_user.id,
        metadata={"finding_id": finding_id},
    )
    await db.commit()
    return {"status": "open", "finding_id": finding_id}
