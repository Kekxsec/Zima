# backend/app/providers/content_analysis/social_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_social.py (MIT licensed)
import re
from typing import Any

_SOCIAL_PATTERNS = {
    "twitter": re.compile(
        r"(?:https?://)?(?:www\.)?twitter\.com/([a-zA-Z0-9_]{1,50})", re.IGNORECASE
    ),
    "linkedin": re.compile(
        r"(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([a-zA-Z0-9\-_%]{1,60})",
        re.IGNORECASE,
    ),
    "facebook": re.compile(
        r"(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9.\-]{1,60})", re.IGNORECASE
    ),
    "instagram": re.compile(
        r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9_.]{1,50})", re.IGNORECASE
    ),
    "github": re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9\-]{1,50})", re.IGNORECASE
    ),
    "youtube": re.compile(
        r"(?:https?://)?(?:www\.)?youtube\.com/(?:user|channel|c)/([a-zA-Z0-9_\-]{1,60})",
        re.IGNORECASE,
    ),
    "reddit": re.compile(
        r"(?:https?://)?(?:www\.)?reddit\.com/(?:user|u)/([a-zA-Z0-9_\-]{1,50})",
        re.IGNORECASE,
    ),
}


from backend.app.providers.base.client import BaseProviderClient


class SocialProvider(BaseProviderClient):
    name = "social"

    async def extract_social_links(
        self,
        *,
        domain: str | None = None,
        url: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"web_content", "url", "domain"}:
                continue
            val = _value.strip()
            for platform, pattern in _SOCIAL_PATTERNS.items():
                matches = pattern.findall(val)
                for match in matches[:3]:
                    key = f"{platform}:{match}"
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="social_media",
                            title=f"{platform}: {match}",
                            description=f"{platform} profile found: {match}",
                            entity_type="username",
                            entity_value=match,
                            confidence=0.80,
                            tags=["social", platform, "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Social profile detected: {platform}/{match}",
                            raw={"platform": platform, "username": match},
                            confidence=0.80,
                        )
                    )
        return findings
