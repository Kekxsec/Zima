# backend/app/providers/content_analysis/webserver/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_webserver.py (MIT licensed)
# Copyright (c) Steve Micallef.
import json
import re
from typing import Any

_SERVER_SIGS = [
    ("Apache", re.compile(r"\bApache[/\s]", re.I)),
    ("nginx", re.compile(r"\bnginx[/\s]", re.I)),
    ("IIS", re.compile(r"\bMicrosoft-IIS[/\s]|\bIIS[/\s]", re.I)),
    ("LiteSpeed", re.compile(r"\bLiteSpeed\b", re.I)),
    ("Caddy", re.compile(r"\bCaddy\b", re.I)),
    ("Tomcat", re.compile(r"\bApache-Coyote\b|\bTomcat\b", re.I)),
    ("Gunicorn", re.compile(r"\bgunicorn[/\s]", re.I)),
    ("Jetty", re.compile(r"\bJetty[/\s]", re.I)),
    ("CloudFront", re.compile(r"\bCloudFront\b", re.I)),
    ("Cloudflare", re.compile(r"\bcloudflare\b", re.I)),
]


from backend.app.providers.base.client import BaseProviderClient


class WebserverProvider(BaseProviderClient):
    """Detect web server technology from HTTP response header content."""

    name = "webserver"

    async def detect_server(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        if not content:
            return findings
        try:
            headers = json.loads(content)
            if not isinstance(headers, dict):
                return findings
        except Exception:
            # If not JSON, treat as raw header text
            headers = {"server": content}

        headers_lower = {k.lower(): str(v) for k, v in headers.items()}
        server_val = (
            headers_lower.get("server", "")
            + " "
            + headers_lower.get("x-powered-by", "")
        )

        for label, pattern in _SERVER_SIGS:
            if label in seen:
                continue
            if pattern.search(server_val):
                seen.add(label)
                findings.append(
                    dict(
                        provider=self.name,
                        category="technology_fingerprint",
                        title=f"Web server identified: {label}",
                        description=f"{label} detected in HTTP response headers",
                        entity_type="web_content",
                        entity_value=label,
                        confidence=0.85,
                        tags=[
                            "content_analysis",
                            "webserver",
                            "fingerprint",
                            "passive",
                        ],
                    )
                )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Web server technology identified from headers",
                    raw={"servers": list(seen)},
                    confidence=0.85,
                )
            )

        return findings
