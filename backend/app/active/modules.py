# backend/app/active/modules.py
"""Active module registry — the single wiring source for all scan modules.

This list replaces the DOMAIN_MODULES dict in runner.py. Every module that
the runner may execute must have an entry here. Modules with
``status="deferred"`` are wired but skipped at runtime.

Dependency rule: this file may import from ``backend.app.modules.**`` but
nothing in ``modules/**`` imports from ``active/``. The ``active/`` package
is a leaf in the dependency graph.
"""

from __future__ import annotations

from backend.app.active.specs import ModuleSpec
from backend.app.core.enums import Tier

# Browser
from backend.app.modules.browser.browser_configuration.service import (
    BrowserConfigurationService,
)
from backend.app.modules.browser.extension_risk.service import ExtensionRiskService
from backend.app.modules.device.device_inventory.service import DeviceInventoryService
from backend.app.modules.device.firewall_status.service import FirewallStatusService

# Device
from backend.app.modules.device.os_security.service import OsSecurityService
from backend.app.modules.device.patch_status.service import PatchStatusService
from backend.app.modules.device.software_inventory.service import (
    SoftwareInventoryService,
)
from backend.app.modules.device.software_vulnerability.service import (
    SoftwareVulnerabilityService,
)

# Domain
from backend.app.modules.domain.dns_intelligence.service import (
    DomainDNSIntelligenceService,
)
from backend.app.modules.domain.domain_reputation.service import (
    DomainReputationService,
)
from backend.app.modules.identity.account_enumeration_risk.service import (
    AccountEnumerationRiskService,
)
from backend.app.modules.identity.account_inventory.service import (
    AccountInventoryService,
)
from backend.app.modules.identity.alias_correlation.service import (
    AliasCorrelationService,
)

# Identity
from backend.app.modules.identity.breach_monitor.service import BreachMonitorService
from backend.app.modules.identity.credential_exposure.service import (
    CredentialExposureService,
)
from backend.app.modules.identity.darkweb_identity_monitor.service import (
    DarkwebIdentityMonitorService,
)
from backend.app.modules.identity.email_reputation.service import (
    EmailReputationService,
)
from backend.app.modules.identity.maigret_scan.service import MaigretScanService
from backend.app.modules.identity.phone_exposure.service import PhoneExposureService
from backend.app.modules.identity.public_profile_scan.service import (
    PublicProfileScanService,
)
from backend.app.modules.identity.stealer_log_exposure.service import (
    StealerLogExposureService,
)
from backend.app.modules.identity.username_exposure.service import (
    UsernameExposureService,
)

# Infrastructure
from backend.app.modules.infrastructure.infrastructure_exposure.service import (
    InfrastructureExposureService,
)

ACTIVE_MODULES: list[ModuleSpec] = [
    # --- identity ---
    ModuleSpec(
        service_class=BreachMonitorService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    ModuleSpec(
        service_class=StealerLogExposureService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    ModuleSpec(
        service_class=CredentialExposureService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    ModuleSpec(
        service_class=UsernameExposureService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    ModuleSpec(
        service_class=MaigretScanService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=PhoneExposureService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    ModuleSpec(
        service_class=AccountInventoryService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=AccountEnumerationRiskService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=AliasCorrelationService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=DarkwebIdentityMonitorService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    ModuleSpec(
        service_class=PublicProfileScanService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    ModuleSpec(
        service_class=EmailReputationService,
        domain="identity",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    # --- browser ---
    ModuleSpec(
        service_class=BrowserConfigurationService,
        domain="browser",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=ExtensionRiskService,
        domain="browser",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    # --- device ---
    ModuleSpec(
        service_class=OsSecurityService,
        domain="device",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=PatchStatusService,
        domain="device",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=SoftwareVulnerabilityService,
        domain="device",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=FirewallStatusService,
        domain="device",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=DeviceInventoryService,
        domain="device",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=SoftwareInventoryService,
        domain="device",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    # --- infrastructure ---
    ModuleSpec(
        service_class=InfrastructureExposureService,
        domain="infrastructure",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
    # --- domain ---
    ModuleSpec(
        service_class=DomainDNSIntelligenceService,
        domain="domain",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=False,
    ),
    ModuleSpec(
        service_class=DomainReputationService,
        domain="domain",
        tier_minimum=Tier.CORE,
        status="active",
        requires_credentials=True,
    ),
]
