# backend/app/api/v1/onboarding.py
"""Onboarding endpoints — implemented in Stage 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
