# backend/app/api/v1/scans.py
"""Scan endpoints — implemented in Stage 6."""

from fastapi import APIRouter

router = APIRouter(prefix="/scans", tags=["scans"])
