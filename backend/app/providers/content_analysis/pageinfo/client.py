# backend/app/providers/content_analysis/pageinfo/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_pageinfo.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

_TITLE_RE = re.compile(r"<title[^>]*>([^<]{1,200})</title>", re.I)
_FORM_RE = re.compile(r"<form\b", re.I)
_LOGIN_RE = re.compile(
    r"""(?:type=["']password["']|name=["']password["']|id=["']password["'])""", re.I
)
_SCRIPT_RE = re.compile(r"<script\b", re.I)
_IFRAME_RE = re.compile(r"<iframe\b", re.I)
_INPUT_RE = re.compile(r"<input\b", re.I)
_LINK_RE = re.compile(r'href=["\']([^"\'<>]{1,500})["\']', re.I)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")


from backend.app.providers.base.client import BaseProviderClient


class PageinfoProvider(BaseProviderClient):
    name = "pageinfo"

    async def get_page_info(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []

        if not content:
            return findings
        content = content

        meta: dict = {}

        title_match = _TITLE_RE.search(content)
        if title_match:
            meta["title"] = title_match.group(1).strip()

        meta["has_forms"] = bool(_FORM_RE.search(content))
        meta["has_login"] = bool(_LOGIN_RE.search(content))
        meta["has_scripts"] = bool(_SCRIPT_RE.search(content))
        meta["has_iframes"] = bool(_IFRAME_RE.search(content))
        meta["input_count"] = len(_INPUT_RE.findall(content))
        meta["link_count"] = len(_LINK_RE.findall(content))
        meta["email_count"] = len(_EMAIL_RE.findall(content))

        if meta.get("has_login"):
            findings.append(
                dict(
                    provider=self.name,
                    category="page_characteristics",
                    title="Login form detected on page",
                    description="Page contains a password input field (potential login form)",
                    entity_type="web_content",
                    entity_value=meta.get("title", ""),
                    confidence=0.75,
                    tags=["pageinfo", "login_form", "passive"],
                )
            )
        if meta.get("has_iframes"):
            findings.append(
                dict(
                    provider=self.name,
                    category="page_characteristics",
                    title="iFrame detected on page",
                    description="Page embeds one or more iFrames",
                    entity_type="web_content",
                    entity_value=meta.get("title", ""),
                    confidence=0.70,
                    tags=["pageinfo", "iframe", "passive"],
                )
            )

        evidence.append(
            dict(
                source=self.name,
                description="Page characteristics extracted",
                raw=meta,
                confidence=0.70,
            )
        )

        return findings
