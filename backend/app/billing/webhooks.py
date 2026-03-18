# backend/app/billing/webhooks.py
"""Stripe webhook handlers — implemented in Stage 7."""

from fastapi import APIRouter

router = APIRouter(tags=["webhooks"])
