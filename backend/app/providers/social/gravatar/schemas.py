# backend/app/providers/social/gravatar/schemas.py
"""Typed schemas for Gravatar provider enrichment dicts."""

from typing import Any, TypedDict


class GravatarVerifiedAccount(TypedDict, total=False):
    """A verified social account linked to the Gravatar profile."""

    service_type: str
    service_label: str
    url: str


class GravatarEnrichment(TypedDict, total=False):
    """Enrichment dict returned by GravatarProvider.lookup().

    Gravatar is enrichment-only — it does not emit ProviderFindings.
    Consumers use this dict directly for alias correlation and profile enrichment.
    """

    hash: str
    display_name: str | None
    profile_url: str | None
    avatar_url: str | None
    location: str | None
    description: str | None
    job_title: str | None
    company: str | None
    verified_accounts: list[GravatarVerifiedAccount]
    links: list[dict[str, Any]]
    raw: dict[str, Any]
