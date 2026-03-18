# backend/app/api/v1/auth.py
"""Auth endpoints — implemented in Stage 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
