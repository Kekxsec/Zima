# backend/app/providers/tools/whatsmyname/schemas.py
"""Typed schemas for WhatsmyName (Sherlock) provider raw data and normalised findings."""

from typing import NotRequired, TypedDict


class WhatsmynameRaw(TypedDict, total=False):
    """Shape of the ``raw`` dict embedded in a WhatsmyName finding."""

    site: NotRequired[str]
    url: NotRequired[str]
    username: NotRequired[str]


class WhatsmynameFinding(TypedDict, total=False):
    """Normalised finding dict returned by WhatsmyNameProvider."""

    provider: str
    category: str
    title: str
    description: str | None
    entity_type: str
    entity_value: str
    tags: list[str]
    raw: WhatsmynameRaw
