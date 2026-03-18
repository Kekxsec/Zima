# backend/app/providers/ip/wigle/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_wigle.py (MIT licensed)
import base64
import urllib.parse
from typing import Any

# WiGLE uses BSSID, SSID, or address lookups
_BSSID_ET = "bssid"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class WigleProvider(BaseProviderClient):
    name = "wigle"
    base_url = "https://api.wigle.net/api/v2"

    def __init__(
        self, api_name: str = "", api_token: str = "", timeout_seconds: int = 15
    ):
        self._api_name = api_name
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds

    async def search_wifi(
        self,
        *,
        bssid: str | None = None,
        address: str | None = None,
        ssid: str | None = None,
        wifi_network: str | None = None,
    ) -> list[dict[str, Any]]:
        api_name = str(self._api_name).strip()
        api_token = str(self._api_token).strip()
        if not api_name or not api_token:
            raise ProviderError(
                message="WiGLE API name and token are required", retryable=False
            )
        creds = base64.b64encode(f"{api_name}:{api_token}".encode()).decode()
        headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if bssid is not None:
            _inputs.append(("bssid", bssid))
        if address is not None:
            _inputs.append(("address", address))
        if ssid is not None:
            _inputs.append(("ssid", ssid))
        if wifi_network is not None:
            _inputs.append(("wifi_network", wifi_network))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "bssid":
                params = urllib.parse.urlencode({"netid": val})
            elif _entity_type == "ssid":
                params = urllib.parse.urlencode({"ssid": val})
            elif _entity_type == "physical_address":
                params = urllib.parse.urlencode({"addresscode": val})
            else:
                return findings
            url = f"{self.base_url}/network/search?{params}"
            data = self._fetch(url, headers)
            results = data.get("results", [])
            if not isinstance(results, list):
                continue
            for r in results[:10]:
                if not isinstance(r, dict):
                    continue
                ssid = str(r.get("ssid", "") or "").strip()
                netid = str(r.get("netid", "") or "").strip()
                lat = r.get("trilat")
                lon = r.get("trilong")
                label = f"{ssid} ({netid})" if ssid else netid
                if not label:
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="wifi_network",
                        title=f"WiGLE network: {label}",
                        description=f"WiFi network found at/near {val}: {label}"
                        + (f" at {lat},{lon}" if lat and lon else ""),
                        entity_type="wifi_network",
                        entity_value=label,
                        confidence=0.70,
                        tags=["wigle", "wifi", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"WiGLE results for {val}",
                        raw={"count": len(results)},
                        confidence=0.70,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Wigle", headers=headers, timeout=self._timeout_seconds
        )
