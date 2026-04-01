#!/usr/bin/env python3
# scripts/demo_signals.py
"""
Demonstrates the Zima signal pipeline end-to-end using mock provider data.
No database or API keys required.

Run:
    cd /Users/max/Zima
    python scripts/demo_signals.py
"""

import asyncio
import sys
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

sys.path.insert(0, "/Users/max/Zima")

from backend.app.core.enums import SignalStatus
from backend.app.signals.dedup import compute_signal_id
from backend.app.signals.schemas import SignalCreate

# ─────────────────────────────────────────────
#  Fake persistent "database" for the demo
# ─────────────────────────────────────────────
SIGNAL_STORE: dict[str, dict[str, Any]] = {}


def fake_upsert(data: SignalCreate) -> dict[str, Any]:
    sig_id = compute_signal_id(
        data.user_id, data.signal_type, data.entity_id, data.source_ref
    )
    existing = sig_id in SIGNAL_STORE
    SIGNAL_STORE[sig_id] = {
        "signal_id": sig_id,
        "signal_type": data.signal_type,
        "category": data.category,
        "entity_value": data.entity_value,
        "severity": data.severity.value,
        "confidence": data.confidence.value,
        "source": data.source,
        "provider": data.provider,
        "summary": data.summary,
        "evidence": data.evidence,
        "tags": data.tags,
        "recommended_action": data.recommended_action,
        "status": SignalStatus.OPEN,
        "source_ref": data.source_ref,
    }
    return {"action": "UPDATE" if existing else "INSERT", **SIGNAL_STORE[sig_id]}


# ─────────────────────────────────────────────
#  Mock provider responses
# ─────────────────────────────────────────────
MOCK_HIBP_FINDINGS = [
    {
        "title": "Adobe (2013)",
        "description": "In October 2013, 153 million Adobe accounts were breached.",
        "tags": ["email", "password_hint"],
        "raw": {
            "breach_date": "2013-10-04",
            "data_classes": ["email", "password_hints"],
        },
    },
    {
        "title": "LinkedIn (2016)",
        "description": "In May 2016, LinkedIn had 164 million email addresses and passwords exposed.",
        "tags": ["email", "password"],
        "raw": {"breach_date": "2016-05-18", "data_classes": ["email", "passwords"]},
    },
]

MOCK_DEHASHED_FINDINGS = [
    {
        "title": "Credential exposure via DeHashed",
        "description": "DeHashed breach records with password data found.",
        "raw": {
            "total": 3,
            "has_plaintext": True,
            "has_hash": True,
            "sample_count": 3,
            "entries": [
                {
                    "email": "alice@example.com",
                    "password": "REDACTED",
                    "source": "combo_list_2022",
                },
                {"email": "alice@example.com", "hashed_password": "HASH_REDACTED"},
            ],
        },
        "tags": ["breach"],
    }
]

MOCK_HUDSON_ROCK_FINDINGS = [
    {
        "title": "Stealer log: Redline",
        "description": "Email found in Redline stealer log — device was compromised.",
        "raw": {
            "malware_name": "Redline",
            "computer_name": "DESKTOP-X7F2",
            "operating_system": "Windows 10",
            "credential_count": 47,
            "date_uploaded": "2024-08-12",
        },
        "tags": ["stealer", "redline"],
    }
]

MOCK_HOLEHE_FINDINGS = [
    {
        "title": "Account found: GitHub",
        "description": "This email has an account on GitHub.",
        "raw": {"site": "GitHub", "registration_confirmed": True},
    },
    {
        "title": "Account found: Spotify",
        "description": "This email has an account on Spotify.",
        "raw": {"site": "Spotify", "registration_confirmed": True},
    },
    {
        "title": "Account found: Twitter",
        "description": "This email has an account on Twitter/X.",
        "raw": {"site": "Twitter/X", "registration_confirmed": True},
    },
]


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
SEV_COLOR = {
    "critical": "\033[91m",  # red
    "high": "\033[93m",  # yellow
    "medium": "\033[94m",  # blue
    "low": "\033[96m",  # cyan
    "info": "\033[97m",  # white
}
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def sev(s: str) -> str:
    return f"{SEV_COLOR.get(s, '')}{s.upper()}{RESET}"


def section(title: str) -> None:
    print(f"\n{BOLD}{'─' * 60}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}")


def print_signal(sig: dict[str, Any], action: str = "") -> None:
    badge = f"{DIM}[{action}]{RESET} " if action else ""
    print(f"\n  {badge}{BOLD}{sig['signal_type']}{RESET}  {sev(sig['severity'])}")
    print(f"    summary  : {sig['summary']}")
    print(f"    provider : {sig['provider']}")
    print(f"    source   : {sig['source']}")
    print(f"    sig_id   : {DIM}{sig['signal_id']}{RESET}")
    if sig.get("recommended_action"):
        short = (
            sig["recommended_action"][:80] + "…"
            if len(sig["recommended_action"]) > 80
            else sig["recommended_action"]
        )
        print(f"    action   : {short}")


# ─────────────────────────────────────────────
#  Demo runner
# ─────────────────────────────────────────────
async def run_demo() -> None:
    user_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    email = "alice@example.com"

    print(f"\n{BOLD}Zima Signal Pipeline Demo{RESET}")
    print(f"  user_id  : {user_id}")
    print(f"  asset_id : {asset_id}")
    print(f"  email    : {email}")

    # ── 1. breach_monitor ──────────────────────────────────────────
    section("Module: breach_monitor  (HIBP + DeHashed + BreachDirectory)")

    with (
        patch(
            "backend.app.providers.breach.hibp.client.HibpProvider.search_breaches",
            new=AsyncMock(return_value=MOCK_HIBP_FINDINGS),
        ),
        patch(
            "backend.app.providers.breach.dehashed.client.DehashedProvider.search_breaches",
            new=AsyncMock(return_value=MOCK_DEHASHED_FINDINGS),
        ),
        patch(
            "backend.app.core.config.settings",
        ) as mock_settings,
    ):
        mock_settings.hibp_api_key = None  # no key needed — provider is mocked
        mock_settings.dehashed_email = "test@test.com"
        mock_settings.dehashed_api_key = type(
            "_S", (), {"get_secret_value": lambda self: "key"}
        )()
        mock_settings.breachdirectory_rapidapi_key = None  # skip for brevity

        from backend.app.modules.identity.breach_monitor.service import (
            BreachMonitorService,
        )

        svc = BreachMonitorService()
        signals = await svc.run(user_id=user_id, asset_id=asset_id, asset_value=email)

    for s in signals:
        row = fake_upsert(s)
        print_signal(row, row["action"])

    print(f"\n  → {len(signals)} signal(s) emitted")

    # ── 2. stealer_log_exposure ────────────────────────────────────
    section("Module: stealer_log_exposure  (Hudson Rock)")

    with (
        patch(
            "backend.app.providers.breach.hudson_rock.client.HudsonRockProvider.get_compromised_data",
            new=AsyncMock(return_value=MOCK_HUDSON_ROCK_FINDINGS),
        ),
        patch("backend.app.core.config.settings") as mock_settings2,
    ):
        mock_settings2.hudson_rock_api_key = type(
            "_S", (), {"get_secret_value": lambda self: "key"}
        )()

        from backend.app.modules.identity.stealer_log_exposure.service import (
            StealerLogExposureService,
        )

        svc2 = StealerLogExposureService()
        signals2 = await svc2.run(user_id=user_id, asset_id=asset_id, asset_value=email)

    for s in signals2:
        row = fake_upsert(s)
        print_signal(row, row["action"])

    print(f"\n  → {len(signals2)} signal(s) emitted")

    # ── 3. account_inventory ──────────────────────────────────────
    section("Module: account_inventory  (Holehe)")

    with patch(
        "backend.app.providers.tools.holehe.client.HoleheProvider.check_accounts_tool",
        new=AsyncMock(return_value=MOCK_HOLEHE_FINDINGS),
    ):
        from backend.app.modules.identity.account_inventory.service import (
            AccountInventoryService,
        )

        svc3 = AccountInventoryService()
        signals3 = await svc3.run(user_id=user_id, asset_id=asset_id, asset_value=email)

    for s in signals3:
        row = fake_upsert(s)
        print_signal(row, row["action"])

    print(f"\n  → {len(signals3)} signal(s) emitted")

    # ── 4. Deduplication demo ──────────────────────────────────────
    section("Deduplication: re-run breach_monitor (same scan, second pass)")

    with (
        patch(
            "backend.app.providers.breach.hibp.client.HibpProvider.search_breaches",
            new=AsyncMock(return_value=MOCK_HIBP_FINDINGS),
        ),
        patch(
            "backend.app.providers.breach.dehashed.client.DehashedProvider.search_breaches",
            new=AsyncMock(return_value=MOCK_DEHASHED_FINDINGS),
        ),
        patch("backend.app.core.config.settings") as mock_settings3,
    ):
        mock_settings3.hibp_api_key = None
        mock_settings3.dehashed_email = "test@test.com"
        mock_settings3.dehashed_api_key = type(
            "_S", (), {"get_secret_value": lambda self: "key"}
        )()
        mock_settings3.breachdirectory_rapidapi_key = None

        svc_dup = BreachMonitorService()
        dup_signals = await svc_dup.run(
            user_id=user_id, asset_id=asset_id, asset_value=email
        )

    for s in dup_signals:
        row = fake_upsert(s)
        print_signal(row, row["action"])

    print(
        f"\n  → {len(dup_signals)} signal(s) processed — all UPDATEs (no duplicates created)"
    )

    # ── 5. Summary ────────────────────────────────────────────────
    section("Signal Store Summary")

    all_signals = list(SIGNAL_STORE.values())
    by_sev: dict[str, list[dict[str, Any]]] = {}
    for sig in all_signals:
        by_sev.setdefault(sig["severity"], []).append(sig)

    print(f"\n  Total unique signals in store: {BOLD}{len(all_signals)}{RESET}")
    for s_level in ["critical", "high", "medium", "low", "info"]:
        count = len(by_sev.get(s_level, []))
        if count:
            print(f"    {sev(s_level):<30} {count}")

    print("\n  Signal IDs are deterministic:")
    for sig in all_signals:
        recomputed = compute_signal_id(
            user_id, sig["signal_type"], asset_id, sig.get("source_ref")
        )
        match = "✓" if recomputed == sig["signal_id"] else "✗"
        label = f"{sig['signal_type']} / {sig['provider']}"
        if sig.get("source_ref"):
            label += f"  [{sig['source_ref']}]"
        print(f"    {match}  {sig['signal_id']}  ← {label}")

    print(f"\n{BOLD}Demo complete.{RESET}\n")


if __name__ == "__main__":
    asyncio.run(run_demo())
