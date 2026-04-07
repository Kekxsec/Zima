# backend/app/modules/identity/breach_monitor/schemas.py
"""Typed schemas for breach monitor provider findings."""

from typing import Any, TypedDict


class BreachFinding(TypedDict):
    """Normalised finding dict returned by a breach provider."""

    title: str
    description: str | None
    provider: str
    raw: dict[str, Any]
    tags: list[str]


class BreachEvidence(TypedDict):
    """Evidence dict attached to a breach_monitor signal."""

    source_provider: str
    breach_name: str | None
    breach_date: str | None
    data_classes: list[str]
    has_plaintext: bool
    has_hash: bool
    total_records: int
    raw_finding: dict[str, Any]
