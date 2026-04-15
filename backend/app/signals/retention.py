# backend/app/signals/retention.py
"""
Evidence retention classes and minimization.

Every signal's evidence is classified into one of three retention tiers
before persistence.  Each tier defines what data survives and for how long.

Retention classes
-----------------
ephemeral_raw
    Raw provider payloads that are useful for debugging but contain PII-heavy
    or high-volume data (e.g. full stealer-log entries, breach record dumps).
    Stored with a TTL tag; subject to periodic cleanup.

durable_product
    Normalised evidence that drives product behaviour — severity decisions,
    remediation actions, dashboard display.  Retained for the user's account
    lifetime or until deletion is requested.

immutable_audit
    Security-critical audit trail: policy decisions, scan events, deletion
    records.  Retained for compliance-mandated periods.  Never modified after
    write.

Usage
-----
Called automatically from ``SignalRepository.upsert()`` to tag and minimise
evidence before DB write.
"""

from __future__ import annotations

import enum
from typing import Any


class RetentionClass(enum.StrEnum):
    EPHEMERAL_RAW = "ephemeral_raw"
    DURABLE_PRODUCT = "durable_product"
    IMMUTABLE_AUDIT = "immutable_audit"


# Keys in evidence dicts that are always safe to keep (product-critical).
_DURABLE_KEYS: frozenset[str] = frozenset(
    {
        "source_provider",
        "platform",
        "site",
        "profile_url",
        "username",
        "carrier",
        "line_type",
        "country",
        "confirmed",
        "reputation_score",
        "suspicious",
        "spam",
        "blacklisted",
        "references",
        "alias_detected",
        "breach_name",
        "breach_date",
        "exposed_data_classes",
        "browser",
        "policy_key",
        "policy_value",
        "extension_id",
        "version",
        "total_risk",
        "risk_breakdown",
        "package_count",
        "scan_target",
        "email_count",
        "registration_confirmed",
        "caller_name",
        "domain",
        "name",
        "job_title",
        "location",
        "linkedin",
        "twitter",
        "verified",
        "severity_reason",
        "sub_key",
        "source_path",
        "syft_schema_version",
    }
)

# Keys that contain raw provider payloads — stripped for ephemeral signals
# before persistence.
_RAW_KEYS: frozenset[str] = frozenset(
    {
        "raw_response",
        "raw_payload",
        "full_record",
        "raw_results",
        "sample_emails",
        "packages",  # can be very large (100s of items)
        "phone_numbers",
        "references",  # emailcrawlr references list can be large
    }
)

# Signal types that produce raw/high-volume evidence.
_EPHEMERAL_SIGNAL_TYPES: frozenset[str] = frozenset(
    {
        "stealer_log_exposure",
        "software_inventory_scan_completed",
        "software_inventory_scan_empty",
    }
)

# Signal types that are audit-grade.
_AUDIT_SIGNAL_TYPES: frozenset[str] = frozenset(
    {
        "scan_completed",
        "scan_failed",
        "gdpr_deletion_completed",
    }
)


def classify_signal(signal_type: str) -> RetentionClass:
    """Determine the retention class for a signal based on its type."""
    if signal_type in _AUDIT_SIGNAL_TYPES:
        return RetentionClass.IMMUTABLE_AUDIT
    if signal_type in _EPHEMERAL_SIGNAL_TYPES:
        return RetentionClass.EPHEMERAL_RAW
    return RetentionClass.DURABLE_PRODUCT


def minimise_evidence(
    evidence: dict[str, Any] | None,
    retention_class: RetentionClass,
) -> dict[str, Any]:
    """Apply retention-class-appropriate minimisation to evidence.

    - DURABLE_PRODUCT: keep all keys (already redacted by redact_evidence).
    - EPHEMERAL_RAW: strip high-volume raw keys, keep summary fields.
    - IMMUTABLE_AUDIT: keep everything (audit records are never trimmed).

    Always tags the result with ``_retention_class`` for downstream cleanup.
    """
    if not evidence:
        return {"_retention_class": retention_class.value}

    result: dict[str, Any]

    if retention_class == RetentionClass.EPHEMERAL_RAW:
        # Keep only durable-safe keys + any small scalar values.
        result = {}
        for k, v in evidence.items():
            if k in _RAW_KEYS:
                # Replace large payloads with a count/summary.
                if isinstance(v, list):
                    result[f"{k}_count"] = len(v)
                else:
                    result[k] = "[minimised]"
            else:
                result[k] = v
    else:
        # DURABLE_PRODUCT and IMMUTABLE_AUDIT: pass through.
        result = dict(evidence)

    result["_retention_class"] = retention_class.value
    return result
