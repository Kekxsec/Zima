# tests/unit/modules/browser/test_browser_configuration.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.browser.browser_configuration.rules import (
    CHROMIUM_SIGNAL_MAP,
    FIREFOX_NESTED_SIGNAL_MAP,
    FIREFOX_SIGNAL_MAP,
    chromium_policy_triggers,
    firefox_nested_policy_triggers,
    firefox_policy_triggers,
)
from backend.app.modules.browser.browser_configuration.service import (
    BrowserConfigurationService,
)
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


# ─── Rules ────────────────────────────────────────────────────────────────────


def test_chromium_safe_browsing_triggers_on_false() -> None:
    assert chromium_policy_triggers("SafeBrowsingEnabled", False) is True
    assert chromium_policy_triggers("SafeBrowsingEnabled", True) is False


def test_chromium_block_third_party_cookies_triggers_on_false() -> None:
    assert chromium_policy_triggers("BlockThirdPartyCookies", False) is True
    assert chromium_policy_triggers("BlockThirdPartyCookies", True) is False


def test_chromium_extension_forcelist_triggers_on_nonempty() -> None:
    assert chromium_policy_triggers("ExtensionInstallForcelist", ["ext1"]) is True
    assert chromium_policy_triggers("ExtensionInstallForcelist", []) is False


def test_firefox_disable_app_update_triggers_on_true() -> None:
    assert firefox_policy_triggers("DisableAppUpdate", True) is True
    assert firefox_policy_triggers("DisableAppUpdate", False) is False


def test_firefox_extension_update_triggers_on_false() -> None:
    assert firefox_policy_triggers("ExtensionUpdate", False) is True
    assert firefox_policy_triggers("ExtensionUpdate", True) is False


def test_firefox_password_manager_triggers_on_false() -> None:
    assert firefox_policy_triggers("PasswordManagerEnabled", False) is True
    assert firefox_policy_triggers("PasswordManagerEnabled", True) is False


def test_firefox_nested_doh_triggers_on_false() -> None:
    assert firefox_nested_policy_triggers("DNSOverHTTPS", "Enabled", False) is True
    assert firefox_nested_policy_triggers("DNSOverHTTPS", "Enabled", True) is False


def test_firefox_nested_tracking_protection_triggers_on_false() -> None:
    assert (
        firefox_nested_policy_triggers("EnableTrackingProtection", "Value", False)
        is True
    )
    assert (
        firefox_nested_policy_triggers(
            "EnableTrackingProtection", "Cryptomining", False
        )
        is True
    )
    assert (
        firefox_nested_policy_triggers(
            "EnableTrackingProtection", "Fingerprinting", True
        )
        is False
    )


def test_firefox_nested_cookies_triggers_on_non_reject_foreign() -> None:
    assert firefox_nested_policy_triggers("Cookies", "Behavior", "allow") is True
    assert (
        firefox_nested_policy_triggers("Cookies", "Behavior", "reject-foreign") is False
    )


def test_chromium_signal_map_severity_safe_browsing() -> None:
    signal_type, severity = CHROMIUM_SIGNAL_MAP["SafeBrowsingEnabled"]
    assert signal_type == "safe_browsing_disabled"
    assert severity == Severity.HIGH


def test_firefox_signal_map_contains_expected_keys() -> None:
    assert "DisableAppUpdate" in FIREFOX_SIGNAL_MAP
    assert "AppUpdateURL" in FIREFOX_SIGNAL_MAP
    assert "PasswordManagerEnabled" in FIREFOX_SIGNAL_MAP


def test_firefox_nested_signal_map_structure() -> None:
    assert "DNSOverHTTPS" in FIREFOX_NESTED_SIGNAL_MAP
    assert "Enabled" in FIREFOX_NESTED_SIGNAL_MAP["DNSOverHTTPS"]
    assert "Cookies" in FIREFOX_NESTED_SIGNAL_MAP
    assert "Behavior" in FIREFOX_NESTED_SIGNAL_MAP["Cookies"]


# ─── Service ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_emits_safe_browsing_signal() -> None:
    service = BrowserConfigurationService()
    chrome_policies = [
        {
            "policy_key": "SafeBrowsingEnabled",
            "value": False,
            "source_path": "/etc/chrome/policies/managed/policy.json",
        },
    ]
    with (
        patch(
            "backend.app.modules.browser.browser_configuration.service.ChromiumEnterprisePoliciesProvider.read_policies",
            return_value=chrome_policies,
        ),
        patch(
            "backend.app.modules.browser.browser_configuration.service.FirefoxEnterprisePoliciesProvider.read_policies",
            return_value=[],
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="",
        )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "safe_browsing_disabled"
    assert s.severity == Severity.HIGH
    assert s.entity_type == EntityType.DEVICE
    assert s.provider == "chromium_enterprise_policies"
    assert s.evidence["policy_key"] == "SafeBrowsingEnabled"
    assert s.evidence["browser"] == "chrome"


@pytest.mark.asyncio
async def test_run_emits_firefox_flat_policy_signal() -> None:
    service = BrowserConfigurationService()
    firefox_policies = [
        {
            "policy_key": "DisableAppUpdate",
            "value": True,
            "source_path": "/usr/lib/firefox/distribution/policies.json",
        },
    ]
    with (
        patch(
            "backend.app.modules.browser.browser_configuration.service.ChromiumEnterprisePoliciesProvider.read_policies",
            return_value=[],
        ),
        patch(
            "backend.app.modules.browser.browser_configuration.service.FirefoxEnterprisePoliciesProvider.read_policies",
            return_value=firefox_policies,
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="",
        )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "browser_update_disabled"
    assert s.severity == Severity.MEDIUM
    assert s.provider == "firefox_enterprise_policies"
    assert s.evidence["browser"] == "firefox"


@pytest.mark.asyncio
async def test_run_emits_firefox_nested_doh_signal() -> None:
    service = BrowserConfigurationService()
    firefox_policies = [
        {
            "policy_key": "DNSOverHTTPS",
            "value": {"Enabled": False},
            "source_path": "/usr/lib/firefox/distribution/policies.json",
        },
    ]
    with (
        patch(
            "backend.app.modules.browser.browser_configuration.service.ChromiumEnterprisePoliciesProvider.read_policies",
            return_value=[],
        ),
        patch(
            "backend.app.modules.browser.browser_configuration.service.FirefoxEnterprisePoliciesProvider.read_policies",
            return_value=firefox_policies,
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="",
        )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "dns_over_https_disabled"
    assert s.evidence["sub_key"] == "Enabled"
    assert s.evidence["policy_key"] == "DNSOverHTTPS"


@pytest.mark.asyncio
async def test_run_skips_policies_that_do_not_trigger() -> None:
    """Policies with non-misconfigured values must not emit signals."""
    service = BrowserConfigurationService()
    with (
        patch(
            "backend.app.modules.browser.browser_configuration.service.ChromiumEnterprisePoliciesProvider.read_policies",
            return_value=[
                {"policy_key": "SafeBrowsingEnabled", "value": True, "source_path": ""},
                {
                    "policy_key": "BlockThirdPartyCookies",
                    "value": True,
                    "source_path": "",
                },
            ],
        ),
        patch(
            "backend.app.modules.browser.browser_configuration.service.FirefoxEnterprisePoliciesProvider.read_policies",
            return_value=[
                {"policy_key": "DisableAppUpdate", "value": False, "source_path": ""},
            ],
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="",
        )

    assert signals == []


@pytest.mark.asyncio
async def test_run_graceful_on_chrome_provider_failure() -> None:
    service = BrowserConfigurationService()
    with (
        patch(
            "backend.app.modules.browser.browser_configuration.service.ChromiumEnterprisePoliciesProvider.read_policies",
            side_effect=ProviderError("cannot read policies"),
        ),
        patch(
            "backend.app.modules.browser.browser_configuration.service.FirefoxEnterprisePoliciesProvider.read_policies",
            return_value=[],
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="",
        )

    assert signals == []


@pytest.mark.asyncio
async def test_run_emits_multiple_signals_from_both_browsers() -> None:
    service = BrowserConfigurationService()
    with (
        patch(
            "backend.app.modules.browser.browser_configuration.service.ChromiumEnterprisePoliciesProvider.read_policies",
            return_value=[
                {
                    "policy_key": "SafeBrowsingEnabled",
                    "value": False,
                    "source_path": "",
                },
                {
                    "policy_key": "BlockThirdPartyCookies",
                    "value": False,
                    "source_path": "",
                },
            ],
        ),
        patch(
            "backend.app.modules.browser.browser_configuration.service.FirefoxEnterprisePoliciesProvider.read_policies",
            return_value=[
                {"policy_key": "DisableAppUpdate", "value": True, "source_path": ""},
            ],
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="",
        )

    assert len(signals) == 3
    signal_types = {s.signal_type for s in signals}
    assert "safe_browsing_disabled" in signal_types
    assert "third_party_cookies_allowed" in signal_types
    assert "browser_update_disabled" in signal_types
