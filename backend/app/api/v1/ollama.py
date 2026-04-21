# backend/app/api/v1/ollama.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.api.dependencies import get_current_user
from backend.app.auth.models import User
from backend.app.core.config import settings
from backend.app.providers.ai.ollama.client import OllamaProvider

router = APIRouter(prefix="/ollama", tags=["ollama"])


class OllamaStatusResponse(BaseModel):
    enabled: bool
    mode: str
    model: str
    available: bool
    models: list[str]


@router.get("/status", response_model=OllamaStatusResponse)
async def ollama_status(
    _current_user: User = Depends(get_current_user),
) -> OllamaStatusResponse:
    if not settings.ollama_enabled:
        return OllamaStatusResponse(
            enabled=False,
            mode=settings.ollama_mode,
            model=settings.ollama_model,
            available=False,
            models=[],
        )
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
    available = await provider.health_check()
    models = await provider.list_models() if available else []
    return OllamaStatusResponse(
        enabled=True,
        mode=settings.ollama_mode,
        model=settings.ollama_model,
        available=available,
        models=models,
    )
