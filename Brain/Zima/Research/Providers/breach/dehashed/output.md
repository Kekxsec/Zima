---
title: "output / breach / dehashed"
aliases: ["dehashed output", "dehashed signal registry"]
tags: [zima, research, outputs, signal-registry, breach, dehashed, graph_exclude]
type: provider_research_output
provider: dehashed
provider_category: breach
status: complete
prompt_note: prompt.md
provider_folder: dehashed.md
obsidianUIMode: preview
---
# DeHashed Integration for Zima

DeHashed should be treated as a core signal-producing breach and credential source for Zima, primarily via its Search API (`GET https://api.dehashed.com/search`), which returns per-record breached credentials and related PII.

---

## A. API Surface Appendix

### 1. Search API — `GET https://api.dehashed.com/search`

#### Purpose

Programmatic search over DeHashed’s breach dataset for OSINT and breach intelligence use cases.

#### Endpoint

- **Method:** `GET`
- **URL:** `https://api.dehashed.com/search`
- **Primary query parameter:** `query`
  - Lucene-style search string, typically `field:value`.
- **Other common parameters** (observed in tools/examples, not clearly documented on the official API page):
  - `page` — results page number.
  - `size` — page size / max results per page.
- Some third-party tools also implement `results_from` / `results_to`, but that is XSOAR-side logic, not native DeHashed API behavior.

#### Supported `entity_type` Values

Via the `query` parameter, DeHashed supports searches on:

- `username`
- `email`
- `hashed_password`
- `ip_address`
- `vin`
- `name`
- `address`
- `phone`

Domains are also supported in practice via `domain:` queries.

Directly relevant to Zima:

- `email`
- `username`
- `domain`
- `ip_address`
- `hashed_password`
- `password`
- `phone`
- `name`
- `address`

#### Authentication and Execution Requirements

- **Authentication:** HTTP Basic Auth using:
  - username = DeHashed account email
  - password = API key
- Common request header:
  - `Accept: application/json`
- API access requires:
  - active DeHashed Search subscription
  - pre-purchased API credits (pay-per-query)
- Credits are consumed per API query.

#### Key Request Parameters

- `query` (`string`, required)
  - Free-text or structured Lucene-like query expression.
  - Supports field scoping such as:
    - `username:`
    - `email:`
    - `hashed_password:`
    - `ip_address:`
    - `vin:`
    - `name:`
    - `address:`
    - `phone:`
    - `domain:` (used in practice)
- `page` (`integer`, optional)
  - Page number.
- `size` (`integer`, optional)
  - Number of results per page; tools commonly pass `100`.

#### Parameter Documentation Status

- `query` — documented.
- `page` — inferred from example API clients.
- `size` — inferred from example API clients.

#### Top-Level Response Fields

Observed across blogs, community clients, and XSOAR integration mappings:

- `success` (`boolean`)
  - Indicates whether the API call succeeded.
- `entries` (`array<object>`)
  - List of breach records.
- `total` (`integer`)
  - Total number of matching records.
- `balance` (`integer`)
  - Remaining API credit balance.
- `took` (`float`, possible)
  - Timing field inferred in some tooling, but not clearly documented.

#### Response Field Documentation Status

- `entries` — well supported by multiple sources.
- `success`, `total`, `balance` — inferred from examples and tool logic, not clearly shown on an official canonical schema page.

#### Entry Object Schema (`entries[]`)

Derived from community JSON examples, XSOAR integration mappings, and blog posts:

- `id` (`string`)
- `email` (`string`, optional)
- `username` (`string`, optional)
- `password` (`string`, optional)
- `hashed_password` (`string`, optional)
- `name` (`string`, optional)
- `vin` (`string` or `number`, optional)
- `address` (`string`, optional)
- `ip_address` (`string`, optional)
- `phone` (`string` or `number`, optional)
- `database_name` (`string`, optional)
- `obtained_from` (`string`, optional)

#### Entry Schema Notes

- `database_name` and `obtained_from` appear to represent the same conceptual field: breach source / dataset name.
- All entry fields except `id` and likely breach source are optional, depending on dataset composition.

#### Presence Characteristics

- `id` — assumed always present in observed examples.
- `email` / `username` — common but not guaranteed.
- `password` / `hashed_password` — only present for credential-bearing records.
- `database_name` / `obtained_from` — commonly present for attribution.

#### Successful Hit Variant

Expected pattern:

- HTTP `200`
- JSON body with:
  - `success: true`
  - `entries` length > 0
  - `total` > 0

`balance` is typically decremented according to the credit model.

#### Successful No-Hit Variant

Not explicitly documented, but likely:

- HTTP `200`
- JSON body with:
  - `success: true`
  - `entries: []`
  - `total: 0`

Implementation should defensively handle cases where `entries` is missing or null.

#### Partial or Limited Results

- Some sources describe a default limitation of 100 results per request.
- XSOAR notes logical pages up to 5,000 records and possible client-side slicing.
- Community tools paginate with `page` and rely on `total` to continue.

Conclusion: pagination exists, but exact server-side limits are inconsistently documented.

#### Common Error Cases

From community usage and tooling:

- **Invalid credentials / no subscription**
  - May return `success: false`
  - Status code behavior is inconsistently documented
- **Malformed query / bad request**
  - Some tooling treats HTTP `400` as invalid query or transient failure
- **Insufficient balance / credit exhaustion**
  - Balance is exposed, but exact exhaustion error semantics are not clearly documented.

#### Example Response Excerpts

Example entry schema:

```json
{
  "id": "8912739811",
  "email": "example@testdomain.com",
  "ip_address": "0.0.0.0",
  "username": "exampleusername",
  "password": "thisistheplaintextpassword123",
  "hashed_password": "16652e4c27058396b37c026d1bd419a830b20e6a",
  "name": "John Smith",
  "vin": "5YJSA1DG9DFP14705",
  "address": "123 main street",
  "phone": "123-123-1234",
  "database_name": "MyFitnessPal"
}
```

Troy Hunt example showing top-level fields:

```json
{
  "balance": 99,
  "entries": [
    { "id": "R-RGc9dDLRpus6EOZz89e2OfTmKAoywX7aE" }
  ]
}
```

---

## B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| breach_monitor | signal_producer | search_breaches | `GET https://api.dehashed.com/search` | direct_signal_input | email, username, domain, ip | Only create breach-monitor signals when `entries` contains at least one record whose `email` or `username` matches a monitored identity or domain scope. | Official API marketing and Search description; support search fields; XSOAR mapping; JSON examples.  | Module focuses on any breach record tied to the asset, regardless of credential presence. Domain queries should be expanded into per-identity signals. |
| credential_exposure | signal_producer | search_credentials | `GET https://api.dehashed.com/search` | direct_signal_input | email, username | Only create credential-exposure signals when at least one matching entry has non-empty `password` or `hashed_password`. | Same API; emphasis on `password` and `hashed_password` fields.  | Ignore PII-only records in this module. |
| breach_monitor | signal_producer | enrichment_lookup | `GET https://api.dehashed.com/search` | enrichment_only | email, username, domain, ip | Allow ad-hoc DeHashed lookups as enrichment-only where they would otherwise duplicate scheduled-scan signals. | Same API shape; credits/billing model requires caution.  | Use to enrich investigations, not create duplicate alerts. |
| credential_exposure | signal_producer | enrichment_lookup | `GET https://api.dehashed.com/search` | enrichment_only | email, username | Use for pull-time contextualization of existing credential incidents without emitting duplicate signals. | Same as above.  | Should be credit-aware and throttled. |
| breach_monitor | n/a | monitoring_push | DeHashed monitoring product UI / notifications | out_of_scope | email, username, domain | No documented programmatic monitoring or alert API. | Monitoring product pages but no public API reference.  | Zima should implement its own polling against Search API. |
| credential_exposure | n/a | CSV/JSON exports (UI) | Manual exports from dehashed.com UI | utility_only / manual | email, username, domain | Only relevant for one-off offline backfills, not automated provider-client execution. | Export-oriented tooling references.  | Treat as batch ingestion artifacts if ever supported. |

---

## C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| breach_monitor | breach_monitor | dehashed | search_breaches | breach_record_found | identity_security | medium | yes | If `password` present → critical; else if `hashed_password` present → high; else if only PII/identifiers are present → medium. | email | true_finding | `entries` contains at least one object where `email` or `username` matches the monitored identity, or is scoped by monitored domain, regardless of credential presence. | `id`, `email`, `username`, `password`, `hashed_password`, `ip_address`, `database_name`/`obtained_from`, `name`, `address`, `phone`, `vin`, plus top-level `total`, `balance` when available | `query`, pagination metadata, query timestamp, timing metrics such as `took` if present | `Breach record found for {{entity}} in DeHashed dataset {{database_name}} (credentials may or may not be present).` | derived |  | Tags: `["breach", "pii_exposure"]`. Use for any breach presence. |
| credential_exposure | credential_exposure | dehashed | search_credentials | credential_breach_found | credential_security | high | yes | If `password` non-empty → critical; else if only `hashed_password` non-empty → high; if both empty → do not emit signal. | email | true_finding | `entries` contains at least one matching record for monitored identity with non-empty `password` or `hashed_password`. | `id`, `email`, `username`, `password`, `hashed_password`, `database_name`/`obtained_from`, plus `total`, `balance` | `ip_address`, `name`, `address`, `phone`, `vin`, query context, pagination metadata | `Credentials for {{entity}} were found in DeHashed (source: {{database_name}}); password material is exposed in the breach data.` | derived |  | Tags: `["breach", "credential_stuffing"]`; add `plaintext_password` when `password` is present. |

### Key Clarifications

- `category`
  - `identity_security` for general breach presence
  - `credential_security` for explicit credential exposure
- `entity_type`
  - modeled as `email` for both signals
  - if email is missing but `username` is present, still emit a signal and retain username in evidence
- `database_name` and `obtained_from`
  - normalize internally to a common `breach_source` concept while preserving raw keys.

### Evidence Status Notes

- Top-level `entries`, `id`, `email`, `username`, `password`, `hashed_password`, `name`, `vin`, `address`, `ip_address`, `phone`, and `database_name` / `obtained_from` are derived from multiple independent examples and mappings, not a canonical OpenAPI spec.
- `success`, `total`, and `balance` should be treated as optional.

---

## D. Severity Rules

### 1. `breach_record_found` (`breach_monitor`)

- **Baseline severity:** `medium`
- Rationale:
  - Any confirmed breach presence, even without credentials, is a meaningful risk signal.

#### Conditional Escalation

- `critical`
  - if `password` is present and non-empty
- `high`
  - if no plaintext `password`, but `hashed_password` is present and non-empty
- `medium`
  - if only PII is present (`name`, `email`, `phone`, `address`, `ip_address`) and no credential fields exist

### 2. `credential_breach_found` (`credential_exposure`)

- **Baseline severity:** `high`
- **Escalation:** `critical` if plaintext password is present

#### Conditional Behavior

- `high`
  - `hashed_password` present, no plaintext password
- `critical`
  - `password` present
- **Suppress**
  - If both `password` and `hashed_password` are absent, do not emit this signal

---

## E. Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| breach_monitor | breach_record_found | High overall; DeHashed is widely used and aggregates large breach datasets, but underlying dataset quality varies.  | Many datasets are historical; JSON often lacks explicit breach timestamps.  | Corroborate high or critical findings with internal login telemetry, other breach providers, and vendor disclosures.  | Add `dataset_age` heuristic and measure how often hits map to active accounts. |
| credential_exposure | credential_breach_found | High for presence of credential material; passwords and hashes are concrete indicators.  | Old credentials may have been rotated; provider does not indicate password change status. | Confirm the account exists and, where possible, validate whether exposed credentials remain relevant. | Track outcome rates and tune confidence / severity thresholds based on real-world signal value. |

---

## F. Tags per Signal Type

### `breach_record_found`

- `breach`
- `pii_exposure`

### `credential_breach_found`

Default tags:

- `breach`
- `credential_stuffing`

Conditional tag:

- `plaintext_password` when `password` is non-empty

---

## G. Implementation Notes

### Field Paths and Parsing

Preserve raw JSON for each entry, including:

- `id`
- `email`
- `username`
- `password`
- `hashed_password`
- `ip_address`
- `name`
- `address`
- `phone`
- `vin`
- `database_name`
- `obtained_from`

Normalize `database_name` and `obtained_from` to internal `breach_source`, but retain both raw keys.

### Null, Empty, and No-Hit Behavior

- If `entries` is missing, null, or empty: treat as no-hit and emit no signals.
- For `credential_exposure`
  - emit only when matching entries contain non-empty `password` or `hashed_password`
- For `breach_monitor`
  - emit at most one signal per `(identity, breach_source)` pair
  - consolidate severity upward across multiple rows

### Rate Limits, Billing, and Licensing

- Queries consume API credits.
- Community tooling emphasizes minimizing unnecessary calls due to cost.

Zima should:

- cache results per identity for a configurable interval
- cap pages and total entries per identity
- stop on low-balance or hard-failure conditions

### Deduplication Keys

#### Entry-Level Deduplication

- `(email or username, database_name/obtained_from, hashed_password or password)`

#### Signal-Level Deduplication

- `(entity, breach_source)` over a sliding window
- keep highest-severity representation:
  - plaintext password
  - hash-only
  - PII-only

### Raw Evidence Preservation

Preserve:

- full raw entry for each match
- top-level `balance`
- `total`
- timing fields if present

Especially important for remediation:

- `password` / `hashed_password` for reset and reuse analysis
- `database_name` / `obtained_from` for breach context
- `ip_address`, `name`, `address`, `phone` for fraud investigations

### Responsibility Boundaries

#### Provider Client

- build `query` strings safely
- escape Lucene special characters
- handle pagination, HTTP errors, JSON parsing, and credit-aware throttling

#### Module Mapper

- apply module-specific gating
- map raw data into normalized signal schema
- set severity and tags conditionally

#### Correlation Layer

- deduplicate across providers on `(entity, breach_source)`
- correlate reused hashes/passwords
- merge DeHashed findings with internal telemetry and other intel sources

---

## H. Provider Summary

### Strongest Signal Types

- High-fidelity credential exposure with plaintext or hashed passwords and breach-source attribution
- Broad breach presence detection across emails, usernames, and domains, including PII-only dumps

### Not Appropriate For

- malware, C2, or threat-infrastructure intelligence
- general WHOIS or broad OSINT enrichment
- real-time activity monitoring

### API, Auth, and Licensing Cautions

- requires paid subscription plus credits
- no clearly published public rate-limit values
- treat `success:false`, non-200 responses, and low balance as hard-stop conditions

### Role for Zima

- Treat DeHashed as a **signal-producing provider**, not just enrichment.
- Use scheduled scans for high-value identities and domains.
- Use ad-hoc lookups sparingly for context enrichment only.

---

## I. Structured JSON

```json
{
  "provider": "dehashed",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "search_breaches",
      "endpoint_or_artifact": "GET https://api.dehashed.com/search",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username", "domain", "ip"],
      "gating_logic": "Emit breach_monitor signals when response.entries contains at least one record whose email or username matches the monitored identity or falls under the monitored domain scope.",
      "citation_refs": ["https://dehashed.com/api", "https://dehashed.com/search", "https://support.dehashed.com/hc/en-us/articles/360000867094-How-to-Search-Properly", "https://xsoar.pan.dev/docs/reference/integrations/de-hashed", "https://www.grahamhelton.com/blog/dehash-query-script/"],
      "notes": "Use DeHashed to detect any breach presence tied to identities. Domain-based searches should be converted to per-identity findings. Cost and pagination must be handled in provider client."
    },
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "search_credentials",
      "endpoint_or_artifact": "GET https://api.dehashed.com/search",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username"],
      "gating_logic": "Emit credential_exposure signals only when entries contain records for the monitored identity with non-empty password or hashed_password fields.",
      "citation_refs": ["https://dehashed.com/api", "https://risk3sixty.com/blog/understanding-password-breach-data", "https://xsoar.pan.dev/docs/reference/integrations/de-hashed", "https://www.grahamhelton.com/blog/dehash-query-script/"],
      "notes": "Ignore PII-only records in this module; they are handled by breach_monitor. Severity is driven by presence and type of credential material."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "enrichment_lookup",
      "endpoint_or_artifact": "GET https://api.dehashed.com/search",
      "classification": "enrichment_only",
      "entity_types": ["email", "username", "domain", "ip"],
      "gating_logic": "Use ad-hoc DeHashed lookups to enrich existing incidents; avoid emitting new breach signals if they duplicate existing ones for the same identity and breach source.",
      "citation_refs": ["https://dehashed.com/api", "https://risk3sixty.com/blog/understanding-password-breach-data"],
      "notes": "Analyst-triggered or correlation-triggered lookups should be cost-aware and deduplicated."
    },
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "enrichment_lookup",
      "endpoint_or_artifact": "GET https://api.dehashed.com/search",
      "classification": "enrichment_only",
      "entity_types": ["email", "username"],
      "gating_logic": "Use for contextualizing existing credential exposure cases (adding additional dumps or sources) without creating new primary alerts unless new breach_source is discovered.",
      "citation_refs": ["https://dehashed.com/api", "https://risk3sixty.com/blog/understanding-password-breach-data"],
      "notes": "Throttle and cache repeated lookups for the same identity to control credit usage."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "monitoring_push",
      "endpoint_or_artifact": "DeHashed monitoring UI/notifications",
      "classification": "out_of_scope",
      "entity_types": ["email", "username", "domain"],
      "gating_logic": "No documented programmatic alert/monitor API; only web product is described.",
      "citation_refs": ["https://dehashed.com/monitoring", "https://dehashed.com/api"],
      "notes": "If DeHashed later publishes a webhook/alert API, this mapping should be revisited."
    },
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "csv_json_exports",
      "endpoint_or_artifact": "Manual JSON/CSV exports from web UI",
      "classification": "utility_only",
      "entity_types": ["email", "username", "domain"],
      "gating_logic": "Only used for manual or offline backfills, not as part of automated provider client.",
      "citation_refs": ["https://github.com/syyntax/dehashed-lists"],
      "notes": "Zima might support offline imports of DeHashed JSON exports via a separate ingestion pipeline."
    }
  ],
  "signal_contracts": [
    {
      "module": "breach_monitor",
      "source": "breach_monitor",
      "provider": "dehashed",
      "provider_method": "search_breaches",
      "signal_type": "breach_record_found",
      "category": "identity_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "If any matching entry has non-empty password -> critical; else if any has non-empty hashed_password -> high; else (PII-only) -> medium.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "DeHashed JSON response has an entries array with at least one object where email or username corresponds to the monitored identity or falls under the monitored domain (e.g. email endswith @example.com), regardless of credential material presence.",
      "evidence_fields": [
        "id",
        "email",
        "username",
        "password",
        "hashed_password",
        "ip_address",
        "name",
        "address",
        "phone",
        "vin",
        "database_name",
        "obtained_from",
        "total",
        "balance"
      ],
      "enrichment_fields": [
        "query",
        "page",
        "size",
        "took"
      ],
      "summary_template": "Breach record found for {{entity}} in DeHashed dataset {{database_name}}.",
      "evidence_status": "derived",
      "citation_refs": [
        "https://dehashed.com/api",
        "https://dehashed.com/search",
        "https://support.dehashed.com/hc/en-us/articles/360000867094-How-to-Search-Properly",
        "https://xsoar.pan.dev/docs/reference/integrations/de-hashed",
        "https://www.grahamhelton.com/blog/dehash-query-script/",
        "https://www.troyhunt.com/the-unattributable-lead-hunter-data-breach/"
      ],
      "notes": "Treat database_name and obtained_from as alternative keys for breach source. Dedupe signals on (entity, breach_source) over time. Tags: ['breach', 'pii_exposure']."
    },
    {
      "module": "credential_exposure",
      "source": "credential_exposure",
      "provider": "dehashed",
      "provider_method": "search_credentials",
      "signal_type": "credential_breach_found",
      "category": "credential_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "If password field is non-empty -> critical; else if password empty but hashed_password non-empty -> high; if both are empty -> do not emit this signal.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "DeHashed JSON response has entries with email or username matching the monitored identity and where password is non-empty OR hashed_password is non-empty.",
      "evidence_fields": [
        "id",
        "email",
        "username",
        "password",
        "hashed_password",
        "database_name",
        "obtained_from",
        "total",
        "balance"
      ],
      "enrichment_fields": [
        "ip_address",
        "name",
        "address",
        "phone",
        "vin",
        "query",
        "page",
        "size"
      ],
      "summary_template": "Credentials for {{entity}} were found in DeHashed (source: {{database_name}}).",
      "evidence_status": "derived",
      "citation_refs": [
        "https://dehashed.com/api",
        "https://risk3sixty.com/blog/understanding-password-breach-data",
        "https://xsoar.pan.dev/docs/reference/integrations/de-hashed",
        "https://www.grahamhelton.com/blog/dehash-query-script/"
      ],
      "notes": "Only emit for records with credential material. Tags: default ['breach', 'credential_stuffing']; add 'plaintext_password' when password is non-empty."
    }
  ],
  "confidence_guidance": [
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "breach_record_found",
      "source_reliability": "High; DeHashed is used by law enforcement and enterprises and aggregates large breach datasets, but underlying datasets vary in quality.",
      "freshness_considerations": "Many breaches are historical; JSON schema does not expose explicit breach timestamp, so recency must be inferred from breach source names and external breach intel.",
      "corroboration_rules": "Corroborate with internal login telemetry, phishing reports, and other breach providers for the same identities and datasets.",
      "calibration_todo": "Add dataset_age heuristic and measure fraction of hits that map to active accounts to tune severity for very old breaches."
    },
    {
      "module": "credential_exposure",
      "signal_type_or_use_case": "credential_breach_found",
      "source_reliability": "High for presence of credential material; password/hash fields are concrete and rarely spurious, though impact depends on password reuse and age.",
      "freshness_considerations": "Old passwords may have been rotated; no direct indication of password change date. Treat older breaches as lower impact unless corroborated by current account behavior.",
      "corroboration_rules": "Verify that affected accounts exist and check for recent successful logins or password reuse. Where safe and authorized, test old passwords in controlled conditions.",
      "calibration_todo": "Track real-world success of DeHashed-derived credentials in internal red-team tests to calibrate high vs critical boundaries and throttling rules."
    }
  ]
}
```
