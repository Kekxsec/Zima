# tests/unit/jobs/test_runner_specs.py
"""Guard: ACTIVE_MODULES must contain exactly the modules that were
previously wired in DOMAIN_MODULES. This test prevents silent drops when
the registry is modified.

If a module is intentionally added or removed, update the expected set here
to reflect the new canonical wiring.
"""

from backend.app.active.modules import ACTIVE_MODULES

_EXPECTED_MODULE_NAMES = frozenset(
    {
        "breach_monitor",
        "stealer_log_exposure",
        "credential_exposure",
        "username_exposure",
        "maigret_scan",
        "phone_exposure",
        "account_inventory",
        "account_enumeration_risk",
        "alias_correlation",
        "darkweb_identity_monitor",
        "public_profile_scan",
        "email_reputation",
        "browser_configuration",
        "extension_risk",
        "os_security",
        "patch_status",
        "software_vulnerability",
        "firewall_status",
        "device_inventory",
        "software_inventory",
        "infrastructure_exposure",
        "domain_dns_intelligence",
        "domain_reputation",
    }
)


def test_active_modules_contains_all_expected_modules() -> None:
    """ACTIVE_MODULES must include every module that was in DOMAIN_MODULES."""
    actual = frozenset(spec.service_class.module_name for spec in ACTIVE_MODULES)
    missing = _EXPECTED_MODULE_NAMES - actual
    extra = actual - _EXPECTED_MODULE_NAMES
    assert not missing, f"Modules dropped from registry: {missing}"
    assert not extra, f"Unexpected modules in registry (update expected set): {extra}"


def test_active_modules_all_have_valid_status() -> None:
    for spec in ACTIVE_MODULES:
        assert spec.status in (
            "active",
            "deferred",
        ), f"{spec.service_class.__name__} has invalid status: {spec.status!r}"


def test_active_modules_no_duplicate_service_classes() -> None:
    classes = [spec.service_class for spec in ACTIVE_MODULES]
    seen: set[type] = set()
    for cls in classes:
        assert cls not in seen, f"Duplicate spec for {cls.__name__}"
        seen.add(cls)
