← [[../Zima|Home]] · [[section-05-provider-architecture|← §5 Provider Architecture]] · [[section-07-provider-module-relationships|§7 Provider↔Module Relationships →]]

# Section 6 — Module Architecture

Modules interpret provider data into standardized security signals. Each module lives under a domain folder and implements exactly one focused security capability.

---

## Module Folder Structure

```text
backend/app/modules/<domain>/<module_name>/
├── __init__.py
├── service.py
├── mapper.py
├── rules.py
├── schemas.py
├── config.py
├── constants.py
├── README.md
└── tests/
    ├── test_service.py
    ├── test_mapper.py
    ├── test_rules.py
    └── fixtures/
```

---

## File Responsibilities

| File | Responsibility |
|---|---|
| `service.py` | Entrypoint for module execution; orchestrates provider calls, mapping, and rule evaluation |
| `mapper.py` | Maps provider-specific models into domain-level data structures |
| `rules.py` | Assigns severity and confidence; derives signals from mapped data |
| `schemas.py` | Defines module input and output models |
| `config.py` | Module-level configuration and thresholds |
| `constants.py` | Signal names, classifications, module-level constants |
| `README.md` | Documents what the module does, providers used, signals emitted, known limitations |
| `tests/` | Unit and integration tests for the module |

---

## Module Responsibilities

- accept entity inputs or scope inputs
- call one or more providers
- interpret provider data in a security context
- emit standardized signals
- assign severity and confidence
- optionally emit remediation hints

---

## Module Metadata Template

Every module must clearly define the following in its `README.md` and `constants.py`:

```text
module_name
module_domain
security_capability
tier_support
supported_entities
required_inputs
providers_used
signals_emitted
possible_correlated_findings
remediation_playbooks
automation_hooks
known_limitations
```

---

## Example Module Definition

**Module:** `mfa_posture`
**Domain:** `accounts`
**Security capability:** Detect accounts lacking strong MFA or relying on weak factors such as SMS
**Required inputs:** Account identifiers and admin API access, depending on provider
**Providers used:** Google Workspace, Microsoft 365, GitHub

**Signals emitted:**

- `mfa_missing`
- `sms_mfa_only`
- `fido_key_not_enabled`

**Possible correlated findings:**

- `high_account_takeover_risk`

**Remediation playbooks:**

- enroll in authenticator app MFA
- register hardware security key
- add backup codes

**Automation hooks:**

- open MFA enablement workflow where supported

**Known limitations:**

- requires sufficient API privileges
- may not cover all personal account types
