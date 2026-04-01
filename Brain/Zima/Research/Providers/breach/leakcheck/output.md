---
title: "output / breach / leakcheck"
aliases: ["leakcheck output", "leakcheck signal registry"]
tags: [zima, research, outputs, signal-registry, breach, leakcheck, graph_exclude]
type: provider_research_output
provider: leakcheck
provider_category: breach
status: complete
prompt_note: prompt.md
provider_folder: leakcheck.md
obsidianUIMode: preview
---
LeakCheck should be treated as a core signal-producing breach provider for the `credential_exposure` module, with a single primary query endpoint that returns per-identity breach rows including optional passwords and PII, plus flags about dataset verification and whether passwords are present.

---

## A. API Surface Appendix

## 1. Private / Pro API v2 – Query Endpoint

**Endpoint**

- HTTP method and path: `GET https://leakcheck.io/api/v2/query/{query}` (v2 private/pro API)

- Base URL: `https://leakcheck.io/api/v2`.[github](https://github.com/LeakCheck/leakcheck-api)

- Typical client wrapper method name: `lookup(query=..., query_type=..., limit=..., offset=...)` in `LeakCheckAPI_v2`.[github](https://github.com/LeakCheck/leakcheck-api)


**Purpose**

- Look up an identifier (email, username, domain, phone, hash, etc.) in LeakCheck’s aggregated breach database and return all matching rows, including optional credentials and PII.


**Supported entity types and query types**

LeakCheck allows both auto-detected and explicit query types via the `type` (or `query_type` in SDK) parameter:

- `auto` – automatically detects email, username, phone number, or hash.

- `email` – search by email address (maps cleanly to Zima `entity_type: "email"`).[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- `domain` – domain name search, e.g. `gmail.com` (can be mapped to `domain`).[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- `keyword` – generic keyword search (less clearly mappable to a single entity type).[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- `username` – username search (maps to `username`).[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- `phone` – phone number search (maps to `phone`).[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- `hash` – SHA256 hash of lowercased email (can be truncated to 24 chars; maps to `hash`)

- `phash` – SHA256 hash of password (Enterprise only; can be truncated; maps to `hash` or `exposed_secret` depending on your schema)

- `origin` – origin of stealer logs (Enterprise only; typically domain/host context)

- `password` – password string search (Enterprise only; direct password reuse search)


For your current provider map, the prioritized / most straightforward mapping is `email` → `entity_type: "email"`, with potential later extension to `username`, `phone`, `domain`, and `hash`.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

**Auth / execution requirements**

- API key: pass in `X-API-Key` header, along with `Accept: application/json`.

- You obtain the API key from LeakCheck account settings.

- 3 requests per second per IP by default; this limit is adjustable in settings.

- Error codes indicate missing/invalid key, invalid query/format, too many requests, plan/limit issues, etc.


**Top-level response schema**

For a successful query with a hit (private/pro API v2):

json

`{   "success": true,  "found": 1,  "quota": 400,  "result": [    {      "email": "example@example.com",      "source": {        "name": "BreachedWebsite.net",        "breach_date": "2019-07",        "unverified": 0,        "passwordless": 0,        "compilation": 0      },      "first_name": "Example",      "last_name": "Example",      "username": "leakcheck",      "fields": ["first_name", "last_name", "username"]    }  ] }`

- `success` (boolean) – whether the API call itself succeeded.

- `found` (integer) – number of rows returned for this query.

- `quota` (integer) – remaining query quota for this account.

- `result` (array of objects) – array of breach result rows; may be empty.


**Per-result object fields**

Fields inside each `result` element:

- `email` (string) – the email associated with this row (even if the query was by username/domain/etc. in some cases).[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- `source` (object) – metadata about the breach/data source:

    - `name` (string) – dataset / breach name (e.g., site name, compilation label, stealer source).

    - `breach_date` (string, `"YYYY-MM"` or similar) – when the breach/dataset is dated.

    - `unverified` (integer 0/1) – whether the dataset is flagged as unverified.

    - `passwordless` (integer 0/1) – whether the dataset has no passwords (all non-credential PII).

    - `compilation` (integer 0/1) – whether the dataset is a compilation from multiple breaches.

- Optional PII / credential fields (presence varies by dataset):[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

    - `username` (string)

    - `password` (string) – raw password field from the dataset; docs do not specify whether it is plaintext or hashed.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

    - `first_name` (string)

    - `last_name` (string)

    - `dob` (string or date-like)

    - `address` (string)

    - `zip` (string)

    - `phone` (string)

    - `name` (string)

- `fields` (array of strings) – list of attribute names present for this row (e.g. `["first_name", "last_name", "username"]` in the example); implies that other keys like `password` will also appear here when present.


Presence status (documented vs inferred):

- `success`, `found`, `quota`, `result`, `email`, `source.*`, `fields` are shown in official examples and docs → **documented as present** when applicable.

- The list of possible attributes (`username`, `password`, `dob`, `address`, `zip`, `phone`, `name`, etc.) is described in prose as “includes but is not limited to” → **documented as possible but optional / dataset-dependent.**[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- The behavior that `fields` enumerates all non-core attributes (like `password`) is inferred from the sample and naming rather than explicitly spelled out → **derived from examples.**


**Response variants**

- **Successful hit** – `success: true`, `found > 0`, `result` array contains one or more objects (see above).

- **Successful no-hit** – `success: true`, `found: 0`, `result: []`, `quota` still present.

- **Partial/limited result** – not explicitly described at the JSON level; limits are enforced via `limit` and `offset` query parameters with documented maximums (`limit <= 1000`, `offset <= 2500`), so partial results are client-driven rather than labeled as such in the response.


**Common error cases**

From official docs and the Python wrapper (which repeats the same table):

- 401 – Missing `X-API-Key` header.

- 400 – Invalid `X-API-Key`.

- 400 – Invalid type.

- 400 – Invalid email.

- 400 – Invalid query.

- 400 – Invalid domain.

- 400 – Too short query (< 3 characters).

- 400 – Invalid characters in query.

- 422 – Could not determine search type automatically.

- 429 – Too many requests (rate limit exceeded).

- 403 – Active plan required.

- 403 – Limit reached.


The wrapper indicates these conditions are surfaced as errors / exceptions at client level and can be handled via `ValueError` or tuple-style errors in other clients.

**Field-level notes relevant for Zima**

- `source.passwordless` = 1 means this dataset has **no passwords**, so any hit is PII-only exposure (usernames, addresses, etc.), not direct credential fields.

- `source.unverified` = 1 should be treated as a confidence downgrade: dataset is present but not independently verified.

- `source.compilation` = 1 means the row comes from a compilation, not a single named breach; dedup and naming should treat `source.name + breach_date + email` (and possibly more) as the natural key rather than assuming each compilation row is unique.

- The presence of `password` in the row (and/or in `fields`) is the main indicator of **direct credential exposure**; however, no guarantee is given that it is plaintext, and that must **not** be assumed.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)


**Query parameters**

- `type` (`query_type` in SDK): see types above; optional if auto-detection is used, but errors if detection fails.

- `limit` – max 1000

- `offset` – max


---

## 2. Public API – Limited, Unauthenticated

**Endpoint**

- Base URL: `https://leakcheck.io/api/public`.[github](https://github.com/LeakCheck/leakcheck-api)

- Used via `LeakCheckAPI_Public.lookup(query)` in the official Python wrapper.[github](https://github.com/LeakCheck/leakcheck-api)


**Purpose**

- Allows basic email / username / hash lookups without authentication, with limited access compared to the private API.[github](https://github.com/LeakCheck/leakcheck-api)


**Schema status**

- Official wiki documentation for the public endpoint schema is **not present** in the public docs you provided; the wrapper exposes it but does not show explicit JSON examples.[github](https://github.com/LeakCheck/leakcheck-api)

- Given this, all schema-level assumptions about public responses (fields, presence of `password`, `source`, etc.) must be treated as **unknown / unclear** for implementation.[github](https://github.com/LeakCheck/leakcheck-api)


**Recommendation for Zima**

- For the current build focused on a core `credential_exposure` module with strong evidence semantics, you should **avoid using the public API** as a signal source until its response schema is clarified, and treat it as **out_of_scope** for now. (Classification rationale is derived from incomplete docs, not from vendor guarantees.)[github](https://github.com/LeakCheck/leakcheck-api)


---

## 3. Legacy v1 Client Helpers – `getIP`, `getLimits` (SDK-level)

These are exposed in the older PyPI `leakcheck` client for v1; while v2 is live, these methods illustrate utility functions you may encounter in integrations.[pypi](https://pypi.org/project/leakcheck/0.1.3/)

**Methods / artifacts**

- `LeakCheckAPI.getIP()` – returns your current public IP as a string; used for historical IP-linking requirements that are no longer needed in v2.

- `LeakCheckAPI.getLimits()` – returns a dict of API usage limits for your key (exact fields not documented on the docs site).[pypi](https://pypi.org/project/leakcheck/0.1.3/)


**Purpose**

- Operational / metering info: what IP LeakCheck sees, and what your plan limits are.[pypi](https://pypi.org/project/leakcheck/0.1.3/)


**Schema status**

- Only very high-level descriptions are available; exact JSON shapes are not documented in wiki v2 docs.


**Recommendation for Zima**

- Treat as **utility_only**: useful in provider client code for health checks, monitoring, and internal rate-limit handling, but **not to be consumed by any security module** as a signal.


---

## B. Module Mapping Table

Below, only modules relevant to your provider map are included (currently `credential_exposure`). All other potential uses (e.g. “PII exposure” as separate module) can be layered later.

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|credential_exposure|signal_producer|HTTP GET query / lookup|`GET /api/v2/query/{query}?type=...&limit&offset`|direct_signal_input|email (initial), username, domain, phone, hash (future)|Only create signals when HTTP status is 200, `success == true`, and `found > 0` with a non-empty `result` array; skip on any documented error or when `found == 0`. |[https://wiki.leakcheck.io/en/api/api-v2-pro](https://wiki.leakcheck.io/en/api/api-v2-pro) [wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro); [https://github.com/LeakCheck/leakcheck-api](https://github.com/LeakCheck/leakcheck-api) [github](https://github.com/LeakCheck/leakcheck-api); [https://hexdocs.pm/leak_check/readme.html](https://hexdocs.pm/leak_check/readme.html) [hexdocs](https://hexdocs.pm/leak_check/readme.html)|Main breach lookup for identities; Enterprise-only types (`phash`, `origin`, `password`) should be feature-flagged/licensing-gated in your client.|
|credential_exposure|signal_producer|Public lookup|`GET` to `https://leakcheck.io/api/public` (exact path/schema unclear)|out_of_scope (current stage)|email, username, hash (per wrapper)|Do not consume until response schema (fields, presence of `source`, `password`, etc.) is documented or verified; otherwise cannot reliably derive severity or evidence. [github](https://github.com/LeakCheck/leakcheck-api)|[https://github.com/LeakCheck/leakcheck-api](https://github.com/LeakCheck/leakcheck-api) [github](https://github.com/LeakCheck/leakcheck-api)|Public API is limited and undocumented at schema level; treat as non-production for Zima’s detection pipeline for now.|
|credential_exposure|signal_producer|getIP|SDK helper: `LeakCheckAPI.getIP()` (v1)|utility_only|none|Never mapped into security modules; use only in provider client for diagnostics if you ever adopt v1-style patterns. [pypi](https://pypi.org/project/leakcheck/0.1.3/)|[https://pypi.org/project/leakcheck/0.1.3/](https://pypi.org/project/leakcheck/0.1.3/) [pypi](https://pypi.org/project/leakcheck/0.1.3/)|Historical; v2 docs explicitly say “No more IP linking,” so these helpers are legacy. [wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)|
|credential_exposure|signal_producer|getLimits|SDK helper: `LeakCheckAPI.getLimits()` (v1)|utility_only|none|For internal metering and monitoring only; must not result in Zima signals. [pypi](https://pypi.org/project/leakcheck/0.1.3/)|[https://pypi.org/project/leakcheck/0.1.3/](https://pypi.org/project/leakcheck/0.1.3/) [pypi](https://pypi.org/project/leakcheck/0.1.3/)|Separate from v2 quota field; Zima can rely on response `quota` for per-query accounting instead. [wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)|

---

## C. Signal Contract Table

Given your current mapping and priority (core `credential_exposure` module; primary entity email), there is one main signal contract that should be implemented now, with conditional severity and confidence based on fields such as `password`, `source.passwordless`, `source.unverified`, and `source.breach_date`.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|credential_exposure|credential_exposure|leakcheck|`GET /api/v2/query/{query}?type=email` (or `lookup(query=..., query_type="email")`)|credential_breach_found|identity_security|high|yes|Use `high` as the default severity for any verified breach row that exposes an email, then: (1) escalate to **critical** when the row contains a `password` field (or `fields` includes `"password"`) and `source.passwordless == 0`, especially when `source.unverified == 0` and `source.breach_date` is within the implementation-defined “recent” window; (2) downgrade to **medium** when `source.unverified == 1` or the breach is very old (implementation-defined), or when `source.passwordless == 1` and only non-credential PII is present. This logic is derived from documented fields (`password`, `source.passwordless`, `source.unverified`, `source.breach_date`) and your calibration guide. |email|true_finding|For a given email query, emit one signal per unique combination of `email` and `source` when: HTTP status is 200, response `success == true`, and `found > 0` with at least one object in `result`. (You may choose to aggregate rows into a single signal per email if desired, but gating is strictly `success && found > 0`.) |Per-result: `email`, `source.name`, `source.breach_date`, `source.unverified`, `source.passwordless`, `source.compilation`, full `fields` array, and any present attributes among `username`, `password`, `first_name`, `last_name`, `dob`, `address`, `zip`, `phone`, `name`. Top level: `found`, original query value, `type`/`query_type` where available. |`quota` (for rate/quota telemetry), `limit`, `offset`, and any non-core PII you don’t want promoted into the summary (e.g. `address`, `zip`, `dob`) can be stored as enrichment for investigations without changing signal semantics. |`Credentials for {email} were found in a data breach (source: {source.name}, breach_date: {source.breach_date}).`|documented|[https://wiki.leakcheck.io/en/api/api-v2-pro](https://wiki.leakcheck.io/en/api/api-v2-pro) [wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro); [https://hexdocs.pm/leak_check/readme.html](https://hexdocs.pm/leak_check/readme.html) [hexdocs](https://hexdocs.pm/leak_check/readme.html)|Row-level dedup key should be at least `{email, source.name, source.breach_date}`, with optional inclusion of dataset-level IDs if LeakCheck later exposes them; avoid per-compilation overcounting by treating `source.compilation == 1` as a single dataset label. |

**Evidence / trigger status**

- `success`, `found`, `quota`, `result`, `email`, `source.*`, and `fields` are all **documented** in official or semi-official examples.

- The presence of `password` and other PII fields is documented as “includes but not limited to” and should be treated as **optional but documented possible evidence fields**.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- The interpretation of `password` as “direct credential exposure” and the use of `passwordless` and `unverified` flags for severity tuning is **derived from documented field semantics**, not from any provider-stated severity.


If you later support other entity types (username, phone, domain, hash), you can reuse the same `credential_breach_found` signal_type with `entity_type` adjusted and identical trigger and evidence semantics based on the same response structure.

---

## D. Severity Rules

For the `credential_breach_found` signal above:

## Baseline severity

- **Default severity: high** – any leak row where an identity is confirmed as present in a breach dataset constitutes a confirmed breach affecting that identity, which aligns with your “high” definition (“confirmed breach, exposed PII, verified malicious infrastructure, active threat actor attribution”) when at least PII or account identifiers are present.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)


## Conditional escalation to critical

Escalate to **critical** when:

- The row includes a `password` field (or `fields` includes `"password"`), indicating direct credential exposure of the password associated with the email, and

- `source.passwordless == 0` (dataset is not explicitly passwordless), and

- Optionally (recommended, but implementation-defined) `source.unverified == 0` and `source.breach_date` is within a configurable “recent” window.


This matches your critical rubric for “direct credential exposure” while acknowledging that LeakCheck does not specify whether `password` is plaintext; you can still treat it as a critical event because an exposed password field is sufficient to assume credential compromise until proven otherwise.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

## Conditional downgrade to medium

Downgrade to **medium** when:

- `source.unverified == 1` (unverified dataset), or

- `source.passwordless == 1` and the row only contains usernames / PII / metadata but no `password` field, or

- The breach is very old (e.g., `breach_date` older than a configurable threshold) and you have no corroborating evidence of recent activity.


In these cases, the signal aligns with your “medium” definition: “suspicious activity, unverified breach, reputation degradation, passive threat indicators.”

## First-pass provider severity assessment

- LeakCheck’s content is historical breach data (sometimes including passwords), with explicit flags for verification and password presence; this supports a first-pass view of **high-to-critical** severity for password-bearing hits and **medium-to-high** for PII-only or unverified hits, consistent with your calibration guide.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)


---

## E. Confidence Guidance

## Confidence factors (general)

- **Source reliability:**

    - LeakCheck aggregates a large number of breach datasets and provides explicit flags for verification (`unverified`), password presence (`passwordless`), and compilation (`compilation`), which is better-than-average transparency for this class of provider.

- **Freshness / staleness:**

    - `source.breach_date` is the main field to drive temporal confidence; older breaches should have reduced likelihood of current credential validity unless passwords are known to be reused.

- **Specificity:**

    - Email lookups are highly specific to a single identity; domain / keyword queries are broader and risk returning generic matches that are less directly actionable for a specific user account.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)


## D. Confidence Guidance Table

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|credential_exposure|credential_breach_found (email lookup)|Centralized breach provider with explicit metadata about dataset verification and password presence; reliability is relatively high for confirmed rows, but some datasets are flagged `unverified`. |Use `source.breach_date` to apply time-based decay to confidence; treat very recent breaches as higher risk and very old ones as lower, unless the same email appears in multiple recent datasets. |Where possible, cross-check LeakCheck hits for a given email against other breach providers, internal login telemetry (credential stuffing, anomalous logins), and user reports before auto-escalating to the highest confidence tier.|Empirically measure how often LeakCheck hits correspond to successful credential-stuffing or compromised-account incidents in your environment and tune confidence thresholds and severity mapping accordingly.|
|credential_exposure|credential_breach_found (password/phash/origin Enterprise use-cases)|Enterprise-only query types imply deeper access (password hashes, password strings, stealer-log origins); reliability remains good but coverage may skew toward specific dataset classes like stealer logs. |For password/phash lookups, treat any recent breach row as high confidence for active credential reuse; for origin searches, weight recency and whether origins map to known stealer campaigns. [wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)|For password-based hits, corroborate by checking whether the same password or hash appears in multiple datasets or is observed in live auth logs; for origin hits, cross reference with malware/stealer IOC feeds.|Run staged rollouts where only a subset of password/phash matches are escalated to critical, track false positives (e.g., test passwords, internal seed accounts), and adjust pattern filters and escalation rules accordingly.|

---

## F. Tags

For the `credential_breach_found` signal:

- Recommended tags:

    - `breach` – core breach context.

    - `credential_stuffing` – likely downstream attack vector.

    - `plaintext_password` – only when you empirically validate that LeakCheck’s `password` field is plaintext in your environment; otherwise omit.

    - `pii_exposure` – when PII fields (`address`, `dob`, `phone`, etc.) are present.

    - `dark_web` – if you confirm that a particular `source.name` represents dark-web/stealer-log datasets; otherwise you may hold this tag for a later provider-specific mapping.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)


Given your caution not to overfit vendor specifics, start with `["breach", "credential_stuffing", "pii_exposure"]` and add more only when corroborated.

---

## G. Implementation Notes

## Mapper / rules concerns

- **Field paths to preserve**

    - Preserve full per-row objects from `result`, at least keys: `email`, `source.name`, `source.breach_date`, `source.unverified`, `source.passwordless`, `source.compilation`, `fields`, plus any present credential/PII keys like `password`, `username`, `phone`, `address`, etc.

    - Preserve `found` and the original query string/type at the top level for audit and telemetry.

- **Null / empty / no-hit behavior**

    - When `found == 0` and `result` is an empty array, no signal should be emitted; you may optionally store a negative check in a separate telemetry stream, but not as a security signal.

    - Mapper must handle `result` being large but truncated by `limit`; implement pagination on the client side if you want full coverage, but you likely don’t need more than a handful of rows for detection purposes.

- **Rate limits, billing, licensing**

    - Respect default rate limit of 3 requests per second per IP; centralize backoff handling in the provider client (e.g., queueing in LeakCheck client, not in the module).

    - Certain query types are **Enterprise-only** (`phash`, `origin`, `password`), and attempts to use them without a suitable plan may return `403 Active plan required` or `403 Limit reached`; these should be treated as client-level errors, not module-level signals.

- **Deduplication keys / natural identifiers**

    - At minimum, use `{email, source.name, source.breach_date}` as the deduplication key for leak rows.

    - Consider adding a derived `dataset_id` equal to a hash of `{source.name, breach_date, compilation}` if you need a stable local identifier; this is an internal construct, as LeakCheck does not expose an explicit dataset ID.

- **Raw evidence for remediation / audit**

    - Store original `password` (if present) in a secure evidence store with strict access controls; it may be necessary for targeted remediation (e.g., detecting reuse, constructing user notifications), but is highly sensitive.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

    - Store name and contact fields (`first_name`, `last_name`, `phone`, `address`) when available so you can match to internal HR/identity records, but flag them as PII and avoid exposing them directly in analyst-facing summaries unless necessary.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- **Client vs mapper vs correlation layer**

    - **Provider client**: HTTP interaction, API key handling, rate limit / backoff, retry logic, pagination, and raw JSON capture; also type selection (e.g., forcing `type=email` for this module).

    - **Module mapper (`credential_exposure`)**:

        - Validate `success`, `found`, and schema validity.

        - Project each `result` row into your normalized signal format, applying dedup, severity rules, and evidence selection.

        - Determine whether to emit one signal per row or aggregated per email; for Zima, one signal per `{email, source}` is more expressive.

    - **Correlation layer**:

        - Join LeakCheck signals with internal auth logs, other breach providers, and user risk models.

        - Apply cross-provider deduplication (e.g., same dataset named slightly differently across tools).


---

## H. Provider Summary

**Strongest signal types**

- High-quality breach hits for **email** with:

    - Clear dataset name and breach date via `source.name` and `source.breach_date`

    - Explicit flags for unverified/passwordless/compilation, enabling nuanced severity and confidence tuning.

    - Optional `password` field and multiple PII attributes, which can power both credential compromise detections and PII exposure notifications.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)


**What LeakCheck should not be used for**

- Not suitable as a generic **malware/C2/threat infrastructure** source; it is breach-data centric and does not expose IP/host indicators.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- Not suitable for **WHOIS/ASN/domain reputation** enrichment; those domains are outside its scope.[wiki.leakcheck](https://wiki.leakcheck.io/en/api/api-v2-pro)

- Public API, given missing schema docs, should not be used as a production signal source until you document and test its schema yourself.[github](https://github.com/LeakCheck/leakcheck-api)


**API/auth/rate-limit/licensing cautions**

- API key must be sent in `X-API-Key`; missing or invalid keys generate 401/400.

- Default global rate limit is 3 rps per IP; exceeding it yields 429.

- Some query types (password, phash, origin) are Enterprise-only and will produce 403 errors without an appropriate plan; guard these behind feature flags.


**Overall provider role at current Zima stage**

- Treat LeakCheck as a **signal-producing breach provider** for the `credential_exposure` module, with direct signal input only from the private/pro v2 query endpoint and a single primary signal type `credential_breach_found` with conditional severity.

- Other outputs (quota, rate-limit helpers, IP, limits) are **utility-only** and should live exclusively in the provider client and observability stack, not in module detection logic.


---

## I. Structured JSON

json

`{   "provider": "leakcheck",  "provider_category": "breach",  "provider_role": "signal_producer",  "module_mappings": [    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "HTTP GET query / lookup",      "endpoint_or_artifact": "GET /api/v2/query/{query}?type=...&limit&offset",      "classification": "direct_signal_input",      "entity_types": ["email"],      "gating_logic": "Emit signals only when HTTP status is 200, response.success == true, and response.found > 0 with a non-empty result array; skip on any documented error or when found == 0.",      "citation_refs": [        "https://wiki.leakcheck.io/en/api/api-v2-pro",        "https://github.com/LeakCheck/leakcheck-api",        "https://hexdocs.pm/leak_check/readme.html"      ],      "notes": "Primary breach lookup. Enterprise-only types (phash, origin, password) must be gated by licensing/config."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "Public lookup",      "endpoint_or_artifact": "GET https://leakcheck.io/api/public (exact path/schema unclear)",      "classification": "out_of_scope",      "entity_types": ["email", "username", "hash"],      "gating_logic": "Do not consume until schema is explicitly documented or reverse-engineered and validated; currently insufficient information to derive safe trigger logic.",      "citation_refs": [        "https://github.com/LeakCheck/leakcheck-api"      ],      "notes": "Limited, unauthenticated API; shape and fields unclear from official docs."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "getIP",      "endpoint_or_artifact": "LeakCheckAPI.getIP() (v1 SDK helper)",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Never mapped into detection modules; for diagnostics only.",      "citation_refs": [        "https://pypi.org/project/leakcheck/0.1.3/"      ],      "notes": "Legacy helper; v2 no longer requires IP linking."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "getLimits",      "endpoint_or_artifact": "LeakCheckAPI.getLimits() (v1 SDK helper)",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Only for internal metering and monitoring; never produce signals.",      "citation_refs": [        "https://pypi.org/project/leakcheck/0.1.3/"      ],      "notes": "Superseded by per-query quota field in v2 responses."    }  ],  "signal_contracts": [    {      "module": "credential_exposure",      "source": "credential_exposure",      "provider": "leakcheck",      "provider_method": "GET /api/v2/query/{query}?type=email",      "signal_type": "credential_breach_found",      "category": "identity_security",      "severity": "high",      "severity_is_conditional": "yes",      "conditional_rule": "Default severity is high for any confirmed breach hit. Escalate to critical when the result row includes a password field (or fields contains 'password') and source.passwordless == 0, especially when source.unverified == 0 and source.breach_date is recent (threshold defined at implementation time). Downgrade to medium when source.unverified == 1, when source.passwordless == 1 and no password is present, or when breach_date is very old.",      "entity_type": "email",      "finding_kind": "true_finding",      "trigger_condition": "For a given email query, emit one signal per unique {email, source} combination when HTTP status is 200, response.success == true, and response.found > 0 with at least one object in response.result.",      "evidence_fields": [        "result[].email",        "result[].source.name",        "result[].source.breach_date",        "result[].source.unverified",        "result[].source.passwordless",        "result[].source.compilation",        "result[].fields",        "result[].username",        "result[].password",        "result[].first_name",        "result[].last_name",        "result[].dob",        "result[].address",        "result[].zip",        "result[].phone",        "result[].name",        "found",        "original_query",        "query_type"      ],      "enrichment_fields": [        "quota",        "limit",        "offset"      ],      "summary_template": "Credentials for {email} were found in a data breach (source: {source.name}, breach_date: {source.breach_date}).",      "evidence_status": "documented",      "citation_refs": [        "https://wiki.leakcheck.io/en/api/api-v2-pro",        "https://hexdocs.pm/leak_check/readme.html"      ],      "notes": "You may aggregate multiple result rows into a single signal per email if desired, but keep enough row-level evidence for deduplication and remediation. Use {email, source.name, source.breach_date} as a natural key."    }  ],  "confidence_guidance": [    {      "module": "credential_exposure",      "signal_type_or_use_case": "credential_breach_found (email lookup)",      "source_reliability": "LeakCheck is a centralized breach provider with explicit metadata (unverified, passwordless, compilation), making confirmed rows relatively reliable while allowing discounting of unverified datasets.",      "freshness_considerations": "Use source.breach_date to decay confidence over time; prioritize recent breaches and treat very old breaches as lower-risk unless other indicators suggest continued password reuse.",      "corroboration_rules": "Cross-check LeakCheck hits with other breach sources, internal auth logs (credential stuffing, unusual logins), and user confirmations before auto-escalating to the highest confidence tier.",      "calibration_todo": "Measure how often LeakCheck hits precede or coincide with real account compromises in your environment, then tune severity thresholds and confidence mapping based on observed precision and recall."    },    {      "module": "credential_exposure",      "signal_type_or_use_case": "credential_breach_found (password/phash/origin Enterprise use-cases)",      "source_reliability": "Enterprise-only query types (password, phash, origin) surface deeper credential and stealer-log data, which is generally high value but may be biased toward certain campaigns or data sources.",      "freshness_considerations": "Treat recent password/phash matches as strong indicators of active credential exposure; for origin searches, weigh whether origins map to current stealer campaigns and how recent they are.",      "corroboration_rules": "For password-based matches, confirm reuse via internal password telemetry or secondary breach providers; for origin hits, correlate with malware and stealer IOCs.",      "calibration_todo": "Pilot Enterprise features on a subset of accounts, evaluate false positives (test accounts, seeded credentials), and refine escalation criteria and filters before broad rollout."    }  ] }`
