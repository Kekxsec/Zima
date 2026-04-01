---
title: "output / phone / callername"
aliases: ["callername output", "callername signal registry"]
tags: [zima, research, outputs, signal-registry, phone, callername, graph_exclude]
type: provider_research_output
provider: callername
provider_category: phone
status: not_started
prompt_note: prompt.md
provider_folder: callername.md
obsidianUIMode: preview
---
CallerName currently should be treated as **deferred / out_of_scope** for automated Zima integration: it has only a consumer web UI, no documented API, so there is no stable schema to build signals, mappers, or rules on.ieeexplore.ieee+1

A detailed report with the API surface appendix (showing the lack of any documented API), module mapping table, empty signal contract table (and why it is empty), confidence guidance, provider summary, and the requested structured JSON design contract is available here:

[[ieeexplore.ieee](https://ieeexplore.ieee.org/document/10123678/)]​

In practice this means:

- **No direct_signal_input from CallerName** into `phone_exposure` today; the module mapping classifies CallerName as **out_of_scope** until a proper API exists.callername+1

- **No standalone signals** are defined, so the Signal Contract Table is intentionally empty; there is only forward-looking design guidance for a possible future `phone_pii_exposed_in_data_broker` signal if CallerName ever publishes an API.

- **Conceptual future use-cases** (once an API exists) are limited to identity/phone enrichment and optional privacy/PII-exposure findings, with explicit TODOs for severity and confidence calibration.
# Zima Integration Assessment: CallerName (Phone / People Search)

## Overview

CallerName is a consumer-facing people and reverse phone lookup service that exposes identity and contact data (names, addresses, phone numbers, relatives, emails, social profiles) via a web UI, not a documented developer API. The site advertises free people search and reverse phone lookup but provides no official JSON/REST/OpenAPI documentation, SDKs, or authentication mechanism for programmatic access.[1][2]

Given the absence of a documented API surface, CallerName cannot currently be treated as an implementation-ready signal source for Zima. Any hypothetical integration would require HTML scraping of an unstable consumer interface, which conflicts with the requirement to base triggers and field names on documented schemas.

***

## A. API Surface Appendix

### 1. Web UI: People Search (callername.com)

- **Artifact / Endpoint**: `https://callername.com` (browser-based people search UI, no published API)
- **Purpose**: Free people search by name, phone, or address to retrieve personal details and contact information.[1]
- **Supported entity types (conceptual)**:
  - `phone` – reverse lookup entry point is advertised alongside people search.[2][1]
  - `name` – people search by person name.[1]
  - `address` – people search by address.[1]
- **Auth / execution requirements**:
  - No login or API key required for manual browser searches.[1]
  - No mention of rate limits, API keys, or developer onboarding.[1]
- **Top-level response fields and types**:
  - Not documented as a machine API. The UI marketing copy states that results may include:
    - Personal details such as age, relatives, associates, and neighbors.[1]
    - Contact information including phone numbers, emails, and current or past addresses associated with an individual.[1]
  - These are described in prose, not as structured field names; no JSON schema is exposed.
- **Nested objects/arrays**:
  - Undocumented. The consumer UI likely renders multiple records and sub-sections (e.g., relatives, neighbors), but there is no formal schema.
- **Field presence / premium tiers**:
  - The homepage states CallerName “provides instant access to valuable information” and “retrieves phone numbers, emails, and current or past addresses associated with an individual from hundreds of millions of records,” but does not distinguish mandatory vs optional fields or free vs paid tiers.[1]
  - No explicit premium-only flags, partial-result semantics, or completeness guarantees are documented.
- **Enum or status values**:
  - None documented.
- **Response variants**:
  - **Successful hit**: Not documented as an API; the marketing text implies that matching records are listed and can be refined.[1]
  - **Successful no-hit**: Not documented; presumably a “no results” UI state, but not specified.
  - **Partial/limited result**: Not documented; the homepage recommends verifying information independently, implying that coverage and accuracy are imperfect but without machine-readable indicators.[1]
  - **Errors**: No API error taxonomy is documented.
- **Example responses**:
  - No JSON or XML examples are provided; only user-facing descriptions.

**Implementation implication**: There is no stable, documented API envelope, so Zima cannot safely define field-level mappers or rules for this artifact.

### 2. Web UI: Reverse Phone Lookup (callername.com/phone-lookup)

- **Artifact / Endpoint**: `https://callername.com/phone-lookup` (browser-based reverse phone lookup UI, no published API)
- **Purpose**: Reverse phone lookup to identify unknown callers and uncover identity and related OSINT-style details for a given phone number.[2]
- **Supported entity types (conceptual)**:
  - `phone` – primary input; the page explicitly describes reverse lookup for “any type of phone number.”[2]
- **Auth / execution requirements**:
  - Described as “completely free searches for any type of phone number.”[2]
  - No reference to API keys, authentication headers, IP-based quotas, or developer registration.[2]
- **Top-level response fields and types (conceptual)**:
  - The product description says the reverse lookup “taps into public records and phone data” to reveal:[2]
    - Caller’s name and aliases
    - Current and past addresses
    - Other associated phone numbers
    - Possible relatives
    - Email addresses
    - Social media profiles
  - These are conceptual data categories only; no machine field names, types, or guarantee of presence are specified.
- **Nested objects/arrays**:
  - Likely multiple associated addresses, phone numbers, and relatives, but schema is entirely undocumented.[2]
- **Field presence / optionality / premium-only**:
  - The page contrasts CallerName with other “online services claiming to offer free reverse phone lookup” and says CallerName “offers completely free searches for any type of phone number,” but does not specify which attributes are always available or whether some require account upgrades.[2]
  - No machine-level indication of “hit quality,” “coverage,” or completeness is documented.
- **Enum and status values**:
  - None documented.
- **Response variants**:
  - **Successful hit**: Implied when CallerName can “uncover the identities behind those mysterious numbers,” but not formalized.[2]
  - **Successful no-hit**: Not documented.
  - **Partial/limited result**: Not documented.
  - **Common error cases**: Not documented.
- **Example responses**:
  - No serialized API examples; only narrative explanation of what may be shown in the UI.[2]

**Implementation implication**: As with the people search UI, reverse phone lookup is not documented as an API. Zima cannot define reliable JSON field paths, enums, or error-handling logic based on current public information.

***

## B. Module Mapping Appendix

### Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---------------|-----------------|----------------------|----------------|-------------|-------------|--------------|-------|
| phone_exposure | signal_producer (desired) | unknown (no documented API methods) | https://callername.com/phone-lookup | out_of_scope | ["phone"] | Do not integrate until CallerName publishes an official developer API with a stable schema; avoid scraping consumer HTML. | https://callername.com, https://callername.com/phone-lookup | CallerName currently exposes only browser-based people and reverse phone search; no REST/JSON/OpenAPI docs, auth scheme, or response schema are publicly available.[1][2] |

### Rationale per Module

#### phone_exposure

- **Why not consume now**:
  - Zima’s rules and mappers require concrete, documented field names, types, and response shapes; CallerName exposes only consumer-facing UI descriptions with no programmatic contract.[2][1]
  - Any use today would require scraping HTML or browser automation, which is operationally brittle, may violate site terms of service, and cannot be treated as a stable “provider schema” for long-lived modules.
- **Conceptual potential (future)**:
  - If a proper API were published, reverse phone lookup data (name, addresses, associated numbers, emails, relatives) could be used to:
    - Enrich `phone_exposure` entities with OSINT context.
    - Potentially flag **PII exposure via consumer data broker**, if Zima chooses to treat broad public people-search exposure as a privacy/security issue rather than pure enrichment.
  - Those hypothetical uses are deferred until there is an official, documented API.

***

## C. Signal Contract Table

CallerName should **not** emit standalone Zima signals at this time because there is no documented, machine-consumable API and therefore no reliable field-level trigger logic can be defined.

### Signal Contract Table (Empty)

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|-----------------|-------------|----------|----------|-------------------------|------------------|------------|--------------|-------------------|-----------------|-------------------|------------------|----------------|--------------|-------|

_No rows: CallerName is not used as a signal-producing source until a formal API exists._

***

## D. Severity Rules (Hypothetical, Deferred)

Because there are no defined signals from CallerName, no active severities are assigned. The following is **design guidance only** for future consideration **once** an API exists:

- **Potential future signal: `phone_pii_exposed_in_data_broker`** (if Zima decides that broad people-search exposure is a security finding rather than contextual enrichment):
  - **Category**: `privacy` or `identity_security`.
  - **Entity type**: `phone`.
  - **Severity guidance** (hypothetical):
    - `high` if CallerName (and other brokers) expose current address plus contact emails linked to the same phone, indicating live exploitable PII exposure.
    - `medium` if only historical or partial PII (e.g., outdated address, no emails) is present.
    - `low` if only basic caller name with no richer PII is exposed.
  - This logic **cannot** be implemented now because CallerName does not expose structured fields or timestamps in an official API.

Until an API appears, the correct operational posture is: **no CallerName-based severities, no signals.**

***

## E. Confidence Guidance

Even though CallerName is not currently integrated, it is useful to outline confidence considerations in case an API becomes available.

### Confidence Guidance Table

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|------------------------|---------------------|--------------------------|---------------------|------------------|
| phone_exposure | Future use of CallerName reverse phone/people data for PII exposure or identity enrichment | CallerName states it "obtains data from official sources and open sources" and recommends users verify information independently, indicating non-authoritative but broad aggregated coverage.[1] | No documentation on update frequency, data retention windows, or recency indicators; results may reflect long-lived public records rather than near-real-time changes.[1] | Cross-check CallerName hits with at least one additional phone OSINT or telephony reputation provider before assigning medium/high severity; treat a single CallerName record as low-confidence enrichment. | Once an API exists, collect a calibration set (phones with known exposure states) to estimate hit rate, false positives, and alignment with other data brokers; tune severity and confidence thresholds accordingly. |

***

## F. Provider Summary for Zima

### Strongest conceptual signal types (if an API existed)

- **Phone-based PII exposure via data broker**: Presence of a phone number with detailed associated PII (name, current address, email, relatives) in a consumer people-search product could be framed as a privacy/PII exposure signal, depending on Zima’s policy posture.[1][2]
- **Identity and contact enrichment**: CallerName’s described attributes (names, aliases, addresses, related phones, relatives, emails, social profiles) would offer strong enrichment for identity, fraud, or investigation workflows if exposed through a stable API.[2][1]

### What the provider should not be used for

- **Not for breach confirmation or malware/C2 detection**: CallerName does not claim to provide breach, credential, malware, or infrastructure intelligence.
- **Not for telephony fraud/spam scoring**: Unlike CNAM or reputation APIs that expose spam/scam labels and risk scores, CallerName’s public copy focuses on people search and contact details, not risk classifications.[2]
- **Not for real-time signaling**: There is no indication of real-time or low-latency telephony data (e.g., live call events, porting status); it appears to rely on aggregated public/official records.[1][2]

### API/auth/rate-limit/licensing implementation cautions

- **No official developer API**: There is no documentation describing REST endpoints, authentication, quotas, pricing, or SLAs.[1][2]
- **Scraping risks**: Building an integration by scraping HTML would be brittle (changes to layout could silently break parsers), may contravene terms of service, and would not meet Zima’s standard for schema-stable providers.
- **Compliance and privacy**: CallerName describes access to personal data such as addresses, relatives, and emails derived from “official sources and open sources.” Any future integration must be reviewed against privacy regulations (GDPR/CCPA) and Zima’s own data-handling policies.[1]

### Overall role in current Zima stage

- **Current treatment**: CallerName should be treated as **deferred / out_of_scope** for automated ingestion in Zima because there is no public API to base implementation-grade mappers and rules on.
- **Future possibility**: If CallerName publishes a documented API (or white-label/partner integration) with clear schema and auth, it could be revisited primarily as:
  - An **identity/phone enrichment source** feeding modules like `phone_exposure` with contextual OSINT.
  - Optionally, a **privacy/PII exposure signal producer**, if Zima decides that presence in people-search/data-broker products is a first-class finding.

***

## G. Structured JSON (Design Contract)

```json
{
  "provider": "callername",
  "provider_category": "phone",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "unknown",
      "endpoint_or_artifact": "https://callername.com/phone-lookup",
      "classification": "out_of_scope",
      "entity_types": ["phone"],
      "gating_logic": "Do not integrate until CallerName publishes an official developer API with a stable schema; avoid scraping consumer HTML.",
      "citation_refs": [
        "https://callername.com",
        "https://callername.com/phone-lookup"
      ],
      "notes": "CallerName currently exposes only browser-based people and reverse phone search; no REST/JSON/OpenAPI docs, auth scheme, or response schema are publicly available."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "phone_exposure",
      "signal_type_or_use_case": "future_phone_pii_exposure_or_identity_enrichment_via_callername",
      "source_reliability": "CallerName aggregates data from official and open sources but is not authoritative; users are advised to verify information independently.",
      "freshness_considerations": "No public documentation on update frequency or recency indicators; data may reflect long-lived records rather than near-real-time changes.",
      "corroboration_rules": "If an API becomes available, corroborate CallerName hits with at least one additional phone OSINT or telephony reputation provider before assigning medium/high severity.",
      "calibration_todo": "Once an API exists, build a calibration dataset of phone numbers with known exposure states; measure hit/coverage rate and agreement with other brokers to tune severity and confidence thresholds."
    }
  ]
}
```
