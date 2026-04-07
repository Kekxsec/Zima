# backend/app/providers/base/policy.py
"""
Central provider execution policy.

All allow/deny decisions for provider execution flow through
evaluate_provider_policy. Module services must not inline their own
policy checks — use this function instead.

Inputs are expressed as a ProviderPermissionContext; the caller is
responsible for populating it from scan context, user tier, and settings.
"""

from __future__ import annotations

from backend.app.providers.base.models import (
    ProviderPermissionContext,
    ProviderPolicyDecision,
)


def evaluate_provider_policy(
    provider_name: str,
    has_credentials: bool,
    context: ProviderPermissionContext,
) -> ProviderPolicyDecision:
    """
    Evaluate whether a provider is permitted to run given the current context.

    Checks are applied in priority order — first match wins.

    1. Explicit deny by exact name (deny_names).
    2. Explicit deny by name prefix (deny_prefixes).
       Use prefix "tools/" to block all local-subprocess providers.
    3. Missing credentials — provider cannot run without an API key or
       equivalent credential.

    Returns ProviderPolicyDecision(allowed=True) if all checks pass.
    """
    # 1. Exact name deny list
    if provider_name in context.deny_names:
        return ProviderPolicyDecision(allowed=False, reason="explicitly_denied")

    # 2. Prefix deny list
    for prefix in context.deny_prefixes:
        if provider_name.startswith(prefix):
            return ProviderPolicyDecision(
                allowed=False, reason=f"prefix_denied:{prefix}"
            )

    # 3. Missing credentials
    if not has_credentials:
        return ProviderPolicyDecision(allowed=False, reason="missing_credentials")

    return ProviderPolicyDecision(allowed=True)
