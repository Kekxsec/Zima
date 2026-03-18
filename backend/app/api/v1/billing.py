# backend/app/api/v1/billing.py
"""Billing endpoints — implemented in Stage 7."""

from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["billing"])
