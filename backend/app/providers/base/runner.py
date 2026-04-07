# backend/app/providers/base/runner.py
"""
Centralised provider execution helper.

run_provider() replaces the repeated try/except ProviderError blocks that
previously lived in every module service. It handles:

1. Policy check via evaluate_provider_policy()
2. ScanExecutionContext cache lookup (dedupe within a scan)
3. Quota enforcement via ProviderQuotaGuard
4. Provider call with structured error capture
5. Result caching + event recording on the ScanExecutionContext

Module services call this once per provider and get back a ProviderResult
they can inspect without any exception handling.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from backend.app.core.logging import get_logger
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.base.models import (
    ProviderFinding,
    ProviderPolicyDecision,
    ProviderResult,
)
from backend.app.providers.base.policy import evaluate_provider_policy
from backend.app.providers.base.quota import ProviderQuotaGuard

logger = get_logger(__name__)

# Shared quota guard instance — safe to reuse (stateless aside from Redis).
_quota_guard = ProviderQuotaGuard()


async def run_provider(
    *,
    provider_name: str,
    call: Callable[[], Awaitable[list[dict[str, Any]]]],
    has_credentials: bool,
    user_id: uuid.UUID,
    entity_type: str,
    entity_value: str,
    ctx: Any | None = None,
    check_quota: bool = False,
) -> ProviderResult:
    """
    Execute a single provider call with policy, cache, quota, and error handling.

    Parameters
    ----------
    provider_name:
        Canonical provider name matching the registry (e.g. "dehashed").
    call:
        Zero-arg async callable that returns ``list[dict[str, Any]]``.
        The caller is responsible for constructing the provider instance
        and binding arguments before passing the callable.
    has_credentials:
        Whether the required credentials for this provider are present.
    user_id:
        Current user — used for quota keys and event metadata.
    entity_type:
        Asset entity type (e.g. "email", "username").
    entity_value:
        Asset value being scanned.
    ctx:
        Optional ``ScanExecutionContext``.  When present, results are
        cached and events are recorded.
    check_quota:
        If True, run a ProviderQuotaGuard check before calling.

    Returns
    -------
    ProviderResult
        Structured outcome.  Callers inspect ``.success`` and
        ``.findings`` — no exception handling needed.
    """
    # Import here to avoid circular dependency (context → models → ... → runner)
    from backend.app.jobs.context import ScanExecutionContext

    scan_ctx: ScanExecutionContext | None = (
        ctx if isinstance(ctx, ScanExecutionContext) else None
    )

    # ── 1. Cache lookup ─────────────────────────────────────────────────
    if scan_ctx is not None:
        cached = scan_ctx.get_cached(provider_name, entity_type, entity_value)
        if cached is not None:
            scan_ctx.calls_deduped += 1
            return cached

    # ── 2. Policy check ─────────────────────────────────────────────────
    if scan_ctx is not None:
        perm_ctx = scan_ctx.to_permission_context()
    else:
        from backend.app.providers.base.models import ProviderPermissionContext

        perm_ctx = ProviderPermissionContext(scan_type="full", tier="core", region=None)

    decision: ProviderPolicyDecision = evaluate_provider_policy(
        provider_name=provider_name,
        has_credentials=has_credentials,
        context=perm_ctx,
    )

    if not decision.allowed:
        result = ProviderResult(
            provider=provider_name,
            success=False,
            findings=[],
            reason=decision.reason,
            skipped=True,
        )
        if scan_ctx is not None:
            scan_ctx.cache_result(provider_name, entity_type, entity_value, result)
            scan_ctx.record_event(
                "provider_skipped",
                provider=provider_name,
                reason=decision.reason,
            )
        logger.info(
            "run_provider.skipped",
            provider=provider_name,
            reason=decision.reason,
        )
        return result

    # ── 3. Quota check ──────────────────────────────────────────────────
    if check_quota:
        allowed = await _quota_guard.check_and_increment(user_id, provider_name)
        if not allowed:
            result = ProviderResult(
                provider=provider_name,
                success=False,
                findings=[],
                reason="quota_exceeded",
                skipped=True,
            )
            if scan_ctx is not None:
                scan_ctx.cache_result(provider_name, entity_type, entity_value, result)
                scan_ctx.record_event(
                    "provider_skipped",
                    provider=provider_name,
                    reason="quota_exceeded",
                )
            logger.warning(
                "run_provider.quota_exceeded",
                provider=provider_name,
                user_id=str(user_id),
            )
            return result

    # ── 4. Execute provider ─────────────────────────────────────────────
    try:
        raw_findings = await call()
    except ProviderError as exc:
        result = ProviderResult(
            provider=provider_name,
            success=False,
            findings=[],
            reason=str(exc),
            retryable=exc.retryable,
        )
        if scan_ctx is not None:
            scan_ctx.cache_result(provider_name, entity_type, entity_value, result)
            scan_ctx.record_event(
                "provider_failed",
                provider=provider_name,
                reason=str(exc)[:256],
                retryable=exc.retryable,
            )
        logger.error(
            "run_provider.provider_error",
            provider=provider_name,
            error=str(exc),
            retryable=exc.retryable,
        )
        return result

    # Normalise: providers may return None or a single dict instead of a list.
    # Cast to list[ProviderFinding] — ProviderFinding is a TypedDict (subtype
    # of dict at runtime) so existing module services retain dict-style access.
    findings: list[ProviderFinding]
    if raw_findings is None:
        findings = []
    elif isinstance(raw_findings, dict):
        findings = [raw_findings]  # type: ignore[list-item]
    else:
        findings = list(raw_findings)  # type: ignore[arg-type]

    # ── 5. Success ──────────────────────────────────────────────────────
    result = ProviderResult(
        provider=provider_name,
        success=True,
        findings=findings,
        metadata={"finding_count": len(findings)},
    )
    if scan_ctx is not None:
        scan_ctx.cache_result(provider_name, entity_type, entity_value, result)
        scan_ctx.record_event(
            "provider_succeeded",
            provider=provider_name,
            finding_count=len(findings),
        )

    return result
