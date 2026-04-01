---
title: "output / breach / ghostproject"
aliases: ["ghostproject output", "ghostproject signal registry"]
tags: [zima, research, outputs, signal-registry, breach, ghostproject, graph_exclude]
type: provider_research_output
provider: ghostproject
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: ghostproject.md
obsidianUIMode: preview
---
# GhostProject Integration Reference

## Overview

GhostProject should be treated as a **signal-producing provider** for Zima’s `credential_exposure` module. Its primary value is returning historical breach membership for identities, with optional credential and PII data that can strengthen severity and enrichment handling.

---

## A. API Surface Appendix

### Endpoint: `GET https://ghostproject.fr/api`

**Purpose**

Programmatic search over GhostProject’s breach database to retrieve pwned data such as email addresses, usernames, passwords, and related metadata.

### Supported `entity_type` values

Directly supported via the `column` parameter and observed dataset fields:

- `email`
- `username`
- `password`
- `password2`
- `ip`
- `Database_name`
- `fullname`
- `address`
- `phoneNumber`
- `fax`
- `city`
- `zip`
- `stats`
- `company`

For Zima’s `credential_exposure` module, the primary `entity_type` should be:

- `email`

Possible future extensions:

- `username`
- `phone`

### Auth and execution requirements

- Requires a paid subscription.
- API key is obtained from the GhostProject account UI.
- API key is passed via the `api_key` query parameter.
- Provider policy restricts usage to:
  - improving your own security
  - KYC / AML
  - fraud reduction
- Policy also requires:
  - securing credentials
  - respecting rate limits
  - deleting API-obtained data within 30 days

### Request

- **Method:** `GET`
- **Endpoint:** `https://ghostproject.fr/api`

### Core query parameters

| Field | Type | Description |
|---|---|---|
| `api_key` | string | Required API key for authentication |
| `column` | string | Search column; examples include `username`, `email`, `password`, `ip`, `Database_name`, `fullname`, `address`, `phoneNumber` |
| `username` | string | Described in docs as “a string array of columns”; likely legacy or mislabelled |
| `search_string` | string | Query value; supports exact match with quotes or wildcard without quotes |
| `row` | integer | Optional; default `10`; accepted range `1–1000` |
| `type` | string | Optional; default `json`; supported values: `json`, `xml`, `csv` |

### Additional query behavior

#### Exact vs wildcard search

- `search_string="[email protected]"` → exact email match
- `search_string=ghostproject` → wildcard or fuzzy search, potentially many hits

#### Email wildcard and domain search

Observed / described patterns include:

- `*@ghostproject.fr`
- `@ghostproject.fr`
- `ghostproject.fr`

GhostProject documentation indicates email wildcard queries must contain:

- exactly one `*`
- exactly one `@`

#### Special characters and escaping

Docs reference Solr-style escaping for special characters such as:

- `+`
- `-`
- `&&`
- `||`
- `!`
- `(`
- `)`
- `{`
- `}`
- `[`
- `]`
- `^`
- `"`
- `~`
- `*`
- `?`
- `:`
- `\`

CSV separator handling via `sep` is also mentioned in examples, though not formalized as a documented field enum.

### Top-level response shape (JSON)

GhostProject docs show a Solr-like response structure.

#### `responseHeader`

| Field | Type | Description |
|---|---|---|
| `params` | object | Request parameter details |
| `params.rows` | string | Requested row count |
| `params.wt` | string | Writer type, e.g. `json` |
| `params.indent` | string | Indentation flag |
| `params.q` | string | Underlying query, e.g. `email:\"[email protected]\"` |
| `status` | integer | `0` on success |
| `QTime` | integer | Query execution time |

#### `response`

| Field | Type | Description |
|---|---|---|
| `docs` | array<object> | Result records |
| `numFound` | integer | Total number of matches |
| `start` | integer | Offset |

### Example documented record shapes

#### Example 1: business / PII record without password

Fields observed in `docs[0]`:

- `email`
- `fax`
- `phoneNumber`
- `company`
- `address`
- `url`
- `city`
- `Database_name`
- `zip`
- `stats`

#### Example 2: credential record with password

Fields observed in `docs[0]`:

- `email`
- `password`
- `Database_name`

#### Additional observed fields from third-party client behavior

- `password2`
- `username`
- `fullname`

Some third-party code also suggests clustered or iterable response handling, where items may contain nested `response.docs`.

### Field presence classification

#### Always or near-always for `column=email`

- `response.numFound`
- `response.docs`
- `responseHeader.status`
- `responseHeader.params.q`
- `docs[].email`
- `docs[].Database_name`

#### Optional or conditional

- `docs[].password`
- `docs[].phoneNumber`
- `docs[].address`
- `docs[].city`
- `docs[].zip`
- `docs[].company`
- `docs[].fax`
- `docs[].url`
- `docs[].stats`
- `docs[].password2`
- `docs[].username`
- `docs[].fullname`

### Response variants

#### Successful hit

- HTTP `200`
- `response.numFound > 0`
- `response.docs` contains one or more result objects

#### Successful no-hit

Inferred behavior:

- HTTP `200`
- `response.numFound = 0`
- `response.docs = []`

#### Partial or truncated result

Likely influenced by:

- requested `row` value
- plan-based wildcard limits
- server-side caps

No explicit partial-result flag is documented.

### Error cases

| HTTP Status | Condition | Example message |
|---|---|---|
| `401` | Subscription expired | `Your subscription is expired. Please purchase again.` |
| `401` | Invalid API key | `Invalid API key api_key.` |
| `400` | Missing required field(s) | `Column is required column for this X.` |
| `400` | Disallowed characters | `Special characters is not allowed.` |

### Important implementation examples

GhostProject docs explicitly demonstrate:

- a record with business / PII fields only
- a record with `email + password + Database_name`

FAQ material also references a historical corpus containing cleartext credentials, indicating the provider’s strong orientation toward historical credential exposure.

### Evidence classification

| Aspect | Confidence |
|---|---|
| Response structure, core field names, error codes | documented |
| PII fields in example records | documented |
| Per-dataset PII consistency | unknown |
| `username`, `password2`, `fullname` fields | inferred from client examples |
| Clustered JSON-list response pattern | inferred |
| No-hit format | inferred |
| Truncation semantics | inferred |

---

## B. Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | notes |
|---|---|---|---|---|---|---|---|
| `credential_exposure` | `signal_producer` | `GET /api` query search by identity | `GET https://ghostproject.fr/api` | `direct_signal_input` | `email`, `username`, `phone` | Require valid API key and active subscription. Enforce strict provider cooldown, preferably `5–10s` between requests. Only create signals when HTTP `200` and `response.numFound > 0` for the queried identity. | GhostProject is a dedicated breach search engine returning pwned accounts with email, optional password, breach name, and sometimes PII. It is best treated as a primary source for credential exposure. |

### Mapping conclusion

No other Zima modules appear directly supported by GhostProject. It does **not** provide:

- live threat infrastructure telemetry
- malware telemetry
- DNS / WHOIS intelligence
- IOC feeds
- real-time network reputation

---

## C. Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `credential_exposure` | `credential_exposure` | `ghostproject` | `GET https://ghostproject.fr/api` with `column=email` and `type=json` | `credential_exposed_in_breach` | `identity_security` | `high` | `yes` | Default to `high` when `response.numFound > 0`. Consider escalating to `critical` when `password` or `password2` is present and calibration shows the value is typically cleartext or trivially reversible. | `email` | `true_finding` | HTTP `200` and JSON body where `response.numFound > 0` and at least one `response.docs[i].email` or other searched field equals the queried identity | `response.docs[].email`, `response.docs[].password`, `response.docs[].Database_name`, `request.column`, `request.search_string`, `request.row` | `response.docs[].url`, `response.docs[].phoneNumber`, `response.docs[].address`, `response.docs[].city`, `response.docs[].zip`, `response.docs[].stats`, `response.docs[].username`, `response.docs[].fullname`, `response.docs[].password2` | `Credentials for {email} were found in the GhostProject breach database (example source: {Database_name}).` | `documented` | Treat any hit as confirmed historical breach membership. Password format and exploitability must be calibrated before assuming plaintext. Dedupe on `(email, Database_name, normalized_password, provider, module)`. |

### Signal design notes

- Use a provider-agnostic `signal_type`:
  - `credential_exposed_in_breach`
- Treat records as:
  - `true_finding`
- Avoid creating a provider-specific signal unless there is a clear downstream reason.

Potential future refinement:

- introduce a lower-priority signal such as `breach_membership_without_password` only if production data shows that passwordless records are materially less actionable

---

## D. Severity Rules

### Base severity

- **Base severity:** `high`

### Rationale

GhostProject returns records sourced from known breach corpora or dumped credential datasets. Even where a password field is absent, identity presence in such a dataset is still a meaningful historical exposure.

### Conditional severity logic

#### High

Apply `high` when:

- `response.numFound > 0`
- and either:
  - no password field is present
  - or later calibration shows password values are often hashed or low-exploitability

Interpretation:

- confirmed breach membership
- exposed identity and possibly PII
- not yet proven direct plaintext credential compromise

#### Critical

Candidate escalation to `critical` when:

- record includes non-empty `password` or `password2`
- and calibration shows these values are commonly:
  - cleartext
  - trivially reversible
  - otherwise immediately exploitable

Interpretation:

- direct credential exposure
- strong account takeover relevance
- closer alignment with “plaintext password exposure”

#### Optional nuance

PII-heavy records may justify upward weighting within `high`, especially if they include combinations such as:

- email
- phone number
- address
- fullname

This does not automatically justify `critical`, but it increases impact.

### First-pass recommendation

The correct initial implementation is:

- default all confirmed hits to `high`
- reserve `critical` for empirically validated password exposure conditions

Do **not** assume plaintext simply because GhostProject historically references cleartext dumps.

---

## E. Confidence Guidance Table

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| `credential_exposure` | `credential_exposed_in_breach` | Large dedicated breach corpus with billions of accounts and many databases. Strong for historical exposure, but provenance is heterogeneous. | API does not expose per-record timestamps. Treat hits as historical exposure rather than recent activity unless corroborated elsewhere. | Cross-check with other breach providers. Use `Database_name` to align with known breach references. Sample password-bearing records on test identities to understand exploitability. | Sample `50–100` hits across test identities or domains. Measure password format distribution, PII prevalence, overlap with other sources, and whether password presence should drive severity escalation. |

### Confidence interpretation

GhostProject is suitable as a **high-confidence source of historical breach membership**, but weaker for:

- timing precision
- breach chronology
- recent-event interpretation
- password exploitability assumptions without calibration

---

## F. Tags per Signal Type

### For `credential_exposed_in_breach`

Baseline tags:

- `breach`
- `credential_stuffing`

Conditional tags:

- `plaintext_password`
- `pii_exposure`

### Recommended baseline tagging rule

Use this default set unless calibration proves more:

```json
["breach", "credential_stuffing"]
```

Then conditionally add:

- `plaintext_password` when password handling rules justify it

- `pii_exposure` when meaningful contact or identity fields are present


---

## G. Provider Summary (Implementation-Focused)

### Strongest signal types

GhostProject is strongest for:

- direct evidence that an identity appears in a breach corpus

- breach attribution via `Database_name`

- optional password exposure evidence

- optional PII exposure enrichment


### What GhostProject should not be used for

GhostProject should **not** be treated as:

- a live IOC provider

- a malware telemetry source

- a stealer-log telemetry source

- a DNS / WHOIS intelligence source

- a network reputation provider

- a real-time attack detection feed


### API, auth, rate-limit, and licensing cautions

- Requires paid access and a valid API key

- Usage is contractually restricted

- Retrieved data may need to be deleted within 30 days

- Rate limiting guidance is inconsistent across docs, so implement the stricter policy:

    - `5–10 seconds` between requests

- GhostProject logs:

    - IPs

    - queries

    - user agents


Operational implication:

- avoid querying unnecessarily sensitive identifiers

- route requests in a way that matches internal privacy expectations

- make retention and deletion handling explicit in the integration


### Overall provider role for Zima

|Attribute|Value|
|---|---|
|Provider role|`signal_producer`|
|Primary module|`credential_exposure`|
|Best use case|Historical breach membership and credential exposure detection|
|Integration priority|High|
|Immediate recommendation|Build one canonical signal type first, then add severity / tag conditioning after calibration|

---

## H. Structured JSON

```json
{
  "provider": "ghostproject",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "GET https://ghostproject.fr/api (query searching by identity)",
      "endpoint_or_artifact": "GET https://ghostproject.fr/api",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username", "phone"],
      "gating_logic": "Require valid API key and active subscription; obey provider rate limit (default to 5–10 seconds between requests per API policy); only create signals when HTTP 200 and response.numFound > 0 for the queried identity.",
      "citation_refs": [
        "https://ghostproject.fr/docs/",
        "https://ghostproject.fr/faq/",
        "https://ghostproject.fr/policy",
        "https://ghostproject.fr"
      ],
      "notes": "GhostProject is a dedicated breach search engine returning pwned accounts with email, optional password, breach name, and sometimes PII; primary source for credential_exposure."
    }
  ],
  "signal_contracts": [
    {
      "module": "credential_exposure",
      "source": "credential_exposure",
      "provider": "ghostproject",
      "provider_method": "GET https://ghostproject.fr/api with column=email and type=json",
      "signal_type": "credential_exposed_in_breach",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Default high when response.numFound > 0 for the searched identity. Consider escalating to critical when a password (or password2) field is present and calibration shows it is typically cleartext or trivially reversible.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "HTTP 200 from GhostProject API and JSON body where response.numFound > 0 and at least one response.docs[i].email (or other searched column value) equals the queried identity.",
      "evidence_fields": [
        "response.docs[].email",
        "response.docs[].password",
        "response.docs[].Database_name",
        "request.column",
        "request.search_string",
        "request.row"
      ],
      "enrichment_fields": [
        "response.docs[].url",
        "response.docs[].phoneNumber",
        "response.docs[].address",
        "response.docs[].city",
        "response.docs[].zip",
        "response.docs[].stats",
        "response.docs[].username",
        "response.docs[].fullname",
        "response.docs[].password2"
      ],
      "summary_template": "Credentials for {email} were found in the GhostProject breach database (example source: {Database_name}).",
      "evidence_status": "documented",
      "citation_refs": [
        "https://ghostproject.fr/docs/",
        "https://ghostproject.fr/faq/",
        "https://ghostproject.fr",
        "https://gist.github.com/cyberitech/f03d7e6f73eb275d483847e30594ec59"
      ],
      "notes": "Treat any hit as confirmed historical breach membership. Exact recency and password format (cleartext vs hashed) must be determined via calibration; do not assume plaintext until sampled. Dedupe on (email, Database_name, normalized password) plus provider/module."
    }
  ],
  "confidence_guidance": [
    {
      "module": "credential_exposure",
      "signal_type_or_use_case": "credential_exposed_in_breach",
      "source_reliability": "Large dedicated breach corpus (>15B accounts, thousands of databases) sourced from public dumps and donations; good for historical exposure but heterogeneous provenance and no per-record timestamps.",
      "freshness_considerations": "Contains at least some 2017-era dumps and later additions; API does not expose breach or record dates. Treat as historical exposure unless corroborated with external breach timelines.",
      "corroboration_rules": "Cross-check GhostProject hits with other breach providers and internal incident logs; use Database_name to align with known breaches; sample password fields on test accounts to validate format and exploitability.",
      "calibration_todo": "Sample responses for test domains to measure password cleartext rate and PII presence; compute overlap with other breach sources; finalize severity escalation thresholds and confidence weighting based on empirical coverage and quality."
    }
  ]
}
```
