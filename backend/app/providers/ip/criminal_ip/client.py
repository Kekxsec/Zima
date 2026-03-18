# backend/app/providers/ip/criminal_ip/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
import urllib.parse
from typing import Any

_SCORE_SEVERITY_MAP = {
    "critical": "removed_severity",
    "high": "removed_severity",
    "moderate": "removed_severity",
    "low": "removed_severity",
}


def _score_to_severity(score_str: str) -> str:
    return _SCORE_SEVERITY_MAP.get(str(score_str).lower(), "removed_severity")


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CriminalIPProvider(BaseProviderClient):
    """Criminal IP - IP threat intelligence and domain scanning platform."""

    name = "criminal_ip"
    base_url = "https://api.criminalip.io"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_hosts(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Criminal IP API key is required",
                retryable=False,
            )

        findings: list = []
        evidence: list = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type == "ip_address":
                await self._process_ip(_value.strip(), api_key, findings, evidence)
            elif _entity_type == "domain":
                await self._process_domain(_value.strip(), api_key, findings, evidence)

        return findings

    # ------------------------------------------------------------------
    # IP summary
    # ------------------------------------------------------------------

    async def _process_ip(
        self, ip: str, api_key: str, findings: list, evidence: list
    ) -> None:
        params = urllib.parse.urlencode({"ip": ip})
        url = f"{self.base_url}/v1/ip/summary?{params}"

        resp = await self._get(
            url,
            headers={"x-api-key": api_key},
            timeout=self._timeout_seconds,
        )

        if resp.status_code == 402:
            raise ProviderError(
                message="Criminal IP payment/quota exceeded",
                retryable=False,
            )

        self._check_status_errors(resp, "Criminal IP")

        if resp.status_code == 404 or not resp.content.strip():
            return

        if resp.status_code != 200:
            return

        outer = self._parse_json(resp, "Criminal IP")
        data = outer.get("data") or {}

        score = data.get("score") or {}
        inbound_score = str(score.get("inbound", "")).strip()
        outbound_score = str(score.get("outbound", "")).strip()
        severity = _score_to_severity(inbound_score or outbound_score)

        issues = data.get("issues") or {}
        whois = data.get("whois") or {}
        abuse_count = int(data.get("abuse_record_count", 0))

        org_name = str(whois.get("org_name", "")).strip()
        as_name = str(whois.get("as_name", "")).strip()

        # One finding per notable issue
        issue_map = {
            "is_vpn": ("VPN endpoint", "removed_severity"),
            "is_tor": ("Tor exit node", "removed_severity"),
            "is_proxy": ("Open proxy", "removed_severity"),
            "is_cloud": ("Cloud/hosting provider", "removed_severity"),
            "is_hosting": ("Hosting provider", "removed_severity"),
        }

        for issue_key, (issue_label, issue_sev) in issue_map.items():
            if issues.get(issue_key):
                findings.append(
                    dict(
                        provider=self.name,
                        category="infrastructure_intel",
                        title=f"Criminal IP: {ip} flagged as {issue_label}",
                        description=(
                            f"IP {ip} is identified as a {issue_label} by Criminal IP. "
                            f"Inbound score: {inbound_score}. Outbound score: {outbound_score}."
                            + (f" Org: {org_name}." if org_name else "")
                        ),
                        severity=issue_sev,
                        entity_type="ip_address",
                        entity_value=ip,
                        confidence=0.80,
                        tags=["criminal_ip", "ip_reputation", "passive"],
                    )
                )

        # Abuse records finding
        if abuse_count > 0:
            findings.append(
                dict(
                    provider=self.name,
                    category="infrastructure_intel",
                    title=f"Criminal IP: {ip} has {abuse_count} abuse record(s)",
                    description=(
                        f"IP {ip} has {abuse_count} abuse record(s) on Criminal IP. "
                        f"Inbound score: {inbound_score}. Outbound score: {outbound_score}."
                    ),
                    severity=severity,
                    entity_type="ip_address",
                    entity_value=ip,
                    confidence=0.80,
                    tags=["criminal_ip", "ip_reputation", "passive"],
                )
            )

        # Open ports
        port_block = data.get("port_count") or {}
        ports_data = port_block.get("data") or []
        if isinstance(ports_data, list) and ports_data:
            port_summaries = [
                f"{p.get('port')}/{p.get('protocol', 'TCP')} ({p.get('service_name', '')})"
                for p in ports_data[:20]
                if isinstance(p, dict)
            ]
            findings.append(
                dict(
                    provider=self.name,
                    category="infrastructure_intel",
                    title=f"Criminal IP: {len(ports_data)} open port(s) on {ip}",
                    description=f"Open ports on {ip}: {', '.join(port_summaries)}",
                    entity_type="ip_address",
                    entity_value=ip,
                    confidence=0.80,
                    tags=["criminal_ip", "ip_reputation", "passive", "open_ports"],
                )
            )

        evidence.append(
            dict(
                source=self.name,
                description=f"Criminal IP summary for {ip}",
                raw={
                    "ip": ip,
                    "inbound_score": inbound_score,
                    "outbound_score": outbound_score,
                    "issues": issues,
                    "org_name": org_name,
                    "as_name": as_name,
                    "abuse_record_count": abuse_count,
                    "port_count": port_block.get("count", 0),
                },
                confidence=0.80,
            )
        )

    # ------------------------------------------------------------------
    # Domain scan
    # ------------------------------------------------------------------

    async def _process_domain(
        self, domain: str, api_key: str, findings: list, evidence: list
    ) -> None:
        params = urllib.parse.urlencode({"query": domain})
        url = f"{self.base_url}/v1/domain/scan?{params}"

        resp = await self._get(
            url,
            headers={"x-api-key": api_key},
            timeout=self._timeout_seconds,
        )

        if resp.status_code == 402:
            raise ProviderError(
                message="Criminal IP payment/quota exceeded",
                retryable=False,
            )

        self._check_status_errors(resp, "Criminal IP")

        if resp.status_code == 404 or not resp.content.strip():
            return

        if resp.status_code != 200:
            return

        outer = self._parse_json(resp, "Criminal IP")
        data = outer.get("data") or outer

        findings.append(
            dict(
                provider=self.name,
                category="domain_security",
                title=f"Criminal IP domain scan: {domain}",
                description=f"Criminal IP domain scan completed for {domain}.",
                entity_type="domain",
                entity_value=domain,
                confidence=0.80,
                tags=["criminal_ip", "ip_reputation", "passive", "domain_scan"],
            )
        )

        evidence.append(
            dict(
                source=self.name,
                description=f"Criminal IP domain scan data for {domain}",
                raw={"domain": domain, "scan_data": data}
                if not isinstance(data, dict)
                else {"domain": domain, **data},
                confidence=0.80,
            )
        )
