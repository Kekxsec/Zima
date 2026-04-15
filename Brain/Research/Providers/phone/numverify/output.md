---
title: "output / phone / numverify"
aliases: ["numverify output", "numverify signal registry"]
tags: [zima, research, outputs, signal-registry, phone, numverify, graph_exclude]
type: provider_research_output
provider: numverify
provider_category: phone
status: not_started
prompt_note: prompt.md
provider_folder: numverify.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
# Numverify – Zima Phone Exposure Module Research

## Executive Overview

Numverify is a RESTful JSON API for real-time validation and metadata lookup of national and international phone numbers in 232 countries, returning validity, normalized formats, country, location, carrier, and line type data. Its outputs are high-quality phone metadata but do not include any evidence of breaches, exposures, or malicious activity, so for Zima’s `phone_exposure` module the provider should be treated as enrichment-only rather than a standalone signal source.[1][2][3]

***

## A. API Surface Appendix

### 1. /validate endpoint

**Name / path**

- Path: `/validate` (sometimes also referenced as `/check` in APILayer docs).[2][1]
- Typical base URL: `http://apilayer.net/api/validate` or HTTPS variant; APILayer also exposes the service under its `api.apilayer.com` host, but the path and parameters remain the same.[3][1][2]
- HTTP method: GET (inferred from URL examples intended to be opened directly in browsers and via simple curl calls; not explicitly labeled as GET in docs).[4][2]

**Purpose**

- Validate a phone number (international or national) against up-to-date international numbering plan databases and return a normalized representation plus associated country, location, carrier, and line type metadata.[1][2][3]

**Supported entity_type(s)**

- `phone` (single phone number per request), via the `number` query parameter.[2][3]

**Authentication & execution requirements**

- Authentication via `access_key` query parameter attached to the endpoint URL; each account has a unique API access key.[5][3][2]
- HTTPS support via adding `s` to the protocol (`https://`), documented as using industry-standard SSL; earlier docs mention HTTPS may be plan-dependent, while newer APILayer docs state all customers may establish secure connections.[3][2]
- Subject to API plan quotas, rate limits, and overage billing; exceeding quotas triggers specific error codes such as `usage_limit_reached` and HTTP 429 plus documented overage behavior.[2][3]

**Request parameters**

From numverify.com documentation and APILayer guides:[6][3][2]

- `access_key` (required): API key string for authentication (query parameter).
- `number` (required): Phone number to validate; may contain digits and special characters, which the API normalizes.[2]
- `country_code` (optional): Two-letter country code (ISO 3166-1 alpha-2) when validating a national/local-format phone number; mandatory when providing local-format numbers, and must not be provided when sending an international/E.164-style number.[3][2]
- `format` (optional): `1` to request prettified/indented JSON output for debugging; increases payload size and should not be used in production.[3][2]
- `callback` (optional): Function name for JSONP callbacks; when provided, the JSON result is wrapped in the specified JavaScript function.[2][3]

**Top-level response structure (successful request)**

Standard successful response example for a valid US mobile number:[2]

```json
{
  "valid": true,
  "number": "14158586273",
  "local_format": "4158586273",
  "international_format": "+14158586273",
  "country_prefix": "+1",
  "country_code": "US",
  "country_name": "United States of America",
  "location": "Novato",
  "carrier": "AT&T Mobility LLC",
  "line_type": "mobile"
}
```

Documented fields:[3][2]

- `valid` (boolean): `true` if the specified phone number is valid according to the numbering plan; `false` otherwise.
- `number` (string): The input phone number in a cleaned format, stripped of special characters.
- `local_format` (string): Local/national-format representation of the number.
- `international_format` (string): International (E.164-style) representation including `+` and country code.
- `country_prefix` (string): International dialing prefix including `+` (for example, `+1`).
- `country_code` (string): Two-letter country code (for example, `US`).
- `country_name` (string): Full country name.
- `location` (string or null): City, state, or county where the number is registered; may be unavailable for some numbers.[2]
- `carrier` (string or null): Name of the carrier the number is registered with; may be unavailable for some numbers.[2]
- `line_type` (string or null): Line type for this number; see enumerated values below. May not be available for all numbers.[2]

Docs explicitly state that each API response consists of these objects, and specifically note that `location` and carrier data may not always be available, indicating those are conditional/optional fields.[3][2]

**Line type enum values**

Documented supported `line_type` values:[2]

- `mobile` – Mobile phone.
- `landline` – Landline.
- `special_services` – Special services such as police.
- `toll_free` – Toll-free numbers such as hotels.
- `premium_rate` – Premium rate numbers such as paid hotlines.
- `satellite` – Satellite numbers.
- `paging` – Paging services.

No premium-only line types or additional enums are documented.[2]

**Presence / optionality summary**

- Always present on successful, non-error responses (documented): `valid`, `number`, `local_format`, `international_format`, `country_prefix`, `country_code`, `country_name`.[3][2]
- Conditionally present / may be null or empty (documented): `location`, `carrier`, `line_type`.
- Premium-only: None documented; feature availability (e.g., HTTPS access) is governed by subscription plan, but response schema is the same across plans.[2]

**Response variants**

- **Successful, valid hit** (documented): HTTP 200, `valid: true`, all core fields populated, and optional `location`, `carrier`, `line_type` populated when available.[2]
- **Successful, invalid number** (derived from documented fields): HTTP 200 with body structurally identical to a valid response but with `valid: false`. Docs do not show an explicit invalid-number example but describe `valid` as a boolean indicating validity.[3][2]
- **Partial / limited result** (documented): `valid: true` with `location`, `carrier`, and/or `line_type` missing or null where data is unavailable for specific numbers.[2]
- **Error case** (documented): Response body includes `success: false` and an `error` object containing a 3-digit `code`, `type`, and explanatory `info` string.[3][2]

Example error for missing phone number:[2]

```json
{
  "success": false,
  "error": {
    "code": 210,
    "type": "no_phone_number_provided",
    "info": "Please specify a phone number. [Example: 14158586273]"
  }
}
```

**Error codes and conditions**

The docs present two complementary error tables: an APILayer-style 3-digit internal error code table and an older HTTP-status-style table.[3][2]

APILayer-style internal codes (examples):[3]

- `101` – `missing_access_key`: User did not supply an access key.
- `101` – `invalid_access_key`: User entered an invalid access key (in some docs, same numeric code is shown for both, which may be documentation drift).
- `102` – `inactive_user`: Account not active.
- `103` – `invalid_api_function`: Non-existent API function requested.
- `104` – `usage_limit_reached`: Monthly API request allowance exceeded.
- `105` – `https_access_restricted`: Plan does not support HTTPS.
- `106` – `rate_limit_reached`: Rate limit exceeded.
- `210` – `no_phone_number_provided`: No `number` parameter.
- `211` – `non_numeric_phone_number_provided`: Non-numeric phone number supplied.
- `310` – `invalid_country_code`: Invalid 2-letter country code.
- `404` – `404_not_found`: Resource does not exist.[3]

Older HTTP-status-style codes (examples):[2]

- `403` – `missing_access_key` or `invalid_access_key`.
- `404` – `404_not_found` or `invalid_api_function`.
- `429` – `usage_limit_reached` (monthly quota exceeded).
- `601` – `no_phone_number_provided`.
- `602` – `non_numeric_phone_number_provided`.
- `603` – `invalid_country_code`.

Implementation should therefore treat `success: false` plus an `error` object as the canonical indicator of an unsuccessful call, and not rely solely on the HTTP status code, due to documentation inconsistencies.[3][2]

**JSONP and formatting behavior**

- JSONP: Any endpoint supports attaching `callback=FUNCTION_NAME`; the API then wraps the JSON result in that callback.[3][2]
- Formatting: Attaching `format=1` results in prettified JSON; intended only for debugging due to increased payload size and potential parsing impacts.[3][2]

**Module relevance classification (for Zima `phone_exposure`)**

- For Zima’s `phone_exposure` module, `/validate` is the only endpoint that carries information relevant to a phone indicator (validity, normalization, country, carrier, line type).[1][2]
- However, this information is purely descriptive and does not imply exposure, compromise, or abuse by itself, so at the module boundary it should be treated as **enrichment_only** rather than a direct signal input.[2]

Classification for `phone_exposure`: **enrichment_only** (module-specific).

***

### 2. /countries endpoint

**Name / path**

- Path: `/countries`.[2]
- Typical URL: `http://apilayer.net/api/countries?access_key=YOUR_ACCESS_KEY` (GET).[2]

**Purpose**

- Return a static JSON map of all supported countries (232 territories) with country names and dialing codes, used to build UIs or internal country-code lists.[1][2]

**Supported entity_type(s)**

- None directly mapped to Zima indicator entities; conceptually `country`, but this endpoint does not take or emit indicator-like objects.

**Authentication & execution requirements**

- Same `access_key` query parameter as `/validate`.[2]
- Subject to the same quota, rate limit, and overage rules as other endpoints.[2]

**Top-level response structure**

Example (truncated) from docs:[2]

```json
{
  "AF": {
    "country_name": "Afghanistan",
    "dialling_code": "+93"
  },
  "AL": {
    "country_name": "Albania",
    "dialling_code": "+355"
  },
  "DZ": {
    "country_name": "Algeria",
    "dialling_code": "+213"
  },
  "AS": {
    "country_name": "American Samoa",
    "dialling_code": "+1"
  }
  // ... more country codes
}
```

Documented fields:[2]

- Top-level keys: Two-letter country codes (ISO 3166-1 alpha-2) such as `AF`, `AL`, `DZ`.
- Nested object per country:
  - `country_name` (string): Full country name.
  - `dialling_code` (string): International dialing code including `+`.

All documented fields appear always present for each returned country; no premium-only or conditional fields are documented.[2]

**Response variants & errors**

- Successful response: JSON map as above.[2]
- Error behavior: Shares global error behavior with `/validate` (missing/invalid access key, quota exceeded, etc.), expressed as `success: false` with `error` object; docs do not show a `/countries`-specific error example, so this is inferred from generic error handling.[3][2]

**Module relevance classification (for Zima `phone_exposure`)**

- Provides static metadata about countries and dialing codes; not tied to any phone indicator instance or exposure context.
- Useful for building configuration UIs or as a lookup table in the provider client, but not for generating or enriching exposure signals directly.

Classification for `phone_exposure`: **utility_only** at the provider client / configuration layer; effectively **out_of_scope** for the detection/rules layer.

***

## B. Module Mapping Table

### Module-to-provider usage

The table below reflects how Numverify should be consumed specifically by the `phone_exposure` module.

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---------------|-----------------|----------------------|----------------|-------------|-------------|--------------|-------|
| phone_exposure | signal_producer (provider-level role) | `validate` | `/validate` | enrichment_only | phone | Only call when another upstream source has already surfaced a candidate phone indicator; require HTTP 200 (or equivalent) and either missing `success` or `success != false`; on error (`success: false` with `error`), treat as "no enrichment" and do not create or suppress any signal; do not treat `valid == false` as a security finding, only as quality metadata. | https://numverify.com/documentation [2]; https://docs.apilayer.com/numverify/docs/getting-started [3]; https://docs.apilayer.com/numverify/docs/api-documentation [1] | Provides validity, normalized formats, country, carrier, and line type for phones but no breach/abuse information; should be wired into the enrichment path for any `phone_exposure` signal generated from other providers, not used to emit its own signals. |
| phone_exposure | signal_producer (provider-level role) | `countries` | `/countries` | utility_only | none | Load periodically into provider client or configuration service; never call from hot-path detection or rules; no gating on indicators because endpoint is not indicator-specific. | https://numverify.com/documentation [2] | Static list of supported countries and dialing codes; useful for UI and validation of user-supplied country codes but conceptually out_of_scope for the `phone_exposure` detection module. |

***

## C. Signal Contract Table

Numverify does not, by itself, provide any direct evidence of breach, exposure, abuse, or malicious infrastructure. It validates number format and returns metadata such as country, carrier, and line type, which are descriptive attributes rather than security findings. Therefore, Zima’s `phone_exposure` module should **not** emit standalone signals sourced solely from Numverify; instead, Numverify should enrich signals generated from other providers that actually surface exposure or threat events.[1][2]

Per the specification, this section provides an empty table structure with no rows.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|-----------------|------------|----------|----------|------------------------|------------------|------------|--------------|-------------------|----------------|------------------|------------------|----------------|--------------|-------|

***

## D. Severity Rules (Explanation)

Because there are no standalone Numverify-based signals for `phone_exposure`, no severity rules are defined in the contract table.

- Validity (`valid == true` or `false`) and other fields like `carrier` or `line_type` describe what a number is, not how it is being used or whether it has been exposed, so they do not map directly to the Zima severity scale of credential exposure, PII leakage, or active malicious infrastructure.[2]
- Even potentially interesting cases such as `line_type = premium_rate` or specific carriers are at most **contextual risk factors** and must be interpreted in combination with actual exposure or abuse evidence from other sources.

Thus, any severity assigned to a `phone_exposure` signal that uses Numverify data should be determined by the upstream exposure/threat provider and Zima’s correlation logic, with Numverify inputs used only as modifiers or context.

***

## E. Confidence Guidance

Even though Numverify is enrichment-only for `phone_exposure`, its reliability characteristics matter when tuning correlation and risk scoring.

### Confidence Guidance Table

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|-------------------------|---------------------|--------------------------|---------------------|------------------|
| phone_exposure | Use Numverify `/validate` to enrich any phone indicator (validity, normalized formats, country, carrier, line_type) attached to upstream exposure or threat findings. | Numverify cross-checks numbers against "the latest international numbering plan databases" and is operated by APILayer, a long-running provider of data APIs; reliability is expected to be high for structural validity, country code, and dial prefix, but location, carrier, and line type are explicitly documented as sometimes unavailable, indicating imperfect coverage.[2][1] | Numbering plans, carrier assignments, and line-type mappings can change over time; docs promise use of latest numbering plan databases but do not state an update interval, so results for dynamic attributes (especially carrier and line type) should be treated as mostly-current rather than ground truth for historical data.[2] | Treat a single Numverify enrichment result as strong evidence for formatting and country code, but softer evidence for carrier, location, and line type; when those attributes materially affect severity or routing, corroborate using at least one additional source (e.g., another telephony intelligence provider or an internal telco reference) before hard decisions. | During pilot, log Numverify responses alongside at least one other source of truth for subsets of phone indicators (for example, internal customer records or a second validator) and measure disagreement rates by field; use observed disagreement to adjust how much weight carrier/line_type/location should carry in any risk scoring for `phone_exposure` cases. |

***

## F. Provider Summary for Zima

### Strongest signal types and value

- **Phone normalization and structural validity**: Numverify’s `valid`, `international_format`, `local_format`, `country_prefix`, `country_code`, and `country_name` are highly valuable for normalizing phone indicators from disparate upstream providers into a consistent internal representation, improving deduplication and cross-source correlation.[3][2]
- **Carrier and line type context**: The `carrier` and `line_type` fields provide useful risk/contextual signals when combined with exposure data, such as distinguishing mobile vs. VoIP or toll-free numbers, or flagging patterns like repeated exposures involving cheap throwaway carriers.[2]

### What Numverify should not be used for

- **Not a breach or exposure source**: Numverify never indicates that a phone number has been breached, sold, or used maliciously; it knows nothing about data leaks, dark web listings, spam campaigns, or fraud incidents.[1][2]
- **Not an abuse reputation feed**: There are no reputation scores, spam indicators, or threat-intel-style attributions in the schema, so it should not be used to declare a number as abusive, malicious, or compromised on its own.
- **Not an identity or ownership source**: Numverify returns carrier and location information, but nothing that ties a number to a specific individual or account-level identity; it cannot, by itself, confirm that a number actually belongs to a given user.

### API, auth, rate-limit, and licensing cautions

- **API key management**: Every request requires an `access_key` query parameter; missing or invalid keys produce `missing_access_key` / `invalid_access_key` errors. Keys must be stored in Zima’s secrets management, not in rules or mappers.[3][2]
- **Quota and rate limiting**: Docs define per-plan API call quotas and overage pricing; exceeding quotas or per-minute rate limits yields `usage_limit_reached` and `rate_limit_reached` errors, and HTTP 429 in older docs. The provider will continue serving requests and charge overages unless the customer configures otherwise, so the provider client should enforce its own rate/backoff logic.[2]
- **HTTPS vs HTTP**: Earlier docs mention HTTPS access as plan-dependent (`https_access_restricted`), while newer docs state all customers may use HTTPS; client code should always prefer HTTPS and gracefully handle rare HTTPS restriction errors.[3][2]
- **JSONP and formatting**: `callback` and `format=1` are debugging/client-integration aids; Zima’s backend callers should avoid JSONP entirely and never set `format=1` in production, as it increases payload size and complicates parsing.[3][2]

### Evidence and deduplication considerations

- **Field paths to preserve**: For any `phone_exposure` signal sourced from another provider, the Numverify enrichment block should preserve at least `valid`, `number`, `local_format`, `international_format`, `country_prefix`, `country_code`, `country_name`, and, when present, `location`, `carrier`, and `line_type`.[3][2]
- **Natural identifiers**: `international_format` is the best canonical key for deduplicating phone indicators across providers, with `country_code + local_format` as a secondary composite key when international format is missing.[2]
- **Null / empty behavior**: Missing `location`, `carrier`, or `line_type` should be represented as explicit nulls in Zima’s normalized evidence, not as omitted keys, so rules and UIs can distinguish "unknown" from "not requested".[2]

### Layering within Zima

- **Provider client layer**: Handles API key configuration, HTTPS, retry/backoff on `usage_limit_reached` and `rate_limit_reached`, and conversion of the raw JSON from `/validate` and `/countries` into a stable internal provider schema. It should also enforce request throttling based on subscription plan limits and surface structured error conditions to callers.[3][2]
- **Module mapper (`phone_exposure`)**: Consumes the provider client’s normalized output only when another source has already generated a candidate `phone_exposure` signal, attaching the Numverify-derived metadata under the signal’s `evidence`/`enrichment` fields. It must not create new signals based solely on `valid`, `carrier`, or `line_type`, and should avoid treating `valid == false` as either a positive or negative security finding.
- **Correlation layer**: May use Numverify fields (for example, `international_format`, `country_code`, `line_type`) to relate multiple exposures involving the same phone, cluster cases by geography or line type, or adjust severity where Zima has separate evidence that certain line types or carriers are abused more heavily.

### Overall provider role in current Zima stage

- For Zima’s `phone_exposure` module at the current stage, Numverify should be treated as **enrichment-only** and **utility** (for `/countries`) rather than a primary signal producer.
- Future modules focused on data quality or fraud scoring might choose to promote certain Numverify-derived patterns into standalone findings (for example, repeated use of cheap VoIP numbers in high-risk workflows), but that lies outside the scope of the present `phone_exposure` integration.

***

## G. Structured JSON

```json
{
  "provider": "numverify",
  "provider_category": "phone",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "validate",
      "endpoint_or_artifact": "/validate",
      "classification": "enrichment_only",
      "entity_types": ["phone"],
      "gating_logic": "Invoke only when an upstream source has already surfaced a candidate phone indicator; require non-error response (no success:false/error object). On error, treat as missing enrichment and do not alter signal creation. Never treat valid == false as a security finding.",
      "citation_refs": [
        "https://numverify.com/documentation",
        "https://docs.apilayer.com/numverify/docs/getting-started",
        "https://docs.apilayer.com/numverify/docs/api-documentation"
      ],
      "notes": "Provides validation and rich phone metadata (formats, country, carrier, line_type) but no breach/exposure data; should only enrich phone_exposure signals from other providers."
    },
    {
      "module": "phone_exposure",
      "provider_role": "signal_producer",
      "provider_method": "countries",
      "endpoint_or_artifact": "/countries",
      "classification": "utility_only",
      "entity_types": [],
      "gating_logic": "Use only in provider client or configuration flows to cache supported countries and dialing codes; do not call from detection/rules paths.",
      "citation_refs": [
        "https://numverify.com/documentation"
      ],
      "notes": "Static list of country names and dialing codes; not tied to individual indicators or exposures."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "phone_exposure",
      "signal_type_or_use_case": "phone_metadata_enrichment_via_numverify_validate",
      "source_reliability": "High for structural validity and country/dial prefix data based on cross-checking against international numbering plan databases; somewhat lower and explicitly incomplete for location, carrier, and line_type fields.",
      "freshness_considerations": "Numbering plans and carrier assignments can change; docs claim use of latest numbering plan databases but do not specify update cadence, so treat dynamic attributes as mostly-current rather than authoritative for historical data.",
      "corroboration_rules": "Use Numverify as primary normalizer for formatting and country, but corroborate carrier/location/line_type with at least one other source when those attributes materially impact severity or routing.",
      "calibration_todo": "During rollout, compare Numverify output against a secondary source of truth or internal records for a sample of phone indicators and measure disagreement per field; adjust how much weight each field carries in scoring and triage based on observed error rates."
    }
  ]
}
```
