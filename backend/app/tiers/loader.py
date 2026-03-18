# backend/app/tiers/loader.py
from functools import cache
from pathlib import Path

import yaml

from backend.app.core.enums import Tier

TIER_CONFIG_DIR = Path(__file__).parent / "config"


@cache
def load_tier_config(tier: Tier) -> dict[str, object]:
    path = TIER_CONFIG_DIR / f"{tier.value}.yaml"
    with path.open() as f:
        result: dict[str, object] = yaml.safe_load(f)
        return result


def get_enabled_domains(tier: Tier) -> list[str]:
    domains = load_tier_config(tier).get("enabled_domains", [])
    return list(domains) if isinstance(domains, list) else []


def is_domain_enabled(domain: str, tier: Tier) -> bool:
    return domain in get_enabled_domains(tier)
