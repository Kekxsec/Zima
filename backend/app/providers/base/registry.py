# backend/app/providers/base/registry.py
"""
Provider metadata registry.

Static metadata describing every provider that Zima can run against.
This is a lookup layer, not a plugin system.  It is used by:

  - the execution policy to classify providers before allowing them to run
  - scan history events to attach structured metadata to provider outcomes
  - operator tooling and audit reports

Registry entries cover the 11 active providers.  Add a new entry here
whenever a new provider client is introduced.

Field contract
--------------
name                   — canonical provider name matching BaseProviderClient.name
risk_class             — execution category:
                           "passive_api"       HTTPS call to an external service
                           "local_subprocess"  spawns a child process on the host
required_credentials   — settings keys the provider checks before executing;
                         empty tuple means the provider has an anonymous free tier
entity_coverage        — entity types the provider accepts ("email", "username", "phone")
cost_class             — billing / quota model:
                           "free"              no charge, no quota
                           "quota"             free tier with request cap
                           "paid_subscription" flat subscription with generous quota
                           "paid_per_call"     billed per API call or lookup
is_subprocess          — True if the provider spawns a local child process
returns_sensitive_evidence  — True if findings include breach data, credential
                              indicators, stealer log content, or identity traces
sandboxing_required    — True if the provider must run behind extra isolation
                         (always True when is_subprocess is True)
transport              — network transport used:
                           "https"  all traffic over TLS to an external endpoint
                           "local"  no network I/O; process runs on host only
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderMetadata:
    name: str
    risk_class: str
    required_credentials: tuple[str, ...]
    entity_coverage: tuple[str, ...]
    cost_class: str
    is_subprocess: bool
    returns_sensitive_evidence: bool
    sandboxing_required: bool
    transport: str


# ---------------------------------------------------------------------------
# Active provider registry
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, ProviderMetadata] = {
    # ── Breach / credential-leak providers ─────────────────────────────────
    "haveibeenpwned": ProviderMetadata(
        name="haveibeenpwned",
        risk_class="passive_api",
        required_credentials=("HIBP_API_KEY",),
        entity_coverage=("email",),
        cost_class="paid_subscription",
        is_subprocess=False,
        returns_sensitive_evidence=True,
        sandboxing_required=False,
        transport="https",
    ),
    "dehashed": ProviderMetadata(
        name="dehashed",
        risk_class="passive_api",
        required_credentials=("DEHASHED_API_EMAIL", "DEHASHED_API_KEY"),
        entity_coverage=("email", "domain"),
        cost_class="paid_subscription",
        is_subprocess=False,
        returns_sensitive_evidence=True,
        sandboxing_required=False,
        transport="https",
    ),
    "breachdirectory": ProviderMetadata(
        name="breachdirectory",
        risk_class="passive_api",
        required_credentials=("RAPIDAPI_KEY",),
        entity_coverage=("email", "username"),
        cost_class="paid_per_call",
        is_subprocess=False,
        returns_sensitive_evidence=True,
        sandboxing_required=False,
        transport="https",
    ),
    "leakcheck": ProviderMetadata(
        name="leakcheck",
        risk_class="passive_api",
        # Empty tuple — the provider has a rate-limited public tier.
        # LEAKCHECK_API_KEY unlocks the full v2 API.
        required_credentials=(),
        entity_coverage=("email", "username"),
        cost_class="quota",
        is_subprocess=False,
        returns_sensitive_evidence=True,
        sandboxing_required=False,
        transport="https",
    ),
    "hudson_rock": ProviderMetadata(
        name="hudson_rock",
        risk_class="passive_api",
        required_credentials=("HUDSON_ROCK_API_KEY",),
        entity_coverage=("email", "domain"),
        cost_class="paid_subscription",
        is_subprocess=False,
        # Stealer log data: device info, malware name, credential counts.
        returns_sensitive_evidence=True,
        sandboxing_required=False,
        transport="https",
    ),
    # ── Reputation providers ────────────────────────────────────────────────
    "emailrep": ProviderMetadata(
        name="emailrep",
        risk_class="passive_api",
        # Empty tuple — anonymous access is permitted at a low rate limit.
        # EMAILREP_API_KEY raises the quota.
        required_credentials=(),
        entity_coverage=("email",),
        cost_class="quota",
        is_subprocess=False,
        returns_sensitive_evidence=False,
        sandboxing_required=False,
        transport="https",
    ),
    # ── Phone providers ─────────────────────────────────────────────────────
    "numverify": ProviderMetadata(
        name="numverify",
        risk_class="passive_api",
        required_credentials=("NUMVERIFY_API_KEY",),
        entity_coverage=("phone",),
        cost_class="quota",
        is_subprocess=False,
        returns_sensitive_evidence=False,
        sandboxing_required=False,
        transport="https",
    ),
    # ── Local subprocess tools ──────────────────────────────────────────────
    "tool_holehe": ProviderMetadata(
        name="tool_holehe",
        risk_class="local_subprocess",
        # Holehe is a local tool; no external API key is required.
        required_credentials=(),
        entity_coverage=("email",),
        cost_class="free",
        is_subprocess=True,
        # Returns account presence across ~100 services.
        returns_sensitive_evidence=True,
        sandboxing_required=True,
        transport="local",
    ),
    "tool_maigret": ProviderMetadata(
        name="tool_maigret",
        risk_class="local_subprocess",
        # Maigret is a local tool; no external API key is required.
        required_credentials=(),
        entity_coverage=("username",),
        cost_class="free",
        is_subprocess=True,
        # Returns account presence across 3000+ sites.
        returns_sensitive_evidence=True,
        sandboxing_required=True,
        transport="local",
    ),
    # ── Infrastructure intelligence ─────────────────────────────────────────
    "leakix": ProviderMetadata(
        name="leakix",
        risk_class="passive_api",
        required_credentials=("LEAKIX_API_KEY",),
        entity_coverage=("domain",),
        cost_class="quota",
        is_subprocess=False,
        # Returns exposed service metadata and data leak details for domains.
        returns_sensitive_evidence=True,
        sandboxing_required=False,
        transport="https",
    ),
    # ── Browser extension store enrichment (Wave 3) ────────────────────────
    "chrome_web_store_api": ProviderMetadata(
        name="chrome_web_store_api",
        risk_class="passive_api",
        # No API key required — scrapes the public CWS detail page.
        required_credentials=(),
        entity_coverage=("url",),
        cost_class="free",
        is_subprocess=False,
        # Returns extension name/URL — no breach or identity data.
        returns_sensitive_evidence=False,
        sandboxing_required=False,
        transport="https",
    ),
    "firefox_addons_site_api": ProviderMetadata(
        name="firefox_addons_site_api",
        risk_class="passive_api",
        # No API key required — uses the public Mozilla AMO REST API.
        required_credentials=(),
        entity_coverage=("url",),
        cost_class="free",
        is_subprocess=False,
        # Returns add-on name/guid/author — no breach or identity data.
        returns_sensitive_evidence=False,
        sandboxing_required=False,
        transport="https",
    ),
    # ── Local subprocess tools (infrastructure) ─────────────────────────────
    "frankenstein": ProviderMetadata(
        name="frankenstein",
        risk_class="local_subprocess",
        # No API key required — binary probes domains directly.
        required_credentials=(),
        entity_coverage=("domain",),
        cost_class="free",
        is_subprocess=True,
        # Returns TLS certificate state, security headers, DNS health.
        returns_sensitive_evidence=False,
        sandboxing_required=True,
        transport="local",
    ),
}


def get_metadata(provider_name: str) -> ProviderMetadata | None:
    """
    Return metadata for a registered provider, or None if not found.

    Callers should treat a missing entry as 'unknown provider' and
    either block execution or log a warning — do not proceed silently.
    """
    return PROVIDER_REGISTRY.get(provider_name)


def requires_sandboxing(provider_name: str) -> bool:
    """Convenience helper: True if the provider must run under isolation."""
    meta = PROVIDER_REGISTRY.get(provider_name)
    return meta.sandboxing_required if meta is not None else False


def is_subprocess_provider(provider_name: str) -> bool:
    """Convenience helper: True if the provider spawns a local subprocess."""
    meta = PROVIDER_REGISTRY.get(provider_name)
    return meta.is_subprocess if meta is not None else False
