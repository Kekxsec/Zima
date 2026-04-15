# backend/app/api/v1/findings.py
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.rate_limit import limiter
from backend.app.correlation.models import Finding
from backend.app.db.models.audit import AuditEventType
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.findings import FindingRepository
from backend.app.db.repositories.signals import SignalRepository
from backend.app.signals.models import Signal

router = APIRouter(prefix="/findings", tags=["findings"])

_CONFIDENCE_SCORES: dict[str, float] = {
    "low": 0.45,
    "medium": 0.7,
    "high": 0.92,
}


def _confidence_to_score(value: str) -> float:
    return _CONFIDENCE_SCORES.get(value.lower(), 0.5)


def _extract_breach_details(
    signal_evidence: dict[str, object] | None,
) -> tuple[str | None, str | None, list[str]]:
    if not isinstance(signal_evidence, dict):
        return None, None, []

    raw_finding = signal_evidence.get("raw_finding")
    raw_value = raw_finding.get("raw") if isinstance(raw_finding, dict) else None
    raw_payload: dict[str, object] = raw_value if isinstance(raw_value, dict) else {}

    breach_name = (
        signal_evidence.get("breach_name") or raw_payload.get("breach_name") or None
    )
    breach_date = (
        signal_evidence.get("breach_date") or raw_payload.get("breach_date") or None
    )
    data_classes_raw = (
        signal_evidence.get("data_classes")
        or signal_evidence.get("exposed_data_classes")
        or raw_payload.get("data_classes")
        or []
    )
    data_classes = (
        [str(item) for item in data_classes_raw if isinstance(item, str)]
        if isinstance(data_classes_raw, list)
        else []
    )

    return (
        str(breach_name) if breach_name else None,
        str(breach_date) if breach_date else None,
        data_classes,
    )


def _serialize_supporting_signal(signal: Signal) -> dict[str, object]:
    breach_name, breach_date, data_classes = _extract_breach_details(
        getattr(signal, "evidence", None)
    )
    return {
        "signal_id": signal.signal_id,
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "provider": signal.provider,
        "source": signal.source,
        "summary": signal.summary,
        "details": signal.details,
        "entity_type": signal.entity_type,
        "entity_value": signal.entity_value,
        "recommended_action": signal.recommended_action,
        "breach_name": breach_name,
        "breach_date": breach_date,
        "data_classes": data_classes,
    }


def _serialize_impacted_breaches(signals: list[Signal]) -> list[dict[str, object]]:
    seen: set[tuple[str, str, str | None, str, str]] = set()
    impacted: list[dict[str, object]] = []

    for signal in signals:
        breach_name, breach_date, data_classes = _extract_breach_details(
            getattr(signal, "evidence", None)
        )
        if not breach_name:
            continue

        key = (
            signal.entity_value,
            breach_name,
            breach_date,
            signal.provider,
            signal.signal_type,
        )
        if key in seen:
            continue
        seen.add(key)

        impacted.append(
            {
                "email": signal.entity_value,
                "breach_name": breach_name,
                "breach_date": breach_date,
                "provider": signal.provider,
                "signal_type": signal.signal_type,
                "summary": signal.summary,
                "data_classes": data_classes,
            }
        )

    return impacted


class SuppressRequest(BaseModel):
    reason: str | None = Field(None, max_length=256)


@router.get("")
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
    asset_repo = AssetRepository(db)

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

    contributing_signal_ids = list(
        {
            signal_id
            for finding in findings
            for signal_id in finding.contributing_signal_ids
        }
    )
    affected_entity_ids = [
        entity_id
        for entity_id in {
            entity_id
            for finding in findings
            for entity_id in finding.affected_entity_ids
        }
        if isinstance(entity_id, str)
    ]

    supporting_signals = await signal_repo.get_by_signal_ids_for_user(
        user_id=current_user.id,
        signal_ids=contributing_signal_ids,
    )
    signal_map = {signal.signal_id: signal for signal in supporting_signals}

    asset_uuids: list[uuid.UUID] = []
    for entity_id in affected_entity_ids:
        try:
            asset_uuids.append(uuid.UUID(entity_id))
        except ValueError:
            continue
    affected_assets = await asset_repo.get_by_ids_for_user(
        user_id=current_user.id,
        asset_ids=asset_uuids,
    )
    asset_map = {str(asset.id): asset for asset in affected_assets}

    def _build_finding_row(f: Finding) -> dict[str, object]:
        finding_signals = [
            signal
            for signal_id in f.contributing_signal_ids
            if (signal := signal_map.get(signal_id)) is not None
        ]
        return {
            "finding_id": f.finding_id,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "confidence": _confidence_to_score(f.confidence),
            "confidence_label": f.confidence,
            "title": f.title,
            "explanation": f.explanation,
            "rule_name": f.rule_name,
            "status": f.status,
            "contributing_signal_ids": f.contributing_signal_ids,
            "affected_entity_ids": f.affected_entity_ids,
            "recommended_actions": list(
                dict.fromkeys(
                    signal.recommended_action
                    for signal in finding_signals
                    if signal.recommended_action
                )
            ),
            "supporting_signals": [
                _serialize_supporting_signal(signal) for signal in finding_signals
            ],
            "impacted_breaches": _serialize_impacted_breaches(finding_signals),
            "affected_entities": [
                {
                    "id": str(asset.id),
                    "entity_type": asset.entity_type,
                    "value": asset.value,
                    "is_primary": asset.is_primary,
                    "is_verified": asset.is_verified,
                }
                for entity_id in f.affected_entity_ids
                if (asset := asset_map.get(entity_id)) is not None
            ],
            "created_at": f.created_at.isoformat(),
            "updated_at": f.updated_at.isoformat(),
        }

    return {
        "findings": [_build_finding_row(f) for f in findings],
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
