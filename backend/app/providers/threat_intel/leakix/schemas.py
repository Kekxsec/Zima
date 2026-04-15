# backend/app/providers/threat_intel/leakix/schemas.py
"""Typed schemas for LeakIX provider raw data and normalised findings."""

from typing import Any, NotRequired, TypedDict


class LeakIXRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a LeakIX finding."""

    ip: NotRequired[str]
    host: NotRequired[str]
    port: NotRequired[int | str]
    protocol: NotRequired[str]
    summary: NotRequired[str]
    time: NotRequired[str]
    tags: NotRequired[list[str]]
    leak: NotRequired[dict[str, Any]]
    geoip: NotRequired[dict[str, Any]]
    ssl: NotRequired[dict[str, Any]]
    http: NotRequired[dict[str, Any]]


class LeakIXFinding(TypedDict, total=False):
    """Normalised finding dict returned by LeakIXProvider."""

    provider: str
    category: str
    entity_type: str
    entity_value: str
    ip: str
    host: str
    port: str
    protocol: str
    transport: list[str]
    summary: str
    time: str
    has_leak: bool
    leak_severity: str
    dataset_rows: int
    dataset_size_bytes: int
    dataset_collections: int
    country: str
    as_name: str
    as_num: int | None
    ssl_detected: bool
    ssl_enabled: bool
    http_status: int | None
    http_title: str
    tags: list[str]
    no_auth: bool
    raw: LeakIXRaw | dict[str, Any]
