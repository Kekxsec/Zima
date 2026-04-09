# backend/app/providers/reputation/emailrep/schemas.py
"""Typed schemas for EmailRep provider raw data and findings."""

from typing import TypedDict


class EmailrepRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in an EmailRep finding."""

    reputation: str
    suspicious: bool
    blacklisted: bool
    spam: bool
    references: int
    profiles: list[str]


class EmailrepFinding(TypedDict, total=False):
    """Normalised finding dict returned by EmailrepProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: EmailrepRaw
