# backend/app/active/specs.py
"""ModuleSpec — metadata wrapper for a wired module service class.

Each spec describes one module entry in the active wiring registry
(active/modules.py). Fields that are already declared on the service
class itself (module_name, required_entity_types) are not duplicated here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.core.enums import Tier
from backend.app.modules.base.service import BaseModuleService


@dataclass(frozen=True)
class ModuleSpec:
    """Runtime descriptor for a wired module.

    Attributes
    ----------
    service_class:
        The concrete ``BaseModuleService`` subclass to instantiate.
    domain:
        Domain name matching tier YAML ``enabled_domains`` values
        (e.g. "identity", "device").
    tier_minimum:
        The lowest tier at which this module is permitted to run.
        The runner intersects this with ``get_enabled_domains(tier)`` —
        both authorities must allow the domain before the module executes.
    status:
        ``"active"`` — included in runs for eligible tiers.
        ``"deferred"`` — wired but skipped at runtime (e.g. pending
        credential setup or staged rollout).
    requires_credentials:
        ``False`` — module always runs (uses local tools or companion data).
        ``True`` — module is skipped when no API key is configured.
        Enforcement is the caller's responsibility; this field is metadata.
    """

    service_class: type[BaseModuleService]
    domain: str
    tier_minimum: Tier
    status: Literal["active", "deferred"]
    requires_credentials: bool
