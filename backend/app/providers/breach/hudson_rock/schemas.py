# backend/app/providers/breach/hudson_rock/schemas.py
"""Typed schemas for Hudson Rock Cavalier provider raw data and findings."""

from typing import TypedDict


class HudsonRockRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a Hudson Rock finding.

    Email queries populate ``malware_name`` and ``credential_count``.
    Domain queries populate ``stealer_count`` in place of ``malware_name``.
    """

    date_uploaded: str
    computer_name: str
    operating_system: str
    malware_name: str
    credential_count: int
    stealer_count: int


class HudsonRockFinding(TypedDict, total=False):
    """Normalised finding dict returned by HudsonRockProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: HudsonRockRaw
