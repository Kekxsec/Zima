# backend/app/api/v1/signals.py
"""Signal endpoints — implemented in Stage 6."""

from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["signals"])
