# backend/app/providers/breach/breachdirectory/schemas.py
"""Typed schemas for BreachDirectory provider raw data and findings."""

from typing import TypedDict


class BreachDirectoryRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a BreachDirectory finding."""

    sources: list[str]
    has_password: bool
    has_plaintext: bool
    is_hash: bool


class BreachDirectoryFinding(TypedDict, total=False):
    """Normalised finding dict returned by BreachDirectoryProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: BreachDirectoryRaw
