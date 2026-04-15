---
title: "output / breach / illicit_services"
aliases: ["illicit_services output", "illicit_services signal registry"]
tags: [zima, research, outputs, signal-registry, breach, illicit_services, graph_exclude]
type: provider_research_output
provider: illicit_services
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: illicit_services.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
# Illicit Services / search.0t.rocks – Zima stealer_log_exposure integration

## Overview

Illicit Services (search.illicit.services, later search.0t.rocks) was an OSINT data breach search engine built on Apache Solr that indexed large aggregated breach datasets, including the Naz.API credential corpus composed of credential stuffing lists and stealer logs. The original hosted service has been shut down, but the author has released the full code for the search engine (search.0t.rocks) and sample document schema, which effectively serve as the only "official" technical reference for its API and data model. Zima should treat this provider as a signal-producing breach/credential source whose JSON search endpoint feeds direct signals for credential exposure, while the rest of the fields act as enrichment.[1][2][3][4]

***

## A. API Surface Appendix

Because there is no formal developer documentation, this appendix is derived from:

- The open-source search.0t.rocks server implementation (Express + Solr).[4]
- The Solr document schema example in `sample.jsonl`.[4]
- The Illicit-Services-Enum-Script Python client for `https://search.illicit.services/records?wt=json&…`.[5][6]
- OSINT write-ups describing Illicit Services’ capabilities.[7][8][9]

Where behavior is taken from code rather than written docs, it is labeled as *derived from code*.

### 1. `GET /records` – main search endpoint

**Endpoint**
`GET /records`

On the public instance this was exposed at `https://search.illicit.services/records` (and later via the search.0t.rocks host); in the open-source version it is served by the Express app in `dataapp/index.ts` listening on port 3000.[10][4]

**Purpose**
Search the aggregated breach index for records matching a set of personal identifiers (email, username, phone, address, IP/ASN, domain, vehicle identifiers, etc.) and return structured JSON or HTML describing matching documents.[8][7][4]

**Supported entity types (by query parameter)**
All query keys are taken from `buildQuery` in `dataapp/index.ts` and from the Illicit-Services-Enum-Script argument map.[6][5]

- `emails` – one email address string; supports exact and fuzzy matching, with special handling to also query by domain.[5][4]
- `usernames` – username string.[4]
- `phoneNumbers` – phone number string; code normalizes digits and can perform exact or fuzzy matches.[4]
- `firstName`, `lastName` – personal name filters.[4]
- `address`, `city`, `state`, `zipCode` – location/physical address filters.[4]
- `ips` – IP address string, encoded with sentinels in the indexed field.[4]
- `asn`, `asnOrg` – ASN number and organization.[4]
- `domain` – domain field (can be treated as exact or fuzzy).[4]
- `country` – country string.[4]
- `VRN` – vehicle registration number / license plate.[5][4]
- `vin` – vehicle identification number.[5][4]
- `passwords` – search by password value or list of password values.[4]
- Various `not…` prefixed counterparts (e.g., `notemails`, `notusernames`) for negation filters.[4]

**Authentication / access control**
Auth is enforced only when JSON output is requested:

- If `wt=json` is **absent**, `/records` returns an HTML page and does **not** enforce API-key checks, although anti-automation heuristics still run.[4]
- If `wt=json` is **present**, the handler treats the request as API use and requires an API key or allowed user agent:
  - It reads `apikey` query param or the `User-Agent` header into `apiKey`.[4]
  - It checks whether `apiKey` is present in the `whitelistedUserAgents` array (which acts as the server-side allowlist of API keys/identifiers).[4]
  - If not allowed, it returns HTTP 403 with JSON: `{ error: true, message: 'API Access requires a free API token. Please contact …' }`.[4]

In addition, there is a separate automation-detection path:

- `isAutomated(req)` checks the connecting IP against a local blacklist and inspects the `User-Agent` to decide whether the caller looks like a bot.[4]
- If classified as automated, the server responds with a synthetic JSON payload via `doAutomatedRes` that contains a single fake record, including a warning message instructing users to obtain an API token instead of scraping.[4]
- A special hard-coded user agent string (`yeayeyayaeyayeayeyaeyeayyaeyeyaeyae`) bypasses this bot check, presumably for internal tooling.[4]

**Key query parameters (non-entity options)**

- `wt=json` – when present, returns JSON: `{ resultCount, count, records }`; otherwise returns rendered HTML.[4]
- `exact` – when truthy, switches some fields (e.g., `emails`, `domain`, `usernames`, `phoneNumbers`) into exact-match mode, disabling additional fuzzy/domain-only queries.[4]
- `sofreshandsoclean` – undocumented flag used in code to bump `rows` to 10000 for some additional queries; this effectively controls page size for the secondary query.[4]

**Top-level JSON response structure (when `wt=json`) – *derived from code***
Per the `/records` handler:[4]

```json
{
  "resultCount": <int>,   // total estimated matching docs from Solr
  "count": <int>,         // number of records actually returned in this response
  "records": [
    {
      "id": "uuid",
      "emails": ["user@example.com", "alt@example.org"],
      "passwords": ["hashOrPlaintext", "…"],
      "usernames": ["user1"],
      "firstName": "…",
      "lastName": "…",
      "address": "…",
      "city": "…",
      "state": "…",
      "zipCode": "…",
      "phoneNumbers": ["15551234567"],
      "vin": "…",
      "VRN": ["plate"],
      "latLong": "38.8121904,-90.7966084",
      "links": ["domain.com", "198.51.100.10"],
      "notes": ["companyName: …", "jobLastUpdated: 2020-01-01"],
      "dob": ["YYYY-MM-DD"],
      "gender": ["m"],
      "source": "Linkedin" | "…",
      // many other optional attributes (autoMake, autoModel, ethnicity, income, etc.)
      "canMap": true,
      "fields": ["key: value", "key2: value2", "…"]
    }
  ]
}
```

- The base document structure comes from the Solr index example (`sample.jsonl`), which shows documents with fields like `id`, `emails`, `passwords`, `usernames`, `firstName`, `lastName`, `address`, `city`, `state`, `zipCode`, `phoneNumbers`, `autoMake`, `vin`, `dob`, `gender`, `notes`, `links`, `latLong`, and many others.[4]
- The `/records` handler wraps each Solr document, adding:
  - `canMap` – boolean, true if record has either `address` or `latLong`.[4]
  - `fields` – array of `"key: value"` strings for all document keys except `id` and `_version_`.[4]

**Field presence (always/optional) – *derived from sample & code***

- Always present in a valid record:
  - `id` – UUID or similar unique identifier; appears in all documents and is used as the primary key for drill-down via `/documents/by_id`.[4]
- Common but not guaranteed:
  - `emails` – often present for email-centric records; some sample docs show only `id` + `emails`, others have extensive metadata.[4]
  - `passwords` – present for many records, mixing plaintext passwords, unsalted hashes, and modern password hashes (e.g., bcrypt `$2y$…`).[4]
  - `usernames`, `phoneNumbers`, `firstName`, `lastName`, `address`, `city`, `state`, `zipCode` – widely present but not universal.[4]
- Optional / conditional:
  - `latLong`, `autoMake`, `autoModel`, `autoYear`, `VIN`, `VRN`, `dob`, `gender`, `income`, `ethnicity`, `photos`, `links`, `notes`, `source`, and others are present only where available in the underlying dataset.[4]

**Result variants – *derived from code***

- **Successful hit**: HTTP 200, `resultCount > 0`, `records` non-empty.
- **Successful no-hit**: HTTP 200, `resultCount == 0`, `records` empty; `count` will be 0.[4]
- **Partial / limited**: Solr is queried for up to `rows` (default 100; optionally 10000 when `sofreshandsoclean` is present) for each of the primary and additional queries; `resultCount` may be larger than `count` when there are more matches than returned records.[4]
- **Anti-automation response**: If `isAutomated` or `checkIPAutomatedSTDDEV` (in other routes) classifies the client as a bot, `doAutomatedRes` returns HTTP 200 JSON with `resultCount: 69420`, `count: 69420`, and a single fake record whose fields contain a warning about automated scraping and attribution to search.illicit.services.[4]

**Error cases – *derived from code***

- 400 `no query!!!` when `buildQuery` produces an empty or invalid query (e.g., only negative filters).[4]
- 400 in some malformed-query conditions inside `buildQuery` (e.g., only NOT clauses with no positive query); the handler returns `"no query!!!"`.[4]
- 403 JSON error when `wt=json` is present and the `apikey` / `User-Agent` is not in `whitelistedUserAgents`.[4]
- 500 on unexpected exceptions in the handler catch block (body only calls `res.status(500)` without JSON payload).[4]

**Example document (from `sample.jsonl`, abbreviated)** – *example only; not a live response*

```json
{
  "id": "af29f889-542c-4f2f-bcc1-6959bd336c66",
  "emails": ["athirawarrier95@gmail.com"],
  "passwords": ["fNJVuE"]
}
```

This shows a record with a Gmail address and a short apparent plaintext password value `"fNJVuE"`.
[4]


### 2. `GET /documents/by_id/:id` – single-record drill-down

**Endpoint**
`GET /documents/by_id/{id}` with optional query parameters.

**Purpose**
Retrieve a single record by its unique `id`, optionally including a list of similar/related records, either rendered as HTML or returned as JSON.[4]

**Supported entity type**

- Primary: `id` (string) used as the natural document identifier.

**Auth / automation behavior**

- Uses `isAutomated(req)` and `checkIPAutomatedSTDDEV(req)` to detect bots; if either returns true, responds via `doAutomatedRes` as described above (synthetic warning record, possible HTML or JSON depending on `wt`).[4]
- Does **not** enforce the `whitelistedUserAgents` API-key check; JSON is available without the `apikey` gate, but bot-heuristics remain.[4]

**Response variants – *derived from code***

- If no record is found for the given `id`, returns HTTP 404 with text `"No record found."`.[4]
- If `wt=json` is present and `moreLikeThis` is not `true`:

```json
{
  "record": { /* SolrRecord fields, same as in /records */ }
}
```

- If `wt=json` is present and `moreLikeThis=true`, it calls `getSimilarRecords(record)` and returns:

```json
{
  "record": { /* SolrRecord */ },
  "related": [ { /* SolrRecord */ }, … ]
}
```

  where `related` is a list of similar documents identified by combinations of shared email and username values plus Solr MoreLikeThis on `emails`.[4]

- If `wt=json` is absent, it renders an HTML page from `recordById.mustache` showing key–value pairs and related records as a listing.[4]

**Top-level response fields and types (JSON)**

- `record` – object; document with same fields as returned by `/records` (minus UI-only wrappers like `fields` if omitted in view templates; the JSON version uses raw Solr docs).[4]
- `related` – array of objects; only present when `moreLikeThis=true`, each object shaped like a Solr document with its own `id` and fields.[4]


### 3. `GET /spatial` – geospatial search

**Endpoint**
`GET /spatial?latLong=at,lon>&d=<distanceKm>`

**Purpose**
Perform a geospatial search for records with `latLong` within a given distance `d` in kilometers, using a Solr geofilt query.[4]

**Supported entity type**

- Coordinates: `latLong` string in the form `"at>,on>"`.

**Auth / automation behavior**

- No API-key enforcement; returns JSON regardless of `wt` (there is no `wt` handling here).[4]
- Performs validation only on `latLong` format and `d` bounds.

**Request validation (from code)**

- `latLong` must match regex `^-?\d{1,3}(?:\.\d{1,20})?,-?\d{1,3}(?:\.\d{1,20})?$`; otherwise returns `{"error": true, "errorMessage": "Please only send coordinates as lat,long"}`.[4]
- `d` must be a string parseable as a float, between 0.1 and 1000; otherwise returns `{"error": true, "errorMessage": "Please provide a valid d between 0.1 and 1000"}`.[4]

**Response structure**
Calls `queryForDocsSpatial` which returns:

```json
{
  "numDocs": <int>,
  "records": [ { /* SolrRecord */ }, … ]
}
```

where `records` includes the same fields as in `/records`, without the `canMap`/`fields` augmentations used by the HTML path.[4]

**Relevance to Zima**
This endpoint is not needed for the stealer_log_exposure module, but it demonstrates that `latLong` is part of the schema and that some records can be location-mapped.


### 4. Wallet / exports internals (utility-only)

The server also contains helper functions for a separate Solr core named `Wallets` (for per-wallet credit balances) and an `Exports` core.[4]

- `getWalletBalance(wallet)`, `addWalletBalance(wallet, credits)`, `removeWalletBalance(wallet, credits)` call Solr endpoints at `…/solr/Wallets/select` and `…/update` to fetch and update a document `{ id: wallet, credits: number }`.[4]
- `queryForExportDocs(query, …)` queries `…/solr/Exports/select` similarly to `queryForDocs`.[4]

Express route definitions using these helpers are present but are only involved in billing/donation/export flows, not in breach search itself; they can be treated as **utility-only** and out of scope for signal generation.[4]


### 5. Illicit-Services-Enum-Script behavior (client-side)

The Illicit-Services-Enum-Script Python client demonstrates how the public API was expected to behave and shows the JSON response shape the author relied on.[6][5]

- It constructs `base_url = 'https://search.illicit.services/records?wt=json&'` and appends up to 5 query parameters (hard-coded cap), mapped as:

  - `first-name` → `firstName`
  - `last-name` → `lastName`
  - `email` → `emails`
  - `username` → `usernames`
  - `phone` → `phoneNumbers`
  - `address` → `address`
  - `license-plate` → `VRN`
  - `vin` → `vin`
  - `city` → `city`
  - `state` → `state`
  - `zip` → `zipCode`.[5]

- It expects `response.json()` to contain a top-level `records` array, iterating `for record in data['records']` and reading `record['emails'][0]` for each hit.[5]
- It then optionally uses those discovered emails to run additional `/records?wt=json&emails=…` queries, deduplicating addresses and printing all unique emails.[5]

This script confirms both the endpoint URL and that the JSON API consistently returns `records` with at least an `emails` array when an email match exists.


***

## B. Module Mapping Appendix

### Module mapping table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---------------|-----------------|----------------------|----------------|-------------|-------------|--------------|-------|
| stealer_log_exposure | signal_producer | search_breaches | `GET /records?wt=json&emails={email}` | direct_signal_input | email | Only treat records where `emails` contains the normalized target email and `passwords` is a non-empty array as signal candidates; ignore records without `passwords` for this module. Also require that the response is not the anti-scraping dummy (resultCount 69420, warning text). | search.0t.rocks server code; Illicit-Services-Enum-Script; OSINT descriptions of Illicit Services’ data (passwords, emails, PII). | `/records` is the primary interface for Naz.API and other breach data; JSON output requires API key/whitelisted UA when hitting a hosted instance, but this constraint disappears when self-hosting the open-source code.[5][2][4][9] |
| stealer_log_exposure | signal_producer | fetch_record_by_id | `GET /documents/by_id/{id}?wt=json` | enrichment_only | email | Only call when a prior `/records` search has already produced a matching record `id` and a signal is being created; use it to pull the full record (including any fields omitted from the first page) but do not independently create signals from `/documents/by_id` responses. | search.0t.rocks server code. | `/documents/by_id` gives full-record drill-down and optional `related` records; valuable for remediation context (full PII, additional usernames, phone numbers) but not necessary to determine whether a credential for the email is exposed.[4] |
| stealer_log_exposure | signal_producer | search_spatial | `GET /spatial?latLong=…&d=…` | out_of_scope | coordinates | Not used; module is keyed to email-centric credential exposure, not geospatial clustering. | search.0t.rocks server code. | `/spatial` could be useful for later privacy/PII modules (e.g., clustering exposed home addresses), but it does not on its own identify credential exposure for a specific email.[4] |


***

## C. Signal Contract Table

Only one standalone signal is recommended for this provider in the `stealer_log_exposure` module; all other fields should be treated as enrichment.

### Signal contract table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|-----------------|------------|----------|----------|------------------------|------------------|------------|--------------|-------------------|-----------------|-------------------|------------------|----------------|--------------|-------|
| stealer_log_exposure | stealer_log_exposure | illicit_services | search_breaches | credential_breach_found | identity_security | high | yes | Treat as **critical** when at least one `passwords` value appears to be plaintext (short, non-hex, non-hash-like); otherwise **high** for hash-only or ambiguous password formats. | email | true_finding | A `/records?wt=json&emails={email}` call returns a JSON body where `records` contains at least one object such that: (1) `emails` includes the normalized entity email (case-insensitive), and (2) `passwords` exists and is a non-empty array. Exclude responses where `resultCount == 69420` and the record contains the anti-automation warning text. | `id`, `emails`, `passwords`, `usernames` (if present), plus any `source` or `notes` fields that describe the underlying leak. | `firstName`, `lastName`, `address`, `city`, `state`, `zipCode`, `latLong`, `phoneNumbers`, `links`, `dob`, `gender`, `autoMake`/`autoModel`/`autoYear`, `VRN`, `vin`, `notes` entries not directly needed to prove credential exposure. | `Credentials associated with {{entity}} were found in an external breach dataset, including at least one exposed password.` | derived | search.0t.rocks index implementation; sample.jsonl showing `emails` + `passwords` fields; Illicit-Services-Enum-Script; Naz.API and Illicit Services breach descriptions. | Some hosted instances reportedly removed password visibility later ("no passwords anymore"), so password presence will depend on the data you import; the open-source engine and sample schema still include `passwords` arrays. Naz.API itself is a mix of stealer logs and credential stuffing lists, so exposed credentials may be old but still valid if reused.[5][11][2][3][4] |

**Evidence vs enrichment rationale**

- **Evidence fields**: `emails` and `passwords` jointly prove that at least one credential for the entity email was available in the aggregated dataset, which is enough to justify a "credential breach found" signal.[2][3][4]
- `usernames` are often the login identifier for specific services and strengthen attribution that the credential relates to the target; they should be preserved in evidence when present.[8][4]
- `source` and structured `notes` entries (e.g., containing `companyName`, `companyWebsite`, `jobLastUpdated`) help explain the origin of the data and can be valuable for remediation decisions and deduplication.[4]
- **Enrichment fields** such as postal address, phone numbers, vehicle data, and demographics materially increase privacy risk but are not necessary to show that a credential was leaked; they should be persisted for later PII/identity modules rather than creating separate signals here.[7][8]


***

## D. Severity Rules

### Base severity mapping

Using Zima’s calibration guide and the observed data characteristics:

- Presence of any `passwords` value tied to the entity email constitutes a **credential leak**, not just a reputational indicator.[3][2][4]
- Naz.API and related sources are composed of both credential stuffing lists and stealer logs, but in both cases the attacker has at least one historical password for the account; even old credentials may still be reused.[2][3]

Therefore, for the `credential_breach_found` signal:

- **Critical**:
  - `passwords` contains at least one value that appears to be plaintext or trivially reversible (short, non-hex, does not match common hash prefixes like `$2a$`, `$2b$`, `$2y$`, `$argon2`, etc.).
  - Rationale: plaintext credentials are immediately usable for account takeover, and Naz.API explicitly aggregates stealer logs where browser-saved passwords are captured directly.[12][3][2]
- **High** (default):
  - `passwords` is present but all values look like hashes (hex strings of consistent length, bcrypt/argon2 identifiers, etc.), or their format is ambiguous.
  - Rationale: hashed passwords still significantly increase credential stuffing and offline cracking risk, especially when passwords are weak or hash parameters are outdated, but are not quite as immediately exploitable as plaintext.[13][2]

This aligns with Zima’s guide: direct plaintext credential exposure → **critical**; confirmed but potentially older/hashed credentials → **high**.

### Conditional logic and caveats

- There is **no recency field** for credentials; some Naz.API credentials are explicitly described as "old" but still widely reused, so severity is not downgraded solely due to age.[14][3][2]
- If Zima can later correlate that the leaked password **does not match** the current credential (e.g., via safe comparison against a password-history hash), severity could be reduced from critical/high to medium; this correlation is outside the provider and should live in Zima’s correlation layer.
- If a record contains only email and extensive PII but **no `passwords` field**, no `credential_breach_found` signal should be emitted for this module; that scenario belongs to a distinct `pii_exposure` or privacy module.

The user’s first-pass assessment for this provider was unspecified; based on available evidence, treating password-bearing hits as high/critical is justified, provided Zima later calibrates using internal telemetry.


***

## E. Confidence Guidance

### Provider and data reliability

- Illicit Services/search.0t.rocks is fueled primarily by aggregated breach data, with Naz.API cited as a major source; Naz.API itself is a composite dataset built from stealer logs and credential stuffing lists, not a single canonical breach.[15][16][17][3][2]
- The service explicitly claimed to index only data that was already "publicly available" (rebroadcast breaches), which improves transparency but also means there is no privileged collector pipeline to validate or enrich records beyond what is in the source dumps.[1][8]
- Sample documents and OSINT reporting show realistic combinations of emails, plaintext and hashed passwords, PII, and even mortgage/vehicle data, indicating that the collection is broad and heterogeneous rather than curated to a strict standard.[9][7][8][4]
- Some later public instances of Illicit Services reportedly **removed password visibility** from the UI/API, so current behavior depends entirely on the data and configuration used when self-hosting the released engine.[11]

Overall, the **existence** of a record with `emails` + `passwords` is highly reliable as evidence that the email/password pair appeared in at least one historical breach or stealer log, but the **freshness and current validity** of that password cannot be inferred from this provider alone.

### Freshness / staleness considerations

- Naz.API and other constituent lists include breaches from many years, and OSINT analyses emphasize that many passwords in Naz.API are old, albeit still widely reused.[14][3][2]
- The public Illicit Services instance has been shut down (search.0t.rocks now just displays a shutdown message), so any Zima integration will likely be against a **static self-hosted snapshot**, with updates only when operations imports new dumps.[18][19][20][4]
- Individual records sometimes contain `notes` fields with timestamps like `jobLastUpdated: 2020-01-01` or `locationLastUpdated: 2020-10-01`, but there is no equivalent metadata for `passwords`; these timestamps cannot be used to infer credential freshness.[4]

### Corroboration opportunities

For production confidence scoring, Zima should treat Illicit Services as **one of several breach sources** and corroborate findings where possible:

- Cross-check the email against other breach-notification services (e.g., Have I Been Pwned) to see whether the same address appears in other datasets and whether any breach names match clues in `notes` or `source` fields.[16][21][2]
- If Zima has access to internal authentication logs, correlate `credential_breach_found` signals with:
  - Recent successful logins from unusual IPs/ASNs for the account.
  - Credential stuffing patterns (many failed logins across multiple accounts from a single IP or automation tool).
- When safe and compliant, compare the leaked password (or its hash) against the current password hash or known-password-history for the account to determine whether the credential is still in use.
- Combine with other stealer-log-specific providers that label malware families, infection times, and cookie/session theft to increase confidence that the exposure originated from active infostealer malware rather than from an old static breach list.[22][13][12]

### Calibration TODOs

- **Empirical validation**: For a subset of internal accounts with `credential_breach_found` from Illicit Services, measure:
  - Fraction where the leaked password matches the current credential.
  - Fraction where matching credentials later appear in internal incident investigations.
- **Hash vs plaintext impact**: Track separately the incident rate for hits with plaintext passwords vs. hash-only passwords to validate the critical vs. high severity split.
- **Staleness modeling**: Where possible, infer approximate leak windows from cross-referenced breach names or hashed-password reuse across time, then test whether older leaks correlate with lower incident probability.
- **Vendor-schema drift**: As operators self-host and adjust the index (e.g., removing `passwords` for legal reasons), periodically verify that new deployments still include the fields Zima relies on; if not, downgrade this provider to enrichment-only for those deployments.


### Confidence guidance table

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|-------------------------|---------------------|--------------------------|---------------------|------------------|
| stealer_log_exposure | credential_breach_found via `/records` (`emails` + `passwords`) | High that the email/password pair appeared in at least one historical breach or stealer log; moderate on whether it still matches the live credential; collection is broad but not curated, and behavior depends on the self-hosted snapshot. | Treat as potentially stale: Naz.API and other lists mix old and new breaches, and the engine is usually run on static snapshots; no explicit per-password timestamps are available. | Cross-check email in other breach sources; correlate with login telemetry and incident investigations; when safe, compare leaked password (or its hash) against current password hash to determine whether it is still valid. | Measure match rates between leaked and current credentials; track incident correlation for plaintext vs hash-only hits; add age-aware scoring where cross-provider timestamps are available; routinely validate that self-hosted schema still exposes `passwords` and `emails`. |


***

## F. Provider Summary and Implementation Notes

### Strongest signal types

- The most valuable output for Zima is any record where `emails` contains the target email and `passwords` is non-empty, indicating that at least one historical password for that account is known to attackers.
[3][2][5][4]
- When `passwords` includes clear plaintext values (as seen in `sample.jsonl`), the risk is especially acute because these can be re-used immediately for credential stuffing and VPN/SaaS login attempts without cracking.[12][2][4]
- The presence of linked `usernames`, `links` (domains/IPs), and `notes` (company name, job metadata) provides rich context for targeting and remediation (e.g., which SaaS or corporate accounts are most at risk), even though they are not themselves separate signals in the stealer_log_exposure module.[8][4]

### What the provider should **not** be used for

- **Not a real-time detector**: There is no streaming or incremental update mechanism; datasets are imported in bulk via Solr, making this unsuitable for real-time detection of newly compromised credentials.
[4]
- **Not infrastructure threat intel**: While some records contain `links` or `ips`, these are incidental and not structured as a malicious-infrastructure feed; other providers should handle malware C2, phishing domains, and botnet infrastructure.
[22][12][8]
- **Not authoritative identity resolution**: Names, addresses, and demographic fields are derived from often noisy breach/marketing data and should not be treated as ground truth for KYC or HR systems.
[7][8]
- **Not legal/compliance evidence of breach origin**: Naz.API and similar lists amalgamate many sources; they are excellent for risk detection but poor for attributing a specific vendor or application as the root cause of compromise.[17][2][3]

### API / auth / rate-limit / licensing cautions

- The original hosted Illicit Services instance implemented strong anti-scraping controls: IP-based behavioral heuristics, dummy responses for suspected bots, and an API-key requirement for JSON access; any attempt to query the original service at scale would have to coordinate with the operator, but that service is no longer available.[23][20][1][7][4]
- The open-source search.0t.rocks engine is licensed under Apache-2.0, but the **data** you import (Naz.API and other breaches) will have its own legal and ethical constraints; Zima should obtain and process such data only under appropriate legal advice and policies.[24][4]
- Since search.0t.rocks is built on Apache Solr, indexing billions of documents requires careful Solr capacity planning (sharding, replication, JVM tuning), and misconfiguration can lead to data loss or performance collapse; this risk belongs to the data engineering layer, not the detection logic.[4]

### Implementation notes for Zima

**Client vs mapper vs correlation responsibilities**

- **Provider client**:
  - Implement a thin HTTP client for `/records` and `/documents/by_id`, including:
    - Construction of `GET /records?wt=json&emails={normalized_email}`.
    - Handling of API-key / `User-Agent` authentication where configured.
    - Robust detection of anti-automation dummy responses (resultCount 69420, warning text) and 403/400 errors, mapping them to provider-errors rather than no-hits.[4]
  - Optionally, support additional filters (e.g., `domain`) when Zima needs to scope searches to particular organizations, but keep the default path simple: email-only.

- **Module mapper (`modules/stealer_log_exposure/mapper.py`)**:
  - Normalize email to lowercase for matching and deduplication.
  - For each record where `emails` contains the entity email:
    - If `passwords` is empty or missing, do **not** emit a signal for this module; just attach the record as enrichment for other modules.
    - Otherwise, extract evidence fields (`id`, `emails`, `passwords`, `usernames`, any `source`/`notes` about the dataset) into the normalized `evidence` object.
    - Attach additional enrichment fields (PII, phone numbers, address, vehicle data, etc.) without promoting them into their own signals.
  - Populate `signal_type = "credential_breach_found"`, `category = "identity_security"`, `entity_type = "email"`, and tags (e.g., `["breach", "stealer_log", "plaintext_password"]` when applicable).

- **Rules layer (`modules/stealer_log_exposure/rules.py`)**:
  - Implement severity selection logic described in Section D, ideally via helper predicates:
    - `has_plaintext_password(record.passwords)` → critical.
    - `passwords_present_but_hashed_only(record.passwords)` → high.
  - Optionally, integrate cross-provider evidence (e.g., other breach sources, internal auth logs) before final severity assignment.

- **Correlation layer**:
  - Deduplicate signals by `(provider="illicit_services", entity_email, normalized_password_value)` when plaintext is visible, or by `(provider, entity_email, hash)` when only hashes are available.
  - Use `id` as an additional deduplication key to avoid repeated alerts when the same record appears across multiple queries.
  - Correlate with internal telemetry to detect active abuse of leaked credentials.

**Field paths to preserve**

- Preserve the full raw record object (minus high-volume UI-only `fields` array) in the `evidence` blob for audit and future schema evolution; `fields` is a redundant stringification of other keys and can be dropped to save space.[4]
- Keys that are especially important to keep:
  - `id`, `emails`, `passwords`, `usernames`, `links`, `notes`, `source`, `dob`, `gender`, `phoneNumbers`, `address`, `city`, `state`, `zipCode`, `latLong`, `VRN`, `vin`, and any `companyName`/`companyWebsite`-like information embedded in `notes`.[4]

**Null / empty / no-hit behavior**

- If `/records` returns HTTP 200 with `records` empty, treat as a **clean no-hit** for this provider and entity.
- If `/records` returns the anti-scraping dummy payload or HTTP 4xx/5xx, classify as **provider error**, not as signal absence; consider limited retry with backoff, but avoid aggressive retries that might trigger further blocking.[4]
- If `records` are present but none contain `passwords`, treat the call as enrichment-only for other modules and do not raise a `credential_breach_found` signal here.

**Rate limits and operational constraints**

- The public service used behavioral heuristics (standard deviation of inter-request timings, total requests per IP) to identify bots; more than ~200 lookups from a single IP and highly regular request timings could trigger blacklisting.[4]
- When self-hosting, these heuristics can be adjusted or removed, but Zima’s client should still implement basic rate limiting and jitter to avoid overloading the Solr backend.

**Deduplication keys / natural identifiers**

- `id` serves as the natural document identifier across endpoints and can be used to deduplicate provider-level results.
- For Zima-level deduplication, `(entity_email, provider="illicit_services", record.id)` is a safe minimum key; optionally augment with inferred `breach_source` if `notes` or `source` indicate a specific dataset.

**Raw evidence retention**

- Store the full record (minus `fields`) and the `/records` response metadata (`resultCount`, `count`, query parameters) in an evidence store to support forensics and to re-run correlation logic as schemas evolve.
- Because data sources include highly sensitive PII and credentials, ensure Zima’s storage, access control, and retention policies for this raw evidence comply with internal and external privacy requirements.

### Overall provider role in Zima

Given the available information and the open-source implementation, the illicit_services / search.0t.rocks stack should be treated as a **signal-producing breach data provider** for the stealer_log_exposure module, specifically for `credential_breach_found` signals when `emails` and `passwords` coexist in a record. All other fields coming from this provider are best handled as enrichment for identity/PII modules and should not spawn standalone signals in the current integration stage.

Here’s the detailed report as a markdown artifact, including the API Surface Appendix, module mapping table, signal contract table, confidence guidance, provider summary, and implementation notes.[[osint-news](https://osint-news.com/2023/07/osint-tool-illicit-services-shuts-down-due-to-unethical-use-concerns/)]​

Programmatic JSON summary (same content model as in the report):

json

``{   "provider": "illicit_services",  "provider_category": "breach",  "provider_role": "signal_producer",  "module_mappings": [    {      "module": "stealer_log_exposure",      "provider_role": "signal_producer",      "provider_method": "search_breaches",      "endpoint_or_artifact": "GET /records?wt=json&emails={email}",      "classification": "direct_signal_input",      "entity_types": ["email"],      "gating_logic": "Only treat records where `emails` contains the normalized target email and `passwords` is a non-empty array as signal candidates; ignore records without `passwords` for this module. Also require that the response is not the anti-scraping dummy (resultCount 69420, warning text).",      "citation_refs": [        "https://github.com/WKL-Sec/Illicit-Services-Enum-Script",        "https://github.com/MiyakoYakota/search.0t.rocks",        "https://www.bleepingcomputer.com/news/security/have-i-been-pwned-adds-71-million-emails-from-nazapi-stolen-account-list/"      ],      "notes": "Primary source of credential exposure; JSON access for hosted instances requires API key / whitelisted UA, but this constraint goes away when you self-host the open-source engine."    },    {      "module": "stealer_log_exposure",      "provider_role": "signal_producer",      "provider_method": "fetch_record_by_id",      "endpoint_or_artifact": "GET /documents/by_id/{id}?wt=json",      "classification": "enrichment_only",      "entity_types": ["email"],      "gating_logic": "Only call when a prior `/records` search has produced a matching record `id` and a signal is being created; do not independently create signals from `/documents/by_id` responses.",      "citation_refs": [        "https://github.com/MiyakoYakota/search.0t.rocks"      ],      "notes": "Used to pull full record (including related docs) for remediation context."    },    {      "module": "stealer_log_exposure",      "provider_role": "signal_producer",      "provider_method": "search_spatial",      "endpoint_or_artifact": "GET /spatial?latLong=…&d=…",      "classification": "out_of_scope",      "entity_types": ["coordinates"],      "gating_logic": "Not used in this module; stealer_log_exposure is email-centric.",      "citation_refs": [        "https://github.com/MiyakoYakota/search.0t.rocks"      ],      "notes": "Potentially useful later for PII/physical-address clustering modules."    }  ],  "signal_contracts": [    {      "module": "stealer_log_exposure",      "source": "stealer_log_exposure",      "provider": "illicit_services",      "provider_method": "search_breaches",      "signal_type": "credential_breach_found",      "category": "identity_security",      "severity": "high",      "severity_is_conditional": "yes",      "conditional_rule": "Treat as critical when at least one `passwords` value appears to be plaintext (short, non-hex, non-hash-like); otherwise high for hash-only or ambiguous password formats.",      "entity_type": "email",      "finding_kind": "true_finding",      "trigger_condition": "A `/records?wt=json&emails={email}` call returns JSON with `records` containing at least one object where (1) `emails` includes the normalized entity email (case-insensitive) and (2) `passwords` exists and is a non-empty array. Exclude responses where `resultCount == 69420` and the record contains the anti-automation warning text.",      "evidence_fields": [        "id",        "emails",        "passwords",        "usernames",        "source",        "notes"      ],      "enrichment_fields": [        "firstName",        "lastName",        "address",        "city",        "state",        "zipCode",        "latLong",        "phoneNumbers",        "links",        "dob",        "gender",        "autoMake",        "autoModel",        "autoYear",        "VRN",        "vin",        "notes (non-breach metadata)"      ],      "summary_template": "Credentials associated with {{entity}} were found in an external breach dataset, including at least one exposed password.",      "evidence_status": "derived",      "citation_refs": [        "https://github.com/MiyakoYakota/search.0t.rocks",        "https://github.com/WKL-Sec/Illicit-Services-Enum-Script",        "https://www.bleepingcomputer.com/news/security/have-i-been-pwned-adds-71-million-emails-from-nazapi-stolen-account-list/",        "https://ionix.io/blog/naz-api-and-how-to-prevent-credential-stuffing/"      ],      "notes": "Passwords may be plaintext or hashed depending on the imported data. Hosted instances have at times removed password visibility; the open-source engine and example schema still expose `passwords`. Naz.API mixes stealer logs and credential-stuffing lists, so credentials may be old but still risky if reused."    }  ],  "confidence_guidance": [    {      "module": "stealer_log_exposure",      "signal_type_or_use_case": "credential_breach_found via /records (emails + passwords)",      "source_reliability": "High that the email/password pair appeared in at least one historical breach or stealer log; moderate that it still matches the live credential. Data is broad, aggregated and may be noisy.",      "freshness_considerations": "Datasets (e.g., Naz.API) are composite and can be years old; self-hosted search.0t.rocks instances are typically static snapshots without per-password timestamps.",      "corroboration_rules": "Cross-check email against other breach sources; correlate with internal login telemetry; when safe and compliant, compare leaked password or its hash against current password hashes; combine with more labeled stealer-log providers.",      "calibration_todo": "Measure match rates between leaked and current credentials; track incident correlation for plaintext vs hash-only hits; model staleness where cross-provider timestamps exist; periodically verify that the deployed schema still exposes `emails` and `passwords` fields."    }  ] }``
