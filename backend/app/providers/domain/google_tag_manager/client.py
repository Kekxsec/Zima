# backend/app/providers/domain/google_tag_manager/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_google_tag_manager.py (MIT licensed)
import re
from typing import Any

_GTM_RE = re.compile(r"GTM-[A-Z0-9]{4,8}", re.IGNORECASE)
_GA_RE = re.compile(r"(?:UA|G)-\d{5,12}(?:-\d+)?", re.IGNORECASE)


from backend.app.providers.base.client import BaseProviderClient


class GoogleTagManagerProvider(BaseProviderClient):
    name = "google_tag_manager"

    async def find_similar(self, url: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        val = url.strip()
        gtm_ids = _GTM_RE.findall(val)
        ga_ids = _GA_RE.findall(val)
        for tid in list(dict.fromkeys(gtm_ids + ga_ids))[:10]:
            if tid in seen:
                continue
            seen.add(tid)
            is_gtm = tid.startswith("GTM-")
            label = "Google Tag Manager ID" if is_gtm else "Google Analytics ID"
            findings.append(
                dict(
                    provider=self.name,
                    category="tracking",
                    title=f"{label}: {tid}",
                    description=f"{label} found in content: {tid}",
                    entity_type="analytics_id",
                    entity_value=tid,
                    confidence=0.90,
                    tags=["google_tag_manager", "tracking", "passive"],
                )
            )
            if gtm_ids or ga_ids:
                evidence.append(
                    dict(
                        source=self.name,
                        description="Google tracking IDs extracted",
                        raw={
                            "gtm": list(dict.fromkeys(gtm_ids)),
                            "ga": list(dict.fromkeys(ga_ids)),
                        },
                        confidence=0.90,
                    )
                )
        return findings
