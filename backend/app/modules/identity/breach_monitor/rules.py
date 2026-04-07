# backend/app/modules/identity/breach_monitor/rules.py
"""Severity decision rules for the breach_monitor module."""

from typing import Any

from backend.app.core.enums import Severity


def breach_severity_hibp(_raw: dict[str, Any]) -> Severity:
    """HIBP does not expose password data — always HIGH."""
    return Severity.HIGH


def breach_severity_dehashed(entries: list[dict[str, Any]]) -> Severity:
    """CRITICAL if any entry exposes a plaintext or hashed password; HIGH otherwise."""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("password") or entry.get("hashed_password"):
            return Severity.CRITICAL
    return Severity.HIGH


def breach_severity_breachdirectory(raw: dict[str, Any]) -> Severity:
    """CRITICAL if plaintext password present; HIGH otherwise."""
    if raw.get("has_plaintext"):
        return Severity.CRITICAL
    return Severity.HIGH


def breach_severity_leakcheck(raw: dict[str, Any]) -> Severity:
    """CRITICAL if leaked field type is plaintext; HIGH for hash."""
    leak_type = str(raw.get("type", "")).lower()
    if "plain" in leak_type:
        return Severity.CRITICAL
    return Severity.HIGH
