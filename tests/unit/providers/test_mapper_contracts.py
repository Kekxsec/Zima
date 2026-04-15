# tests/unit/providers/test_mapper_contracts.py
import pytest

from backend.app.providers.threat_intel.intelx.mapper import (
    to_provider_finding as intelx_to_provider_finding,
)
from backend.app.providers.threat_intel.leakix.mapper import (
    to_provider_finding as leakix_to_provider_finding,
)
from backend.app.providers.tools.frankenstein.mapper import (
    to_provider_finding as frankenstein_to_provider_finding,
)
from backend.app.providers.tools.holehe.mapper import (
    to_provider_finding as holehe_to_provider_finding,
)
from backend.app.providers.tools.maigret.mapper import (
    to_provider_finding as maigret_to_provider_finding,
)
from backend.app.providers.tools.mailcat.mapper import (
    to_provider_finding as mailcat_to_provider_finding,
)
from backend.app.providers.tools.whatsmyname.mapper import (
    to_provider_finding as whatsmyname_to_provider_finding,
)


@pytest.mark.parametrize(
    ("mapper", "finding", "expected_title", "expected_raw"),
    [
        (
            intelx_to_provider_finding,
            {
                "title": "IntelX paste hit",
                "description": "Email found in indexed paste content",
                "tags": ["intelx", "darkweb"],
                "raw": {"storageid": "abc123"},
            },
            "IntelX paste hit",
            {"storageid": "abc123"},
        ),
        (
            mailcat_to_provider_finding,
            {
                "title": "Email discovered: user@example.com",
                "description": "Username 'alice' is associated with user@example.com",
                "tags": ["mailcat"],
                "raw": {"username": "alice", "email": "user@example.com"},
            },
            "Email discovered: user@example.com",
            {"username": "alice", "email": "user@example.com"},
        ),
        (
            holehe_to_provider_finding,
            {
                "title": "Account found: GitHub",
                "description": "Email user@example.com is registered on GitHub",
                "tags": ["holehe"],
                "raw": {"site": "GitHub", "email": "user@example.com"},
            },
            "Account found: GitHub",
            {"site": "GitHub", "email": "user@example.com"},
        ),
        (
            whatsmyname_to_provider_finding,
            {
                "title": "Username found: GitHub",
                "description": "Username 'alice' found on GitHub: https://github.com/alice",
                "tags": ["whatsmyname"],
                "raw": {
                    "site": "GitHub",
                    "url": "https://github.com/alice",
                    "username": "alice",
                },
            },
            "Username found: GitHub",
            {
                "site": "GitHub",
                "url": "https://github.com/alice",
                "username": "alice",
            },
        ),
        (
            maigret_to_provider_finding,
            {
                "title": "Username found: Mastodon",
                "description": "Username alice found on Mastodon: https://fosstodon.org/@alice",
                "tags": ["maigret"],
                "raw": {
                    "site": "Mastodon",
                    "url": "https://fosstodon.org/@alice",
                    "username": "alice",
                },
            },
            "Username found: Mastodon",
            {
                "site": "Mastodon",
                "url": "https://fosstodon.org/@alice",
                "username": "alice",
            },
        ),
    ],
)
def test_existing_stage_10_mappers_preserve_core_contract(
    mapper,
    finding: dict[str, object],
    expected_title: str,
    expected_raw: dict[str, object],
) -> None:
    result = mapper(finding)

    assert result["title"] == expected_title
    assert result["raw"] == expected_raw
    assert "description" in result
    assert "tags" in result


def test_leakix_mapper_derives_contract_from_infrastructure_finding() -> None:
    finding = {
        "host": "grafana.example.com",
        "port": "443",
        "protocol": "https",
        "summary": "Open Grafana instance discovered by crawler",
        "has_leak": True,
        "dataset_rows": 8123,
        "no_auth": True,
        "tags": ["open-database", "no-auth"],
        "raw": {"ip": "203.0.113.10", "host": "grafana.example.com"},
    }

    result = leakix_to_provider_finding(finding)

    assert result["title"] == "LeakIX exposure: https on grafana.example.com:443"
    assert "Open Grafana instance discovered by crawler" in (
        result["description"] or ""
    )
    assert "confirmed leak" in (result["description"] or "")
    assert "Approximate exposed rows: 8123." in (result["description"] or "")
    assert "Tagged as unauthenticated." in (result["description"] or "")
    assert result["tags"] == ["leakix", "open-database", "no-auth"]
    assert result["raw"] == {
        "ip": "203.0.113.10",
        "host": "grafana.example.com",
    }


def test_leakix_mapper_handles_minimal_finding() -> None:
    result = leakix_to_provider_finding({"raw": {}})

    assert result["title"] == "LeakIX exposure: service on unknown host"
    assert result["description"] is None
    assert result["tags"] == ["leakix"]
    assert result["raw"] == {}


def test_frankenstein_mapper_derives_contract_from_posture_finding() -> None:
    finding = {
        "domain": "app.example.com",
        "status": "ALIVE",
        "http_status": 200,
        "days_until_expiry": 14,
        "missing_security_headers": [
            "Strict-Transport-Security",
            "X-Frame-Options",
        ],
        "raw": {"domain": "app.example.com", "status": "ALIVE"},
    }

    result = frankenstein_to_provider_finding(finding)

    assert result["title"] == "Frankenstein posture: app.example.com (ALIVE)"
    assert "HTTP status 200." in (result["description"] or "")
    assert "TLS certificate expires in 14 days." in (result["description"] or "")
    assert "Missing security headers: Strict-Transport-Security, X-Frame-Options." in (
        result["description"] or ""
    )
    assert result["tags"] == ["frankenstein", "alive", "missing_security_headers"]
    assert result["raw"] == {
        "domain": "app.example.com",
        "status": "ALIVE",
    }


def test_frankenstein_mapper_handles_dns_only_tls_failure() -> None:
    finding = {
        "domain": "stale.example.com",
        "status": "DNS-ONLY",
        "is_dns_only": True,
        "tls_expired": True,
        "raw": {"domain": "stale.example.com", "status": "DNS-ONLY"},
    }

    result = frankenstein_to_provider_finding(finding)

    assert result["title"] == "Frankenstein posture: stale.example.com (DNS-ONLY)"
    assert "Domain resolves in DNS but did not answer HTTP/S probes." in (
        result["description"] or ""
    )
    assert "TLS certificate is expired." in (result["description"] or "")
    assert result["tags"] == [
        "frankenstein",
        "dns-only",
        "tls_expired",
        "dns_only",
    ]
