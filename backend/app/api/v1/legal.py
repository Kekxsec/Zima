# backend/app/api/v1/legal.py
from fastapi import APIRouter

from backend.app.core.config import settings

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/privacy")
async def privacy_policy() -> dict[str, str]:
    return {"url": f"{settings.frontend_base_url}/privacy"}


@router.get("/terms")
async def terms_of_service() -> dict[str, str]:
    return {"url": f"{settings.frontend_base_url}/terms"}
