# backend/app/providers/tools/maigret/schemas.py
"""Typed schemas for Maigret provider raw data and normalised findings."""

from typing import NotRequired, TypedDict


class MaigretRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a Maigret finding."""

    site: NotRequired[str]
    url: NotRequired[str]
    username: NotRequired[str]


class MaigretFinding(TypedDict, total=False):
    """Normalised finding dict returned by MaigretProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: MaigretRaw
