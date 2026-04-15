# backend/app/providers/tools/holehe/schemas.py
"""Typed schemas for Holehe provider raw data and normalised findings."""

from typing import NotRequired, TypedDict


class HoleheRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a Holehe finding."""

    site: NotRequired[str]
    email: NotRequired[str]


class HoleheFinding(TypedDict, total=False):
    """Normalised finding dict returned by HoleheProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: HoleheRaw
