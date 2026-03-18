# backend/app/api/v1/findings.py
"""Finding endpoints — implemented in Stage 6."""

from fastapi import APIRouter

router = APIRouter(prefix="/findings", tags=["findings"])
