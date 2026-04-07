# backend/app/modules/browser/browser_configuration/rules.py
from backend.app.core.enums import Severity

# Chromium policy signal types and their severities
CHROMIUM_SIGNAL_MAP: dict[str, tuple[str, Severity]] = {
    # policy_key → (signal_type, severity)
    "SafeBrowsingEnabled": ("safe_browsing_disabled", Severity.HIGH),
    "BlockThirdPartyCookies": ("third_party_cookies_allowed", Severity.MEDIUM),
    "ExtensionInstallForcelist": ("extension_force_installed", Severity.LOW),
}

# Firefox policy signal types and their severities
FIREFOX_SIGNAL_MAP: dict[str, tuple[str, Severity]] = {
    "DisableAppUpdate": ("browser_update_disabled", Severity.MEDIUM),
    "AppUpdatePin": ("browser_update_pinned", Severity.LOW),
    "AppUpdateURL": ("browser_update_url_changed", Severity.MEDIUM),
    "ExtensionUpdate": ("extension_updates_disabled", Severity.LOW),
    "DisablePrivateBrowsing": ("private_browsing_disabled", Severity.LOW),
    "PasswordManagerEnabled": ("password_manager_disabled", Severity.LOW),
}

# Firefox nested policy keys (policy → sub-key → signal_type, severity)
FIREFOX_NESTED_SIGNAL_MAP: dict[str, dict[str, tuple[str, Severity]]] = {
    "DNSOverHTTPS": {
        "Enabled": ("dns_over_https_disabled", Severity.LOW),
    },
    "EnableTrackingProtection": {
        "Value": ("tracking_protection_disabled", Severity.LOW),
        "Cryptomining": ("tracking_cryptomining_disabled", Severity.LOW),
        "Fingerprinting": ("tracking_fingerprinting_disabled", Severity.LOW),
        "EmailTracking": ("tracking_email_disabled", Severity.LOW),
    },
    "Cookies": {
        "Behavior": ("cookies_third_party_allowed", Severity.LOW),
    },
}


def chromium_policy_triggers(policy_key: str, value: object) -> bool:
    """Return True if this Chromium policy value indicates a misconfiguration."""
    if policy_key == "SafeBrowsingEnabled":
        return value is False or value == 0
    if policy_key == "BlockThirdPartyCookies":
        return value is False or value == 0
    if policy_key == "ExtensionInstallForcelist":
        return bool(value)  # non-empty list
    return False


def firefox_policy_triggers(policy_key: str, value: object) -> bool:
    """Return True if this Firefox flat policy value indicates a misconfiguration."""
    if policy_key == "DisableAppUpdate":
        return value is True or value == 1
    if policy_key == "AppAutoUpdate":
        return value is False or value == 0  # auto-update disabled
    if policy_key == "AppUpdatePin":
        return bool(value)  # any pinned version
    if policy_key == "AppUpdateURL":
        return bool(value)  # any non-default URL
    if policy_key == "ExtensionUpdate":
        return value is False or value == 0
    if policy_key == "DisablePrivateBrowsing":
        return value is True or value == 1
    if policy_key == "PasswordManagerEnabled":
        return value is False or value == 0
    return False


def firefox_nested_policy_triggers(
    policy_key: str, sub_key: str, value: object
) -> bool:
    """Return True if this Firefox nested policy sub-key indicates a misconfiguration."""  # noqa: E501
    if policy_key == "DNSOverHTTPS" and sub_key == "Enabled":
        return value is False or value == 0
    if policy_key == "EnableTrackingProtection":
        if sub_key in {"Value", "Cryptomining", "Fingerprinting", "EmailTracking"}:
            return value is False or value == 0
    if policy_key == "Cookies" and sub_key == "Behavior":
        return value != "reject-foreign"
    return False
