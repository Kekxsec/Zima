# backend/app/api/v1/scores.py
"""Score endpoints — implemented in Stage 6."""

from fastapi import APIRouter

router = APIRouter(prefix="/scores", tags=["scores"])
