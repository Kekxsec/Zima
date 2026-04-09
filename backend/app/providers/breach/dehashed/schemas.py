# backend/app/providers/breach/dehashed/schemas.py
"""Typed schemas for DeHashed provider raw data and normalised findings."""

from typing import Any, NotRequired, TypedDict


class DehashedEntry(TypedDict, total=False):
    """One scrubbed record from the DeHashed API (passwords stripped)."""

    id: NotRequired[str]
    email: NotRequired[str]
    ip_address: NotRequired[str]
    username: NotRequired[str]
    address: NotRequired[str]
    phone: NotRequired[str]
    name: NotRequired[str]
    vin: NotRequired[str]
    database_name: NotRequired[str]


class DehashedRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a DeHashed finding."""

    total: int
    sample_count: int
    entries: list[dict[str, Any]]
    has_plaintext: bool
    has_hash: bool


class DehashedFinding(TypedDict, total=False):
    """Normalised finding dict returned by DehashedProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: DehashedRaw
