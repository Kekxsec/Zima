# backend/app/providers/base/models.py
"""
Shared types for provider execution policy and structured results.

ProviderFinding           — typed shape for a single finding dict returned
                            by a provider mapper.  TypedDict so it remains
                            a dict at runtime — module services may still
                            use dict-style key access.
ProviderResult            — the structured outcome of a single provider call.
ProviderPermissionContext — inputs fed to the policy evaluator per scan.
ProviderPolicyDecision    — allow/deny output from the policy evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, NotRequired, TypedDict


class ProviderFinding(TypedDict, total=False):
    """
    Typed shape for a single normalised finding produced by a provider mapper.

    All fields are optional except ``title`` — not every provider populates
    every field, and module services must handle missing keys gracefully.

    TypedDict is used (rather than a frozen dataclass) so that existing
    module code that accesses findings as plain dicts continues to work
    without modification.  At runtime a ProviderFinding IS a dict.
    """

    title: NotRequired[str]
    description: NotRequired[str | None]
    tags: NotRequired[list[str]]
    raw: NotRequired[dict[str, Any]]
    evidence: NotRequired[dict[str, Any]]


@dataclass(frozen=True)
class ProviderResult:
    """
    Structured outcome of one provider execution against one asset.

    Replaces bare try/except ProviderError blocks in module services.
    success=False + retryable=True means the caller may try again later.
    skipped=True means the provider was intentionally not called
    (missing credentials, policy denial, etc.) — not a failure.

    findings is typed as list[ProviderFinding] — a list of typed dicts.
    Existing module code that reads findings as plain dicts is unaffected
    because ProviderFinding is a TypedDict (subtype of dict at runtime).
    """

    provider: str
    success: bool
    findings: list[ProviderFinding]
    reason: str | None = None
    retryable: bool = False
    skipped: bool = False
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderPermissionContext:
    """
    Inputs supplied to the policy evaluator for one provider execution decision.

    deny_names  — exact provider names to block regardless of credentials.
    deny_prefixes — provider name prefixes to block (e.g. "tools/" blocks all
                    local-tool providers when subprocess execution is disabled).
    """

    scan_type: str
    tier: str
    region: str | None
    deny_names: frozenset[str] = field(default_factory=frozenset)
    deny_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderPolicyDecision:
    """
    Allow/deny decision returned by evaluate_provider_policy.

    allowed=False means the provider must not run.
    reason is a short machine-readable code explaining why.
    """

    allowed: bool
    reason: str | None = None
