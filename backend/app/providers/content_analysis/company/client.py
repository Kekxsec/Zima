# backend/app/providers/content_analysis/company/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_company.py (MIT licensed)
import re
from typing import Any

# Common company suffixes for regex matching
_SUFFIXES = r"(?:Inc\.?|LLC\.?|Ltd\.?|Limited|Corp\.?|Corporation|Co\.?|Company|PLC|GmbH|S\.A\.?|B\.V\.?|AG|SE|SAS|SARL|NV|KK)"
_COMPANY_RE = re.compile(
    r"(?<!\w)([A-Z][a-zA-Z0-9&\-\s]{2,40}\s+" + _SUFFIXES + r")(?!\w)", re.MULTILINE
)


from backend.app.providers.base.client import BaseProviderClient


class CompanyProvider(BaseProviderClient):
    name = "company"

    async def detect_company(
        self, *, domain: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"web_content", "ssl_certificate_issued", "domain"}:
                continue
            val = _value.strip()
            matches = _COMPANY_RE.findall(val)
            for match in matches[:20]:
                name = match.strip()
                if not name or name in seen or len(name) < 5:
                    continue
                seen.add(name)
                findings.append(
                    dict(
                        provider=self.name,
                        category="corporate_info",
                        title=f"Company name: {name}",
                        description=f"Company name extracted: {name}",
                        entity_type="human_name",
                        entity_value=name,
                        confidence=0.55,
                        tags=["company", "corporate", "passive"],
                    )
                )
            if matches:
                evidence.append(
                    dict(
                        source=self.name,
                        description="Company names extracted from content",
                        raw={"count": len(set(m.strip() for m in matches))},
                        confidence=0.55,
                    )
                )
        return findings
