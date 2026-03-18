# backend/app/api/v1/legal.py
"""Legal endpoints — implemented in Stage 7."""

from fastapi import APIRouter

router = APIRouter(prefix="/legal", tags=["legal"])
