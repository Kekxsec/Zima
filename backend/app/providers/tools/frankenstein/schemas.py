# backend/app/providers/tools/frankenstein/schemas.py
"""Typed schemas for Frankenstein provider raw data and normalised findings."""

from typing import Any, NotRequired, TypedDict


class FrankensteinRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a Frankenstein finding."""

    domain: NotRequired[str]
    status: NotRequired[str]
    dns_a: NotRequired[str | list[str]]
    dns_cname: NotRequired[str]
    dns_mx: NotRequired[str | list[str]]
    dns_ns: NotRequired[str | list[str]]
    http_status: NotRequired[int | str]
    http_title: NotRequired[str]
    http_server: NotRequired[str]
    http_redirect_chain: NotRequired[str | list[str]]
    tls_issuer: NotRequired[str]
    tls_cn: NotRequired[str]
    tls_expiry: NotRequired[str]
    tls_self_signed: NotRequired[bool | int]
    hsts: NotRequired[bool | int]
    x_frame_options: NotRequired[str]
    cache_control: NotRequired[str]
    response_time_ms: NotRequired[int | str]
    extra: NotRequired[dict[str, Any]]


class FrankensteinFinding(TypedDict, total=False):
    """Normalised finding dict returned by FrankensteinProvider."""

    provider: str
    category: str
    entity_type: str
    entity_value: str
    domain: str
    status: str
    is_alive: bool
    is_dns_only: bool
    is_dead: bool
    dns_a: list[str]
    dns_cname: str
    dns_mx: list[str]
    dns_ns: list[str]
    http_status: int | None
    http_title: str
    http_server: str
    http_redirect_chain: list[str]
    tls_issuer: str
    tls_cn: str
    tls_expiry: str | None
    tls_expired: bool
    tls_self_signed: bool
    days_until_expiry: int | None
    hsts: bool
    x_frame_options: str
    cache_control: str
    missing_security_headers: list[str]
    response_time_ms: int | None
    raw: FrankensteinRaw | dict[str, Any]
