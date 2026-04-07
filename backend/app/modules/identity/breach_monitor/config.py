# backend/app/modules/identity/breach_monitor/config.py
"""Breach monitor configuration — thresholds and provider weight settings."""

# Minimum number of breach records from a provider before emitting a signal.
# Providers that return 0 records should not produce signals.
MIN_BREACH_RECORDS = 1

# Maximum evidence records stored per signal to cap payload size.
MAX_EVIDENCE_ENTRIES = 20

# Breach providers in priority order (first hit wins for deduplication purposes).
PROVIDER_PRIORITY = ["haveibeenpwned", "dehashed", "leakcheck", "breachdirectory"]
