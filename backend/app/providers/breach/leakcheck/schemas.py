# backend/app/providers/breach/leakcheck/schemas.py
"""Typed schemas for LeakCheck provider raw data and normalised findings."""

from typing import NotRequired, TypedDict


class LeakCheckRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a LeakCheck finding."""

    breach_name: str
    breach_date: str
    columns: list[str]
    has_password: bool
    entries: NotRequired[int | None]


class LeakCheckFinding(TypedDict, total=False):
    """Normalised finding dict returned by LeakCheckProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: LeakCheckRaw
