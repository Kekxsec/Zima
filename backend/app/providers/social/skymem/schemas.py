# backend/app/providers/social/skymem/schemas.py
"""Typed schemas for Skymem provider findings."""

from typing import TypedDict


class SkymemFinding(TypedDict, total=False):
    """Normalised finding dict returned by SkymemProvider.

    Note: Skymem findings carry a ``confidence`` float and no ``raw`` dict.
    The mapper normalises these to ProviderFinding by supplying an empty raw.
    """

    provider: str
    category: str
    title: str
    description: str
    entity_type: str
    entity_value: str
    confidence: float
    tags: list[str]
