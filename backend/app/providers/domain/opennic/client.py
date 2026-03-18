# backend/app/providers/domain/opennic/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_opennic.py (MIT licensed)

OPENNIC_TLDS_URL = "https://servers.opennic.org/metric/?format=json&hidetype=REGISTRY"
_OPENNIC_TLDS = {
    "bbs",
    "chan",
    "cyb",
    "dyn",
    "fur",
    "geek",
    "gopher",
    "indy",
    "libre",
    "neo",
    "null",
    "o",
    "oss",
    "oz",
    "parody",
    "pirate",
    "free",
    "bazar",
    "coin",
    "emc",
    "lib",
    "te",
    "uu",
    "bit",
    "ku",
}


from backend.app.providers.base.client import BaseProviderClient


class OpennicProvider(BaseProviderClient):
    name = "opennic"

    async def resolve_dns(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = domain.strip()
        tld = val.rsplit(".", 1)[-1].lower() if "." in val else ""
        if tld in _OPENNIC_TLDS:
            findings.append(
                dict(
                    provider=self.name,
                    category="network_info",
                    title=f"OpenNIC TLD: {val}",
                    description=f"Domain {val} uses OpenNIC TLD .{tld} (alternative DNS namespace)",
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.85,
                    tags=["opennic", "dns", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"OpenNIC TLD detected for {val}",
                    raw={"tld": tld},
                    confidence=0.85,
                )
            )
        return findings
