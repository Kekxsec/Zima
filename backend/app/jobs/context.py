# backend/app/jobs/context.py
"""
ScanExecutionContext — per-scan execution state.

Lives for the duration of one scan background task. Responsibilities:

1. Memoize provider call results so duplicate fetches within a scan
   (e.g. DeHashed called by breach_monitor and credential_exposure)
   are served from cache rather than hitting the upstream again.

2. Accumulate structured events (provider_allowed, provider_skipped,
   provider_failed, etc.) that are later flushed to the scan_events table.

3. Enforce per-provider and total signal budgets to prevent runaway scans
   from a single loud provider monopolising the results table.

4. Expose summary counters for scan completion logging.

Not thread-safe. Each background task creates its own instance and must
not share it with concurrent tasks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from backend.app.providers.base.models import (
    ProviderPermissionContext,
    ProviderResult,
)

# Cache key: (provider_name, entity_type, entity_value)
_CacheKey = tuple[str, str, str]


@dataclass
class ScanExecutionContext:
    scan_id: uuid.UUID
    user_id: uuid.UUID
    tier: str
    scan_type: str = "full"
    region: str | None = None

    # Signal budget caps — module authors must not exceed these per scan.
    # Caps are enforced by record_signal_emitted(); callers should check
    # get_signal_budget_status() before writing to the DB.
    max_signals_per_provider: int = 50
    max_signals_total: int = 200

    # Internal state — not part of the constructor interface
    _result_cache: dict[_CacheKey, ProviderResult] = field(
        default_factory=dict, init=False, repr=False
    )
    _events: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    # provider_name → count of signals emitted this scan
    _provider_signal_counts: dict[str, int] = field(
        default_factory=dict, init=False, repr=False
    )
    _scan_signal_total: int = field(default=0, init=False, repr=False)

    # Summary counters for logging and scan history
    providers_skipped: int = field(default=0, init=False)
    providers_failed: int = field(default=0, init=False)
    providers_succeeded: int = field(default=0, init=False)
    calls_deduped: int = field(default=0, init=False)

    # ------------------------------------------------------------------ #
    # Provider result cache                                                #
    # ------------------------------------------------------------------ #

    def get_cached(
        self,
        provider: str,
        entity_type: str,
        entity_value: str,
    ) -> ProviderResult | None:
        """Return a previously cached result, or None if not cached."""
        return self._result_cache.get((provider, entity_type, entity_value))

    def cache_result(
        self,
        provider: str,
        entity_type: str,
        entity_value: str,
        result: ProviderResult,
    ) -> None:
        """
        Store a provider result in the cache and update counters.

        If a result is already cached for this key the call is a no-op —
        the counters are NOT incremented a second time.
        """
        key: _CacheKey = (provider, entity_type, entity_value)
        if key in self._result_cache:
            self.calls_deduped += 1
            return
        self._result_cache[key] = result

        if result.skipped:
            self.providers_skipped += 1
        elif result.success:
            self.providers_succeeded += 1
        else:
            self.providers_failed += 1

    # ------------------------------------------------------------------ #
    # Event accumulation                                                   #
    # ------------------------------------------------------------------ #

    def record_event(self, event_type: str, **kwargs: object) -> None:
        """
        Append a structured event to the in-memory buffer.

        Events are flushed to scan_events by the orchestrator after each
        stage. Use drain_events() to retrieve and clear the buffer.

        event_type must match one of the canonical names defined in
        Stage 9.4: scan_started, stage_started, provider_allowed,
        provider_skipped, provider_failed, provider_succeeded,
        signals_upserted, notification_sent, notification_failed,
        scan_completed, scan_failed, scan_marked_stale.
        """
        self._events.append(
            {
                "event_type": event_type,
                "ts": datetime.now(UTC).isoformat(),
                **kwargs,
            }
        )

    def drain_events(self) -> list[dict[str, Any]]:
        """Return accumulated events and clear the buffer."""
        events = list(self._events)
        self._events.clear()
        return events

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def to_permission_context(
        self,
        deny_names: frozenset[str] = frozenset(),
        deny_prefixes: tuple[str, ...] = (),
    ) -> ProviderPermissionContext:
        """Build a ProviderPermissionContext from this scan's settings."""
        return ProviderPermissionContext(
            scan_type=self.scan_type,
            tier=self.tier,
            region=self.region,
            deny_names=deny_names,
            deny_prefixes=deny_prefixes,
        )

    # ------------------------------------------------------------------ #
    # Signal budget                                                        #
    # ------------------------------------------------------------------ #

    def record_signal_emitted(self, provider: str) -> bool:
        """
        Record that one signal is about to be written for the given provider.

        Returns True if the signal is within budget and should be written.
        Returns False if either the per-provider cap or the total scan cap
        has been reached — the caller should skip the upsert and log a
        budget_exceeded event instead.
        """
        provider_count = self._provider_signal_counts.get(provider, 0)
        if provider_count >= self.max_signals_per_provider:
            return False
        if self._scan_signal_total >= self.max_signals_total:
            return False
        self._provider_signal_counts[provider] = provider_count + 1
        self._scan_signal_total += 1
        return True

    def get_signal_budget_status(self) -> dict[str, Any]:
        """Return current budget usage for logging / scan summary."""
        return {
            "scan_total": self._scan_signal_total,
            "scan_cap": self.max_signals_total,
            "provider_counts": dict(self._provider_signal_counts),
            "provider_cap": self.max_signals_per_provider,
        }

    def summary(self) -> dict[str, int]:
        """Return a loggable summary of scan execution statistics."""
        return {
            "providers_succeeded": self.providers_succeeded,
            "providers_failed": self.providers_failed,
            "providers_skipped": self.providers_skipped,
            "calls_deduped": self.calls_deduped,
        }
