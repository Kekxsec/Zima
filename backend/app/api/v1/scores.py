# backend/app/api/v1/scores.py
import re

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.db.repositories.scores import ScoreRepository

# RFC-compliant domain label: letters, digits, hyphens; no leading/trailing hyphen
_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)
_SPECIAL_SCORE_DOMAINS = {"identity"}

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("")
async def get_scores(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Returns the most recent score per domain for the authenticated user."""
    score_repo = ScoreRepository(db)
    latest = await score_repo.get_latest_for_user(current_user.id)
    return {
        "scores": [
            {
                "domain": s.domain,
                "score": s.score,
                "signal_count": s.signal_count,
                "scorer_version": s.scorer_version,
                "calculated_at": s.calculated_at.isoformat(),
            }
            for s in latest
        ]
    }


@router.get("/{domain}/history")
async def get_score_history(
    domain: str = Path(min_length=3, max_length=253),
    limit: int = Query(default=30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Returns score history for a domain. Used for trend charts."""
    if domain not in _SPECIAL_SCORE_DOMAINS and not _DOMAIN_RE.match(domain):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid domain format.",
        )
    score_repo = ScoreRepository(db)
    history = await score_repo.get_history_for_domain(
        user_id=current_user.id,
        domain=domain,
        limit=limit,
    )
    return {
        "domain": domain,
        "history": [
            {
                "score": s.score,
                "signal_count": s.signal_count,
                "scorer_version": s.scorer_version,
                "calculated_at": s.calculated_at.isoformat(),
            }
            for s in history
        ],
    }
