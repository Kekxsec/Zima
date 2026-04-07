# backend/app/modules/identity/breach_monitor/mapper.py
"""Map raw provider findings to structured evidence dicts for breach_monitor signals."""

from typing import Any


def hibp_to_evidence(finding: dict[str, Any]) -> dict[str, Any]:
    """Convert a HIBP provider finding to a BreachEvidence-compatible dict."""
    raw: dict[str, Any] = (
        finding.get("raw", {}) if isinstance(finding.get("raw"), dict) else {}
    )
    return {
        "source_provider": "haveibeenpwned",
        "breach_name": raw.get("breach_name"),
        "breach_date": raw.get("breach_date"),
        "data_classes": raw.get("data_classes", []),
        "has_plaintext": False,
        "has_hash": False,
        "total_records": 1,
        "raw_finding": finding,
    }


def dehashed_to_evidence(
    finding: dict[str, Any],
    entries: list[dict[str, Any]],
    total: int,
) -> dict[str, Any]:
    """Convert DeHashed findings to evidence dict."""
    has_plaintext = any(bool(e.get("password")) for e in entries if isinstance(e, dict))
    has_hash = any(
        bool(e.get("hashed_password")) for e in entries if isinstance(e, dict)
    )
    return {
        "source_provider": "dehashed",
        "breach_name": finding.get("title"),
        "breach_date": None,
        "data_classes": [],
        "has_plaintext": has_plaintext,
        "has_hash": has_hash,
        "total_records": total,
        "raw_finding": finding,
    }


def breachdirectory_to_evidence(finding: dict[str, Any]) -> dict[str, Any]:
    """Convert BreachDirectory finding to evidence dict."""
    raw: dict[str, Any] = (
        finding.get("raw", {}) if isinstance(finding.get("raw"), dict) else {}
    )
    return {
        "source_provider": "breachdirectory",
        "breach_name": finding.get("title"),
        "breach_date": None,
        "data_classes": [],
        "has_plaintext": bool(raw.get("has_plaintext")),
        "has_hash": bool(raw.get("is_hash")),
        "total_records": 1,
        "raw_finding": finding,
    }
