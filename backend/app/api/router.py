# backend/app/api/router.py
from fastapi import APIRouter

from backend.app.api.v1 import (
    account,
    assets,
    auth,
    billing,
    email_accounts,
    findings,
    health,
    imports,
    integrations,
    legal,
    scans,
    scores,
    signals,
)
from backend.app.billing.webhooks import router as webhooks_router

api_router = APIRouter()

# Health — no prefix, no auth
api_router.include_router(health.router)

# Webhooks — no auth (Stripe signs requests)
api_router.include_router(webhooks_router, prefix="/api/v1")

# Authenticated API endpoints
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(assets.router, prefix="/api/v1")
api_router.include_router(scans.router, prefix="/api/v1")
api_router.include_router(findings.router, prefix="/api/v1")
api_router.include_router(signals.router, prefix="/api/v1")
api_router.include_router(scores.router, prefix="/api/v1")
api_router.include_router(account.router, prefix="/api/v1")
api_router.include_router(billing.router, prefix="/api/v1")
api_router.include_router(legal.router, prefix="/api/v1")
api_router.include_router(email_accounts.router, prefix="/api/v1")
api_router.include_router(imports.router, prefix="/api/v1")
api_router.include_router(integrations.router, prefix="/api/v1")
