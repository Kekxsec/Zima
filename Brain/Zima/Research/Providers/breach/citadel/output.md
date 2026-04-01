---
title: "output / breach / citadel"
aliases: ["citadel output", "citadel signal registry"]
tags: [zima, research, outputs, signal-registry, breach, citadel, graph_exclude]
type: provider_research_output
provider: citadel
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: citadel.md
obsidianUIMode: preview
---
# Citadel / Leak-Lookup Zima Integration Report

Citadel in your provider map is the SpiderFoot-era name for the Leak-Lookup breach database API (`leak-lookup.com`); for Zima's `credential_exposure` module it should be treated as a real, signal-producing breach provider whose primary integration point is the `/api/search` endpoint, with `/api/hash` as optional enrichment and `/api/stats` as utility-only.

---

## A. API Surface Appendix

### 1. POST `https://leak-lookup.com/api/search` (Search API)

**Purpose**

Searches across all indexed breach datasets for a given identifier (email, username, IP address, phone, domain, password, full name).

**Auth / execution**

- API key required (`key` parameter).
- Public key: free, limited to 10 requests/day, returns only breach names (no row data).
- Private key: paid, business-only, returns full row data for each hit; 10,000-row maximum per query (manual export required beyond that).
- Static IPv4 or CIDR range is optional but recommended to avoid rate-limiting issues.
- Method: `POST`.

**Supported entity types (via `type`)** – documented list:

- `email_address` -> entity_type: email
- `username` -> entity_type: username
- `ipaddress` -> entity_type: ip
- `phone` -> entity_type: phone
- `domain` -> entity_type: domain
- `password` -> entity_type: password (search for a given password across breaches)
- `fullname` -> entity_type: person / fullname

Triggering on each is documented for the API, but which ones Zima should actually use is a Zima design decision.

**Request parameters** (all required)

- `key` (string): API key.
- `type` (string): one of the supported types above.
- `query` (string): search term (email, username, IP, etc.).

**Top-level response fields** – documented shape:

- `error` (string): `"true"` or `"false"`. Always present.
- `message` (object): container for results or error description. Always present.

**Successful response variants**

- **Public API key (documented)** – breach names only:

```json
{
  "error": "false",
  "message": {
    "breach_sitename_1": [],
    "breach_sitename_2": [],
    "breach_sitename_3": [],
    "breach_sitename_4": []
  }
}
```
- Keys under `message` are breach identifiers (typically the “Database Name” you see on `/breaches`, e.g. `linkedin.com`, `citadel.sx`, `special`).

- Arrays are empty for public responses (columns stripped). This is documented: “All indexed columns are stripped from the returned response.”

- **Private API key (documented)** – full row data:

```json
{
  "error": "false",
  "message": {
    "breach_sitename_1": [
      {
        "column1": "value1",
        "column2": "value2",
        "column3": "value3"
      },
      {
        "column1": "value1",
        "column2": "value2"
      }
    ],
    "breach_sitename_2": [
      {
        "column1": "value1",
        "column2": "value2"
      }
    ]
  }
}
```

    - Each key under `message` is a breach name; each value is an array of result rows for that breach.

    - Row fields are per‑breach and may use any of the documented column names below (not guaranteed for every breach).


**Row‑level fields (“Fields” list)** – documented as _possible_ columns, not guaranteed on every row:

Account identifiers / credentials:

- `userid`, `uid`, `memberid`, `member_id`

- `email_address`, `emailaddress`, `email`, `email_address2`, `emailaddress2`, `email2`

- `membername`, `username`, `uname`, `user_name`, `member_name`

- `ipaddress`, `ip_address`, `ip`

- `password`, `password2`, `password3`, `password4`

- `plaintext`

- `hash`

- `salt`, `salt2`, `salt3`

- `secret`, `key`


PII / contact data:

- `firstname`, `first_name`, `fname`

- `lastname`, `last_name`, `lname`

- `fullname`, `full_name`

- `number`, `phone`, `mobile`, `telephone`

- `country`


Address‑type fields (marked “available on request” – likely premium/extra):

- `address`, `address1`, `address2`, `address3`

- `city`, `state`, `county`

- `postcode`, `zipcode`, `postalcode`, `zip`


Breach metadata:

- `breachname`

- `domain_name`

- `fb_id`, `facebook_id`, `fbid`


**Field presence classification**

- `error`, `message`: documented as always present.

- Keys under `message`: present only when there is at least one breach “bucket” in the response (documented); whether a no‑hit returns `{}` vs predefined keys with empty arrays is inferred from examples (docs don’t show no‑hit explicitly).

- All row fields from the “Fields” list: optional and vary by breach; docs explicitly say “we cannot guarantee all fields will be present.”

- Address‑type fields marked “available on request” should be treated as premium‑only / configuration‑dependent.


**Error responses** – documented strings returned in `message` when `error == "true"`:

- `MISSING SEARCH TYPE` – missing `type`

- `MISSING SEARCH QUERY` – missing `query`

- `MISSING API KEY` – missing `key`

- `MISSING REQUIRED PARAMETERS` – some required param missing

- `EMPTY VALUE DETECTED` – parameter present but empty

- `SEARCH FAILED` – internal search failure

- `SEARCH QUERY BLACKLISTED` – disallowed `domain` query, etc.

- `REQUEST LIMIT REACHED` – daily request cap reached

- `RATE LIMIT REACHED` – more than 5 requests in the last minute

- `INACTIVE API KEY` – key exists but inactive

- `INVALID API KEY` – key invalid


HTTP `429` behavior is not mentioned in Leak‑Lookup docs but is handled explicitly in the SpiderFoot `sfp_citadel` module, which retries after 10 seconds when it sees `res['code'] == "429"`. This is derived from client behavior, not directly documented by Leak‑Lookup.

**No‑hit behavior**

- Not explicitly documented.

- From the public API example and typical patterns, it is inferred that:

    - For public keys: no‑hit is either `message: {}` or `message` with no breach keys; or possibly only empty arrays.

    - For private keys: no‑hit is likely `message: {}` or all breach arrays empty.


Implement conservative logic that treats “no keys under `message` OR all arrays empty” as no‑hit.

**Partial / large‑result behavior**

- Docs state a hard cap of 10,000 results per search query for private API; exceeding that requires a manual export.

- This is a documented limit; partial results are returned transparently, but you have no paging mechanism beyond that.


---

## 2. POST `https://leak-lookup.com/api/hash` (Hash API)

**Purpose**

Hash‑cracking service: given an arbitrary hash, returns cracked plaintext if known; otherwise queues the hash for cracking.

**Auth / execution**

- API key required (`key`).

- Method: `POST`.

- Entity_type: hash.


**Request parameters** – all required:

- `key` (string): API key.

- `query` (string): the hash value to search/crack.


**Top‑level response fields** – documented:

- `error` (string): `"true"` or `"false"`.

- `message` (object): contains provider‑specific keys.


**Standard success response** – documented:

```json
{
  "error": "false",
  "message": {
    "hashkiller": [
      {
        "hash": "482c811da5d5b4bc6d497ffa98491e38",
        "plaintext": "password123",
        "salt": ""
      },
      {
        "hash": "482c811da5d5b4bc6d497ffa98491e38",
        "plaintext": "password123",
        "salt": ""
      }
    ]
  }
}
```

- Inside `message`, the key `hashkiller` is an array of result rows.

- Row‑level fields (documented):

    - `hash`

    - `plaintext`

    - `salt`


**Behavior when not yet cracked**

- Docs state: “If the hash has been cracked a plain‑text value will be returned, if not it will be added to the 'cracking' queue.”

- They do not specify how “queued but not yet cracked” appears (empty `hashkiller` vs different key or message string), so exact queue indication is unclear.


**Error responses** – documented error strings in `message` when `error == "true"`:

- `MISSING SEARCH QUERY`

- `MISSING API KEY`

- `MISSING REQUIRED PARAMETERS`

- `EMPTY VALUE DETECTED`

- `SEARCH FAILED`

- `REQUEST LIMIT REACHED`

- `RATE LIMIT REACHED`

- `INACTIVE API KEY`

- `INVALID API KEY`


Same semantics as for `/api/search`.

---

## 3. POST `https://leak-lookup.com/api/stats` (Stats API)

**Purpose**

Account/usage introspection for the current API key: status, type, creation/expiry, request counts, and rate limit.

**Auth / execution**

- API key required (`key`).

- Method: `POST`.

- Entity_type: effectively api_key / provider account; not tied to a Zima entity.


**Request parameters** – required:

- `key` (string): API key.


**Top‑level response fields** – documented:

- `error` (string): `"true"` or `"false"`.

- `message` (object) with:

    - `status` (string): `active` / `inactive`.

    - `type` (string): `public` / `private` / `inactive`.

    - `added` (string): `Y-m-d` (date key was added).

    - `updated` (string): `Y-m-d H:i:s` (last allowance reset).

    - `expiry` (string): `Y-m-d H:i:s` (key expiry).

    - `requests` (integer): current request count.

    - `limit` (integer): current daily request limit.


These fields are described as standard; treat them as always present when `error == "false"`.

**Error responses** – documented strings in `message` when `error == "true"`:

- `MISSING API KEY`

- `MISSING REQUIRED PARAMETERS`

- `EMPTY VALUE DETECTED`

- `INVALID API KEY`


---

## 4. HTML `/breaches` (Databases listing – non‑API artifact)

**Purpose**

Human‑oriented listing of all indexed breach “databases”, including total counts and per‑breach metadata.

**Fields (per page)** – from the HTML table:

- Global summary:

    - `Total Records`

    - `Total Breaches`

- “Latest Indexed Breaches” and “Indexed Breaches” tables, per row:

    - `Database Name` (breach identifier, e.g. `linkedin.com`, `citadel.sx`, `special`).

    - `Record Count`.

    - `Date Indexed`.

    - `Options` (currently usually blank).


**Relationship to API**

- `Database Name` aligns with breach keys under `message` in the `/api/search` response (e.g. `linkedin.com`, `special`).

- There is no documented JSON API for these tables; scraping or offline mirroring would be inferred / non‑official behavior.


Because it’s HTML only, this artifact is enrichment‑only for Zima.

---

## B. Module Mapping Table

## Module–endpoint mapping

| module              | provider_role   | provider_method | endpoint_or_artifact                            | classification       | entity_types                              | gating_logic                                                                                                                                                                                                                 | citation_refs                                                                                     | notes |
|---------------------|-----------------|-----------------|-------------------------------------------------|----------------------|-------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|-------|
| credential_exposure | signal_producer | search          | `POST https://leak-lookup.com/api/search`       | direct_signal_input  | email (primary); username, ip, phone, domain, password, fullname (optional future) | Only call when you have an entity that maps cleanly to a supported `type` value; require non‑empty API key; treat responses with `error == "false"` and a non‑empty `message` (at least one breach key) as candidate hits; ignore or log but do not signal on `error == "true"`, `REQUEST LIMIT REACHED`, `RATE LIMIT REACHED`, `INVALID/INACTIVE API KEY` or empty/zero‑row `message` (no‑hit). Hit gating is derived from documented fields plus examples. | Search docs, fields and errors for `/api/search`.[1] SpiderFoot `sfp_citadel` shows email‑only usage with `type=email_address` and `query` set to the email, and handles HTTP 429 by retrying.[2] Leak‑Lookup marketing describes it as a breach/credential monitoring API.[3] | This is the only endpoint that directly surfaces “email found in breach X” as a primary detection input for `credential_exposure`. Use a private API key if you want row‑level evidence; with public keys you only get breach names, not row data.[1][4] |
| credential_exposure | signal_producer | hash            | `POST https://leak-lookup.com/api/hash`         | enrichment_only      | hash                                      | Only call when you already have a leaked credential hash (e.g. from another provider or internal logs) and want to know whether Leak‑Lookup has a cracked plaintext; require valid API key; treat `error == "false"` and non‑empty `message.hashkiller` as enriched evidence on an existing credential exposure, not as a new breach detection on its own (trigger semantics are derived from docs). | Hash API docs for parameters, fields, and behavior.[5] General API key and rate‑limit semantics shared with `/api/search`.[1][4] | Best treated as a helper that elevates severity (plaintext known, password reuse risk high) or adds remediation context (which password is exposed). For Zima v1 you can leave it unused for `credential_exposure` and revisit under a future `secrets` module. |
| credential_exposure | signal_producer | stats           | `POST https://leak-lookup.com/api/stats`        | utility_only         | api_key                                  | Use only inside the Citadel/Leak‑Lookup client to introspect key status and quota; never emit signals from this endpoint. If `status != "active"` or `type == "inactive"`, the provider client should short‑circuit before calling `/api/search` or `/api/hash`. | Stats API docs with fields and example response.[6]                                          | Purely operational telemetry: request counts, daily limit, expiry. Use to back off before hitting hard errors, and for monitoring/billing in a provider health dashboard. |
| credential_exposure | signal_producer | breaches_html   | `GET https://leak-lookup.com/breaches` (HTML)   | enrichment_only      | breach / site_name (internal)            | Optional offline job; if used, scrape or mirror the breaches table to map each breach name to `record_count` and `date_indexed`. Do not gate signal creation on this page; only use to enrich signals produced from `/api/search`. Behavior is inferred since no JSON API is documented. | Breaches page listing database name, record count and date indexed.[7]                        | Because this is HTML, not an official JSON API, treat it as best‑effort enrichment. Ensure scraping throttling so you do not break ToS, and consider maintaining your own synchronized snapshot rather than live scraping. |

**Citadel vs Leak‑Lookup naming**

- SpiderFoot’s module `sfp_citadel` is documented as “Leak‑Lookup – Searches Leak‑Lookup.com's database of breaches.”

- The data source block points to `https://leak-lookup.com/` and its API/docs.

- Historical references to `citadel.pw` describing “Citadel / Leak - Lookup | Database Search Engine” appear to be the old domain for the same backend, now expired.


For Zima, treat `citadel` as the provider alias for Leak‑Lookup, and standardize on `leak-lookup.com` endpoints.

---

## C. Signal Contract Table

Only one standalone signal type is justified for the `credential_exposure` module with Citadel/Leak‑Lookup today; everything else is enrichment or utility around that core finding.

## Module‑level signal contracts

| module              | source              | provider | provider_method | signal_type             | category         | severity | severity_is_conditional | conditional_rule                                                                                                                                                                                                                                                         | entity_type | finding_kind        | trigger_condition                                                                                                                                                                                                                                                                                                               | evidence_fields                                                                                                                                                                                                                                                                                                            | enrichment_fields                                                                                                                                                                                                                                                                                                                                                                 | summary_template                                                                                                             | evidence_status | citation_refs                                                                                                                                                                             | notes |
|---------------------|---------------------|----------|-----------------|-------------------------|------------------|----------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|---------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|-----------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------|
| credential_exposure | credential_exposure | citadel  | search          | credential_breach_found | account_security | medium   | yes                     | Start at medium when a given email has at least one breach hit but only email/username and no password/hash/secret fields; escalate to high if any row for that email in any breach contains `hash` or any of `password`, `password2`, `password3`, `password4`, `secret`, `key` but `plaintext` is absent; escalate to critical if any row contains non‑empty `plaintext` or an obviously usable password field (e.g. a non‑hashed `password*`) indicating direct credential exposure. This logic is derived from the documented field list and Zima’s severity calibration. | email      | true_finding        | For an email entity, call `/api/search` with `type=email_address` and `query=<email>` using a valid API key. If the JSON response has `error == "false"` and `message` is a non‑empty object with at least one breach key whose array contains ≥1 row (private key) or at least one breach key is present (public key), emit a `credential_breach_found` signal for that email. Do not emit if `error == "true"`, or if `message` is empty / all arrays are empty. This trigger is derived from the documented response shape plus SpiderFoot’s pattern of treating any non‑empty `message` as a hit. | Top‑level: `error`, `message`. Request‑side context: `type`, `query`, API key type (public/private – from `/api/stats` or provider config). Within `message`: full per‑breach arrays as returned, particularly any of: `email`, `email_address*`, `username`, `ipaddress`/`ip_address`/`ip`, `password`, `password2`, `password3`, `password4`, `plaintext`, `hash`, `salt`, `salt2`, `salt3`, `secret`, `key`, `breachname`, `domain_name`, `country`, `firstname`/`lastname`/`fullname`, `phone`/`mobile`/`telephone`. All of these are documented as possible fields but optional; mapper should preserve them as raw evidence when present.[1] | Context but not separate findings: per‑breach record counts and `Date Indexed` from `/breaches` (if you maintain a synchronized copy); inferred breach metadata such as `Database Name` (breach key) → site/domain; non‑credential PII fields (names, phones, addresses) should be stored as enrichment to support impact analysis and notification but not create new signals by themselves. All of this is derived from the breaches listing and the documented field list.[7][1] | `Email {{entity}} appears in {{breach_count}} external credential breach dataset(s) indexed by the Citadel (Leak‑Lookup) provider.` | derived         | Search API docs for request/response, fields and errors.[1] Leak‑Lookup marketing describes real‑time data breach monitoring, credential exposure, and password policy enforcement use cases.[3] Breach catalogue page shows the list of individual breaches (e.g. `linkedin.com`, `citadel.sx`, `special`) and counts, which align with the breach keys returned in `message`.[7] SpiderFoot `sfp_citadel` maps `EMAILADDR` to `EMAILADDR_COMPROMISED` when Leak‑Lookup returns any entries, confirming the “email in breach database” semantics.[2][8] | This contract assumes you have a private API key; with only a public key you still know that an email appears in one or more breaches, but you do not see row fields (passwords, hashes, PII), so you can only operate the “breach name only” part of the logic (still a medium/high finding depending on your policy).[1][4] Some breach names (e.g. `special`) represent aggregated or less‑well‑labeled datasets; the “confirmed breach” semantics are inherited from Leak‑Lookup’s curation, not independently validated by Zima – calibration should account for potential noise.[7] There is no explicit timestamp per row in the API; if you want recency‑aware scoring, you must enrich from `/breaches` (Date Indexed) or external sources. |

Rationale:

- `category = account_security` because the primary risk is account takeover through exposed credentials tied to an email identity.

- `finding_kind = true_finding` because the provider asserts and documents that it stores real breach data and returns per‑email exposure hits, not just reputation scores.

- Severity logic follows your calibration (see next section).


---

## D. Severity Rules

For `credential_breach_found`:

- **Base severity:** `medium`

    - Reason: confirms the email appears in at least one external breach dataset; by itself this is a confirmed breach at the identity level but not necessarily a live password exposure.

- **Conditional escalation (derived from fields)**:

    - **High** when any row for the email contains:

        - Non‑empty `hash` and no `plaintext`.

        - Or non‑empty `password`/`password2`/`password3`/`password4`/`secret`/`key` fields where values appear hashed.

    - **Critical** when any row contains:

        - Non‑empty `plaintext` representing the actual password.

        - Or a `password*` field that is clearly plaintext.


This maps directly onto your calibration: plaintext passwords or direct secrets → critical; confirmed credential leaks (hashes) → high; unqualified “email in breach” → medium.

---

## E. Confidence Guidance

## Confidence & calibration table

| module              | signal_type_or_use_case    | source_reliability                                                                                                                                                                                                       | freshness_considerations                                                                                                                                                                                                    | corroboration_rules                                                                                                                                                                                                                 | calibration_todo                                                                                                                                                                                                                                                                                                         |
|---------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| credential_exposure | credential_breach_found    | Leak‑Lookup positions itself as a dedicated breach database with billions of records and over 4,500 indexed breaches, investing profits into acquiring new leaks/dumps.[3][7] SpiderFoot and other OSINT tools treat it as a mainstream breach source, implying moderate‑to‑high trust in its backend, but data is aggregated from many underground/public sources, so some datasets (e.g. `special`) may be noisy or partially verified.[7][2] | `/breaches` exposes `Date Indexed` per database but not original breach dates; the API doesn’t expose per‑row timestamps.[7][1] Consider treating all hits as historical by default, downgrading severity for very old breaches and focusing operational urgency on: (a) breaches indexed in the last N months, and (b) credentials still in use according to your identity telemetry. | For high‑impact actions (forced password reset, user notifications), corroborate Leak‑Lookup hits against at least one other data source (e.g. HIBP, DeHashed, internal compromise investigations) where available; also validate that the exposed email actually belongs to your current user population to avoid overreacting to “lookalike” or non‑employee hits. Rules here are derived best practices, not vendor‑specific. | 1) Ingest a representative sample of Citadel/Leak‑Lookup hits, compare with other breach providers and internal incident records to estimate false‑positive/false‑negative rates per breach and per field combination. 2) Track distribution of `plaintext` vs `hash`‑only vs “email only” hits to calibrate severity breakpoints. 3) Add a recency/age dimension using `/breaches` “Date Indexed” and, where possible, external breach‑date metadata to decide when old hits should be downgraded to low/medium. 4) Revisit confidence once you’ve observed how often Leak‑Lookup reports breaches that are missing or contradicted elsewhere. |

In practice, start with medium confidence for “any hit” and refine as you measure overlap and noise against other breach feeds.

---

## F. Tags

For `credential_breach_found` from Citadel/Leak‑Lookup, suggested tags:

- `breach` – core breach dataset membership.

- `credential_stuffing` – exposed credentials are candidates for stuffing attacks.

- `plaintext_password` – when severity escalates to critical based on plaintext.

- `pii_exposure` – when PII fields (names, phones, address) are present.


Only apply `plaintext_password` and `pii_exposure` when the corresponding fields are actually present.

---

## G. Provider Summary & Implementation Notes

## Strongest signal types

- Email‑level credential exposure: mapping specific identifiers (primarily emails) to one or more named breach datasets, with row‑level columns for passwords, password hashes, salts, secrets, and PII when using a private key.

- Password intelligence (optional): the Hash API can convert leaked hashes into plaintexts, improving severity assessment and remediation.


## What the provider should _not_ be used for

- Not an IP/domain reputation feed, malware/C2 feed, or phishing URL feed – no time‑series telemetry or active infrastructure labels.

- Not a general dark‑web monitoring platform; it is focused on breach/credential search.

- Not a code/repo secret scanner; it only covers leaks present in breach dumps.


## API/auth/rate‑limit/licensing cautions

- Public keys: free, 10 requests/day, breach names only.

- Private keys: business‑only, paid, higher limits, 10,000‑row cap per query, may require manual exports for very large hits.

- Rate limits:

    - `REQUEST LIMIT REACHED` when daily cap reached.

    - `RATE LIMIT REACHED` if more than 5 requests/min.

    - SpiderFoot’s `sfp_citadel` also anticipates HTTP 429 and backs off 10s before retrying.

- Static IP/CIDR recommended to avoid rate‑limit issues.

- Private key issuance is restricted and subject to terms; abuse leads to termination.


Implementation guidance:

- Use `/api/stats` for pre‑flight checks, monitoring, and to distinguish public vs private behavior.

- Implement robust handling of message‑level errors and HTTP‑level throttling (backoff, retry, circuit‑breaker).

- Keep key and IP/CIDR configuration in the provider client, not in module mappers or rules.


## Role in current Zima stage

- For `credential_exposure`, Citadel/Leak‑Lookup is a **signal‑producing** provider with a single core signal (`credential_breach_found`) from `/api/search` and optional enrichment from `/api/hash` and `/breaches`.

- `/api/stats` remains utility‑only, powering provider health and quota checks.


---

## H. Structured JSON

```json
{
  "provider": "citadel",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "search",
      "endpoint_or_artifact": "POST https://leak-lookup.com/api/search",
      "classification": "direct_signal_input",
      "entity_types": [
        "email",
        "username",
        "ip",
        "phone",
        "domain",
        "password",
        "fullname"
      ],
      "gating_logic": "Call only when the entity can be mapped to a supported `type` value. Require non-empty API key. Treat responses with error == \"false\" and a non-empty `message` object (at least one breach key, and for private keys at least one row in any breach array) as hits. Do not emit signals when error == \"true`, when message is empty or all arrays are empty, or when message contains REQUEST LIMIT REACHED / RATE LIMIT REACHED / INVALID API KEY / INACTIVE API KEY.",
      "citation_refs": [
        "https://leak-lookup.com/docs/search",
        "https://leak-lookup.com/support/api",
        "https://github.com/smicallef/spiderfoot/blob/master/modules/sfp_citadel.py"
      ],
      "notes": "Primary integration for credential_exposure. Private keys return full row data (passwords, hashes, PII); public keys only return breach names. Rate limits apply and are enforced both via error messages and possibly HTTP 429."
    },
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "hash",
      "endpoint_or_artifact": "POST https://leak-lookup.com/api/hash",
      "classification": "enrichment_only",
      "entity_types": [
        "hash"
      ],
      "gating_logic": "Only call when you already have a leaked credential hash from another source and want to know if a plaintext exists. Require non-empty API key. Treat error == \"false\" and non-empty `message.hashkiller` as enrichment on an existing exposure, not a standalone detection.",
      "citation_refs": [
        "https://leak-lookup.com/docs/hash",
        "https://leak-lookup.com/support/api"
      ],
      "notes": "Hash API is best used to confirm/plaintext leaked passwords and improve remediation and severity, not as primary breach detection. Behavior when a hash is queued but not yet cracked is not fully documented."
    },
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "stats",
      "endpoint_or_artifact": "POST https://leak-lookup.com/api/stats",
      "classification": "utility_only",
      "entity_types": [
        "api_key"
      ],
      "gating_logic": "Use to check key status, type, expiry, and remaining limit before performing search/hash calls. If status != active or type == inactive, short-circuit further calls.",
      "citation_refs": [
        "https://leak-lookup.com/docs/stats"
      ],
      "notes": "No signals should be emitted from this endpoint; it is purely for provider client health and quota management."
    },
    {
      "module": "credential_exposure",
      "provider_role": "signal_producer",
      "provider_method": "breaches_html",
      "endpoint_or_artifact": "GET https://leak-lookup.com/breaches (HTML)",
      "classification": "enrichment_only",
      "entity_types": [
        "breach"
      ],
      "gating_logic": "Optional offline/scheduled job. If used, scrape or mirror the breaches table to map breach names to record counts and Date Indexed. Do not gate detection on this; only enrich signals based on search results.",
      "citation_refs": [
        "https://leak-lookup.com/breaches"
      ],
      "notes": "This is not a documented JSON API. Any use is best-effort enrichment and should respect rate limits and terms of service."
    }
  ],
  "signal_contracts": [
    {
      "module": "credential_exposure",
      "source": "credential_exposure",
      "provider": "citadel",
      "provider_method": "search",
      "signal_type": "credential_breach_found",
      "category": "account_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Start at medium when at least one breach hit exists for the email but no password/hash/secret fields are present. Escalate to high if any row contains a non-empty `hash` or password/secret/key field but no `plaintext`. Escalate to critical if any row contains non-empty `plaintext` or a clearly reusable plaintext password.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "For an email entity, POST to https://leak-lookup.com/api/search with type=email_address and query=<email>. If error == \"false\" and `message` is a non-empty object with at least one breach key whose array contains one or more rows (for private keys) or at least one breach key is present (for public keys), emit a credential_breach_found signal. Do not emit when error == \"true\" or `message` is empty/all arrays empty.",
      "evidence_fields": [
        "response.error",
        "response.message",
        "request.type",
        "request.query",
        "stats.type (public/private)",
        "message[breach_name][].email*",
        "message[breach_name][].username",
        "message[breach_name][].ipaddress/ip_address/ip",
        "message[breach_name][].password/password2/password3/password4",
        "message[breach_name][].plaintext",
        "message[breach_name][].hash",
        "message[breach_name][].salt/salt2/salt3",
        "message[breach_name][].secret",
        "message[breach_name][].key",
        "message[breach_name][].breachname",
        "message[breach_name][].domain_name",
        "message[breach_name][].country",
        "message[breach_name][].firstname/lastname/fullname",
        "message[breach_name][].phone/mobile/telephone"
      ],
      "enrichment_fields": [
        "breach_name (key under message)",
        "breach_metadata.record_count (from /breaches snapshot)",
        "breach_metadata.date_indexed (from /breaches snapshot)",
        "non-credential PII fields used for impact analysis and contact (names, phones, addresses)",
        "any organization-specific mapping of breach names to business systems"
      ],
      "summary_template": "Email {{entity}} appears in {{breach_count}} external credential breach dataset(s) indexed by the Citadel (Leak-Lookup) provider.",
      "evidence_status": "derived",
      "citation_refs": [
        "https://leak-lookup.com/docs/search",
        "https://leak-lookup.com/support/api",
        "https://leak-lookup.com/breaches",
        "https://github.com/smicallef/spiderfoot/blob/master/modules/sfp_citadel.py"
      ],
      "notes": "Assumes use of a private API key for full row-level evidence; with a public key only breach names are visible. Age of breaches and verification status vary; use additional calibration and corroboration before enforcing high-impact remediation. Some breach buckets (e.g. 'special') aggregate multiple datasets and may be noisier."
    }
  ],
  "confidence_guidance": [
    {
      "module": "credential_exposure",
      "signal_type_or_use_case": "credential_breach_found",
      "source_reliability": "Moderate to high: Leak-Lookup maintains billions of breach records and thousands of datasets, and is integrated into established OSINT tools such as SpiderFoot, but data originates from a mix of public and underground sources and some datasets may be less verified.",
      "freshness_considerations": "API responses lack per-record timestamps; only the /breaches catalogue exposes Date Indexed per database. Treat all hits as historical by default and optionally downgrade very old breaches or those predating the user's relationship with your organization.",
      "corroboration_rules": "Before triggering org-wide remediations, corroborate high-severity hits (especially critical, plaintext exposures) against at least one other breach provider or internal compromise data where possible, and ensure the exposed identifier belongs to a current, in-scope user or account.",
      "calibration_todo": "Collect a sample of hits and compare against other breach sources to measure overlap and noise. Analyze field combinations (plaintext vs hash vs email-only) and breach recency to tune severity thresholds. Add age-based downgrades once you have a reliable mapping of breach names to breach dates."
    }
  ]
}
```
