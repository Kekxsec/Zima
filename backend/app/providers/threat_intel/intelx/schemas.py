# backend/app/providers/threat_intel/intelx/schemas.py
"""Typed schemas for IntelX provider raw data and normalised findings."""

from typing import Any, NotRequired, TypedDict


class IntelXRaw(TypedDict, total=False):
    """Shape of one raw record returned by the IntelX search result endpoint."""

    storageid: NotRequired[str]
    media: NotRequired[int]
    bucket: NotRequired[str]
    date: NotRequired[str]
    name: NotRequired[str]


class IntelXFinding(TypedDict, total=False):
    """Normalised finding dict returned by IntelXProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: dict[str, Any]
