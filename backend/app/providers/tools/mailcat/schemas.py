# backend/app/providers/tools/mailcat/schemas.py
"""Typed schemas for Mailcat provider raw data and normalised findings."""

from typing import NotRequired, TypedDict


class MailcatRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a Mailcat finding."""

    username: NotRequired[str]
    email: NotRequired[str]


class MailcatFinding(TypedDict, total=False):
    """Normalised finding dict returned by MailcatProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: MailcatRaw
