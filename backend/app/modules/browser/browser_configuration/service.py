# backend/app/modules/browser/browser_configuration/service.py
import uuid

from backend.app.core.enums import Confidence, EntityType
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.modules.browser.browser_configuration.rules import (
    CHROMIUM_SIGNAL_MAP,
    FIREFOX_NESTED_SIGNAL_MAP,
    FIREFOX_SIGNAL_MAP,
    chromium_policy_triggers,
    firefox_nested_policy_triggers,
    firefox_policy_triggers,
)
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.chromium_enterprise_policies.client import (
    ChromiumEnterprisePoliciesProvider,
)
from backend.app.providers.tools.firefox_enterprise_policies.client import (
    FirefoxEnterprisePoliciesProvider,
)
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


def _chromium_summary(signal_type: str, policy_key: str, value: object) -> str:
    if signal_type == "extension_force_installed":
        count = len(value) if isinstance(value, list) else 1
        return f"Chrome enterprise policy forces {count} extension(s) to be installed"
    if signal_type == "safe_browsing_disabled":
        return "Chrome SafeBrowsing is disabled by enterprise policy"
    if signal_type == "third_party_cookies_allowed":
        return "Chrome enterprise policy allows third-party cookies"
    return f"Chrome policy misconfiguration: {policy_key}"


def _firefox_summary(signal_type: str, policy_key: str, sub_key: str | None) -> str:
    summaries: dict[str, str] = {
        "browser_update_disabled": "Firefox automatic updates are disabled by policy",
        "browser_update_pinned": "Firefox update version is pinned by policy",
        "browser_update_url_changed": "Firefox update URL has been changed by policy",
        "extension_updates_disabled": (
            "Firefox extension updates are disabled by policy"
        ),
        "private_browsing_disabled": "Firefox private browsing is disabled by policy",
        "password_manager_disabled": "Firefox password manager is disabled by policy",
        "dns_over_https_disabled": "Firefox DNS-over-HTTPS is disabled by policy",
        "tracking_protection_disabled": (
            "Firefox tracking protection is disabled by policy"
        ),
        "tracking_cryptomining_disabled": "Firefox cryptomining protection is disabled",
        "tracking_fingerprinting_disabled": (
            "Firefox fingerprinting protection is disabled"
        ),
        "tracking_email_disabled": "Firefox email tracking protection is disabled",
        "cookies_third_party_allowed": (
            "Firefox cookie policy allows third-party cookies"
        ),
    }
    return summaries.get(signal_type, f"Firefox policy misconfiguration: {policy_key}")


class BrowserConfigurationService(BaseModuleService):
    module_name = "browser_configuration"
    module_domain = "browser"
    required_entity_types = [EntityType.DEVICE]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: object = None,
    ) -> list[SignalCreate]:
        """Read enterprise browser policies and emit misconfiguration signals.

        asset_value: ignored (DEVICE assets don't have a meaningful string value
                     for this module). Policy paths are read from platform defaults.
        """
        signals: list[SignalCreate] = []

        # --- Chromium enterprise policies ---
        chrome_provider = ChromiumEnterprisePoliciesProvider()
        try:
            chrome_policies = await chrome_provider.read_policies()
        except ProviderError as e:
            logger.error("browser_configuration.chromium_failure", error=str(e))
            chrome_policies = []

        for policy in chrome_policies:
            key = policy.get("policy_key", "")
            value = policy.get("value")
            source_path = policy.get("source_path", "")

            if key not in CHROMIUM_SIGNAL_MAP:
                continue
            if not chromium_policy_triggers(key, value):
                continue

            signal_type, severity = CHROMIUM_SIGNAL_MAP[key]
            signals.append(
                SignalCreate(
                    signal_type=signal_type,
                    category="browser_security",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="chromium_enterprise_policies",
                    summary=_chromium_summary(signal_type, key, value),
                    details=(
                        f"Chrome enterprise policy '{key}' is set to {value!r} "
                        f"(source: {source_path})."
                    ),
                    evidence={
                        "policy_key": key,
                        "policy_value": value,
                        "source_path": source_path,
                        "browser": "chrome",
                    },
                    tags=["browser_configuration", "chrome", "enterprise_policy"],
                    recommended_action=(
                        "Review enterprise policy configuration. "
                        "Ensure policies align with your organisation's security "
                        "baseline."
                    ),
                    source_ref=f"chromium_enterprise_policies:{key}",
                )
            )

        # --- Firefox enterprise policies ---
        firefox_provider = FirefoxEnterprisePoliciesProvider()
        try:
            firefox_policies = await firefox_provider.read_policies()
        except ProviderError as e:
            logger.error("browser_configuration.firefox_failure", error=str(e))
            firefox_policies = []

        for policy in firefox_policies:
            key = policy.get("policy_key", "")
            value = policy.get("value")
            source_path = policy.get("source_path", "")

            # Flat policy signals
            if key in FIREFOX_SIGNAL_MAP and firefox_policy_triggers(key, value):
                signal_type, severity = FIREFOX_SIGNAL_MAP[key]
                signals.append(
                    SignalCreate(
                        signal_type=signal_type,
                        category="browser_security",
                        entity_type=EntityType.DEVICE,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=severity,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="firefox_enterprise_policies",
                        summary=_firefox_summary(signal_type, key, None),
                        details=(
                            f"Firefox enterprise policy '{key}' is set to {value!r} "
                            f"(source: {source_path})."
                        ),
                        evidence={
                            "policy_key": key,
                            "policy_value": value,
                            "source_path": source_path,
                            "browser": "firefox",
                        },
                        tags=["browser_configuration", "firefox", "enterprise_policy"],
                        recommended_action=(
                            "Review Firefox enterprise policy configuration. "
                            "Ensure policies align with your security baseline."
                        ),
                        source_ref=f"firefox_enterprise_policies:{key}",
                    )
                )
                continue

            # Nested policy signals (e.g. DNSOverHTTPS.Enabled, Cookies.Behavior)
            if key in FIREFOX_NESTED_SIGNAL_MAP and isinstance(value, dict):
                nested_map = FIREFOX_NESTED_SIGNAL_MAP[key]
                for sub_key, (signal_type, severity) in nested_map.items():
                    sub_value = value.get(sub_key)
                    if sub_value is None:
                        continue
                    if not firefox_nested_policy_triggers(key, sub_key, sub_value):
                        continue
                    signals.append(
                        SignalCreate(
                            signal_type=signal_type,
                            category="browser_security",
                            entity_type=EntityType.DEVICE,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=severity,
                            confidence=Confidence.HIGH,
                            source=self.module_name,
                            provider="firefox_enterprise_policies",
                            summary=_firefox_summary(signal_type, key, sub_key),
                            details=(
                                f"Firefox policy '{key}.{sub_key}' is set to "
                                f"{sub_value!r} (source: {source_path})."
                            ),
                            evidence={
                                "policy_key": key,
                                "sub_key": sub_key,
                                "policy_value": sub_value,
                                "source_path": source_path,
                                "browser": "firefox",
                            },
                            tags=[
                                "browser_configuration",
                                "firefox",
                                "enterprise_policy",
                            ],
                            recommended_action=(
                                "Review Firefox enterprise policy configuration. "
                                "Ensure policies align with your security baseline."
                            ),
                            source_ref=f"firefox_enterprise_policies:{key}.{sub_key}",
                        )
                    )

        logger.info(
            "browser_configuration.completed",
            user_id=str(user_id),
            signals_emitted=len(signals),
        )
        return signals
