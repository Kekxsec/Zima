← [[../Zima|Home]] · [[Provider Module Map|Provider Map →]]

---
tags: [zima, architecture, development, extension]
created: 2026-03-21
---

# Extending the Platform

How to add new providers, modules, correlation rules, scoring, and remediation mappings. Each layer is independent and testable in isolation.

---

## Practical Sequence for Each New Domain

1. **New provider** under `providers/<category>/<name>/` — fetch + parse only
2. **New module** under `modules/<category>/<name>/` — call provider, assign severity, emit `SignalCreate`
3. **New correlation rule** in `correlation/rules/` — detect patterns across signals, produce `Finding`
4. **New score calculator** in `scoring/calculators/` — weighted deduction for the new category
5. **Register** module + rule + calculator in the job orchestrator (Stage 6)
6. **Update `SIGNAL_TO_PLAYBOOK`** in `remediation/engine.py` for any new signal types

---

## Adding a New Provider

A provider fetches data from an external source and returns typed models. Nothing else.

**Pattern — copy the HIBP structure:**

```
backend/app/providers/
└── breach/
│   └── hibp/          ← existing
└── network/           ← new example
    └── shodan/
        ├── __init__.py
        ├── client.py      ← HTTP calls only, returns typed schemas
        ├── schemas.py     ← Pydantic models for the raw API response
        ├── mapper.py      ← converts raw schemas → SignalCreate
        └── exceptions.py
```

**Rules:**
- `client.py` makes HTTP calls, parses responses, returns `schemas.*` types
- `mapper.py` converts to `SignalCreate` — no severity assignment here
- No imports from `modules/`, `correlation/`, `scoring/`, `api/`

---

## Adding a New Module

A module consumes one or more providers and emits signals. Severity lives here.

**Pattern — copy breach_monitor:**

```
backend/app/modules/
└── identity/
│   └── breach_monitor/    ← existing
└── network/               ← new example
    └── exposure_monitor/
        ├── __init__.py
        ├── service.py      ← extends BaseModuleService, calls provider, maps signals
        ├── mapper.py       ← provider output → SignalCreate with severity assigned
        ├── rules.py        ← business logic: which conditions constitute a signal
        ├── schemas.py
        ├── config.py
        └── constants.py
```

`service.py` always looks like:

```python
class ExposureMonitorService(BaseModuleService):
    async def run(self, asset: Asset, scan_id: uuid.UUID) -> list[SignalCreate]:
        results = await self.provider.search(asset.value)   # fetch
        return mapper.to_signals(results, asset, scan_id)   # map
```

No HTTP here. No DB writes here. Just fetch → map → return signals.

---

## Adding a New Correlation Rule

One file, one class. Register it in the job orchestrator:

```python
# backend/app/correlation/rules/network_exposure.py

class HighNetworkExposureRisk(BaseCorrelationRule):
    rule_name = "high_network_exposure_risk"
    finding_type = "high_network_exposure_risk"
    required_signal_types = ["open_port_critical", "exposed_service"]

    def evaluate(self, signals: list[Signal], user_id: uuid.UUID) -> Finding | None:
        # your logic
        ...
```

Register in the job orchestrator (Stage 6):

```python
engine = CorrelationEngine(rules=[
    HighIdentityCompromiseRisk(),
    HighNetworkExposureRisk(),   # ← just add it here
])
```

The engine calls every rule in sequence. A rule only receives signals whose type is in `required_signal_types`.

---

## Adding a New Score Calculator

The `Score` model has a `domain` column — one score row per domain per scan.

```python
# backend/app/scoring/calculators/network_score.py

SCORER_VERSION = "1.0"
SEVERITY_WEIGHTS: dict[str, int] = { ... }

def calculate_network_score(signals: list[Signal]) -> tuple[int, int]:
    open_signals = [
        s for s in signals
        if s.status == "open" and s.category == "network_security"
    ]
    deduction = sum(SEVERITY_WEIGHTS.get(s.severity, 0) for s in open_signals)
    return max(0, 100 - deduction), len(open_signals)
```

In the job runner (Stage 6), call each calculator and store a `Score` row per domain:

```python
identity_score, count = calculate_identity_score(signals)
await score_repo.insert(Score(user_id=..., domain="identity", score=identity_score, ...))

network_score, count = calculate_network_score(signals)
await score_repo.insert(Score(user_id=..., domain="network", score=network_score, ...))
```

`SCORER_VERSION` lets you change weights later without corrupting historical scores.

---

## Updating Remediation

Two dict additions in `remediation/engine.py`:

```python
SIGNAL_TO_PLAYBOOK: dict[str, str] = {
    "email_breached":           "rotate_credentials",
    "open_port_critical":       "close_exposed_port",    # ← new
    "exposed_rdp":              "disable_rdp",           # ← new
}

FINDING_TO_PLAYBOOKS: dict[str, list[str]] = {
    "high_identity_compromise_risk": ["rotate_credentials", "enable_mfa"],
    "high_network_exposure_risk":    ["close_exposed_port", "enable_firewall"],  # ← new
}
```

No structural changes needed.

---

## Example: Full Domain Walkthrough (Network Exposure)

### 1. `rules.py` — severity decision

```python
CRITICAL_PORTS = {3389, 5432, 3306, 27017, 6379}   # RDP, Postgres, MySQL, Mongo, Redis
MEDIUM_PORTS   = {22, 21, 23, 5900}                 # SSH, FTP, Telnet, VNC

def severity_for_port(port: int, has_known_cve: bool) -> str:
    if port in CRITICAL_PORTS:
        return "critical"
    if has_known_cve:
        return "high"
    if port in MEDIUM_PORTS:
        return "medium"
    return "low"
```

### 2. `mapper.py` — converts provider output to SignalCreate

```python
def to_signals(host: ShodanHost, asset: Asset, scan_id: uuid.UUID) -> list[SignalCreate]:
    signals = []
    for port_data in host.ports:
        signals.append(SignalCreate(
            signal_type  = signal_type_for_port(port_data.port),
            category     = "network_security",
            entity_type  = "ip",
            entity_id    = asset.id,
            severity     = severity_for_port(port_data.port, port_data.has_cve),
            confidence   = "high",
            source       = "exposure_monitor",
            provider     = "shodan",
            summary      = f"Port {port_data.port} exposed on {asset.value}",
            evidence     = {"port": port_data.port, "banner": port_data.banner},
        ))
    return signals
```

### 3. Correlation rule

```python
class CriticalNetworkExposure(BaseCorrelationRule):
    rule_name = "critical_network_exposure"
    required_signal_types = ["open_port_rdp", "exposed_database_port", "vulnerable_service_ssh"]

    def evaluate(self, signals: list[Signal], user_id: uuid.UUID) -> Finding | None:
        critical = [s for s in signals if s.severity == "critical"]
        if not critical:
            return None
        contributing_ids = sorted([str(s.id) for s in critical])
        finding_id = "fnd_" + hashlib.sha256(
            f"{self.rule_name}:{','.join(contributing_ids)}".encode()
        ).hexdigest()[:24]
        return Finding(
            finding_id = finding_id,
            finding_type = self.finding_type,
            user_id = user_id,
            severity = "critical",
            title = "Critical network services exposed to internet",
            ...
        )
```

---

## See Also

- [[../Architecture/Design Principles]] — rules governing all of this
- [[../Architecture/section-07-provider-module-relationships|§7 Provider↔Module Patterns]] — A/B/C patterns
- [[../Architecture/section-11-development-rules|§11 Development Rules]] — what not to do
- [[Provider Module Map]] — full provider → module mapping
- [[Signal Research Guide]] — how to design and document signals
