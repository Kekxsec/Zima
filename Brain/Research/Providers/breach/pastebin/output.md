---
title: "output / breach / pastebin"
aliases: ["pastebin output", "pastebin signal registry"]
tags: [zima, research, outputs, signal-registry, breach, pastebin, graph_exclude]
type: provider_research_output
provider: pastebin
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: pastebin.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
# Pastebin as a Breach Intelligence Source for Zima (alias_correlation, breach_monitor)

## 1. API Surface Appendix

### 1.1 Scraping API overview (threat-intel relevant)

Pastebin exposes a dedicated **Scraping API** intended for high-volume programmatic access to recent public pastes without getting IP-blocked.[1]
This API is only available to **PRO accounts with a single whitelisted IP**, and by default only returns pastes that have syntax highlighting set; an Enterprise API tier removes some of these limitations.[2][1]

Key behavioral properties:

- Access control: Only from a whitelisted IP tied to a PRO account; both IPv4 and IPv6 supported.[1]
- Rate guidance: Pastebin recommends **no more than 1 request per second**; abuse can result in blocking.[1]
- Recency window: `api_scraping.php` returns the most recent public pastes, with **about a 2‑minute cache delay**.[1]
- Polling pattern: Docs recommend polling **100 most recent pastes once per minute**, caching IDs locally, and fetching each paste only once.[1]
- Coverage caveat (third-party): Community tooling reports that since 2020 the scraping API may only return pastes with a non-`text` syntax, significantly reducing observable volume of plain-text leaks.[2]

These behaviors directly affect freshness, rate limiting, and coverage assumptions for Zima.

#### 1.1.1 GET https://scrape.pastebin.com/api_scraping.php

**Purpose**
Return a list of the most recent public pastes as JSON objects with metadata and links to raw content and HTML pages.[1]

**Auth / execution requirements**

- Requires Pastebin PRO account.
- Requires a single **whitelisted IP** for the account; only that IP can access the endpoint.[1]
- Not accessible via generic scraping of pastebin.com; scraping `/raw/*` from the whitelisted IP is explicitly forbidden and may be blocked.[1]

**HTTP method & path**

- Method: `GET`
- URL: `https://scrape.pastebin.com/api_scraping.php`[1]

**Query parameters**

- `limit` (optional): Maximum number of pastes to return; default is 50, max is 250.[1]
- `lang` (optional): Restrict results to a given syntax language (e.g., `lang=php`); must use the short syntax codes from the main API docs (e.g., `php`, `java`, etc.).[3][1]

**Supported entity_type(s)**

- Provider does **not** support direct search by email/domain/IP/etc.; output is an unfiltered stream of recent pastes.[1]
- Zima will treat this as a **generic text source**, using internal logic to match entities (email, domain, username, etc.) in content (inferred, not documented).

**Top-level response fields and types**

Response is a JSON array of objects; each object has at least the following fields:[4][5][1]

- `scrape_url` (string): URL to fetch raw paste data via scraping API, e.g. `https://scrape.pastebin.com/api_scrape_item.php?i=0CeaNm8Y`.[1]
- `full_url` (string): Public HTML paste URL, e.g. `https://pastebin.com/0CeaNm8Y`.[1]
- `date` (string, Unix timestamp): Paste creation time in seconds since epoch, returned as a string.[1]
- `key` (string): Paste key identifier, e.g. `0CeaNm8Y`.[1]
- `size` (string): Paste size in bytes, returned as a string.[1]
- `expire` (string): Expiration time as Unix timestamp string, or `0` for no expiration.[1]
- `title` (string): Paste title; may be empty string when untitled.[5][1]
- `syntax` (string): Short syntax code, e.g. `java`, `php`, `text`; aligns with `api_paste_format` codes from Developers API.[3][1]
- `user` (string): Username of paste author, or empty string if guest.[5][1]

All of these fields are shown in the official example output, but the docs do **not** explicitly mark which ones are optional; third‑party examples show `title` and `user` can be blank.[5][1]

**Presence classification**

- Always present (per example and ecosystem usage): `scrape_url`, `full_url`, `date`, `key`, `size`, `expire`, `syntax`.[5][1]
- Often optional/empty but present as fields: `title`, `user` can be empty strings.[5][1]
- Premium‑tier differences: Docs note **Enterprise API can remove syntax-only limitation** and add commercial-use features, but do not document extra fields.[1]

**Response variants**

- Successful hit (default behavior): JSON array with up to `limit` paste metadata objects; may be empty if there are temporarily no new pastes, but this is not documented.[1]
- Successful no-hit: Not explicitly documented; likely an empty JSON array `[]` when no recent pastes, inferred from example shape and community code.[6][1]
- Partial / limited result: Controlled by `limit` parameter; max 250; no pagination cursor or offset.
- Error cases: Docs do not define JSON error schema; likely HTTP 403/401 when IP not whitelisted or account not PRO (inferred). All scraping-related errors are effectively undocumented.

**Important example excerpt**

```json
[
  {
    "scrape_url": "https://scrape.pastebin.com/api_scrape_item.php?i=0CeaNm8Y",
    "full_url": "https://pastebin.com/0CeaNm8Y",
    "date": "1442911802",
    "key": "0CeaNm8Y",
    "size": "890",
    "expire": "1442998159",
    "title": "Once we all know when we goto function",
    "syntax": "java",
    "user": "admin"
  }
]
```

#### 1.1.2 GET https://scrape.pastebin.com/api_scrape_item.php?i=UNIQUE_PASTE_KEY

**Purpose**
Return the **raw content** of a single paste via scraping API, using a paste key from `api_scraping.php` output.[1]

**Auth / execution requirements**

- Requires PRO account and whitelisted IP (same constraints as `api_scraping.php`).[1]
- Must not scrape `https://pastebin.com/raw/{key}` with the whitelisted IP; doing so may result in a block.[1]

**HTTP method & path**

- Method: `GET`
- URL: `https://scrape.pastebin.com/api_scrape_item.php?i=UNIQUE_PASTE_KEY`[1]

**Query parameters**

- `i` (required): Paste key string from `key` field or URL path.

**Response body**

- Content type: Not explicitly documented, but behavior is described as **“RAW data of any paste”**; third‑party examples treat this as plain text.[7][6][1]
- No JSON wrapper or structured fields; body is the full paste text (inferred from docs and ecosystem usage).

**Presence & variants**

- Successful hit: 2xx with full paste content as body.
- No-hit / error: Docs do not specify; likely standard HTTP errors (e.g., 404 for missing paste, 403 if IP not whitelisted), inferred.

This endpoint is the primary **content source** Zima must inspect for credentials and PII; there is no provider-side parsing or entity awareness.

#### 1.1.3 GET https://scrape.pastebin.com/api_scrape_item_meta.php?i=UNIQUE_PASTE_KEY

**Purpose**
Return **metadata for a single paste** as JSON, keyed by `i` (paste key).[1]

**Auth / execution requirements**

- Same PRO + whitelisted IP requirements as other scraping endpoints.[1]

**HTTP method & path**

- Method: `GET`
- URL: `https://scrape.pastebin.com/api_scrape_item_meta.php?i=UNIQUE_PASTE_KEY`[1]

**Response fields and types**

- Docs state only that the endpoint returns “metadata of any paste” and do **not** show an explicit example.[1]
- It is reasonable (but not guaranteed) to assume the same fields as objects in `api_scraping.php` (`scrape_url`, `full_url`, `date`, `key`, `size`, `expire`, `title`, `syntax`, `user`) with a JSON object shape.[6][5][1]
- Treat field list and types as **inferred from `api_scraping.php` and third‑party examples**, not formally documented.

**Presence & variants**

- Successful hit: Presumed 2xx with a single JSON object containing paste metadata.
- No-hit / error: Undocumented; likely 404 or error page if key invalid (inferred).

For Zima, this endpoint is optional, since `api_scraping.php` already exposes metadata needed for most use-cases.

### 1.2 Developers API overview (mostly non-intel)

The **Developers API** is oriented around managing pastes (create, list, delete) and retrieving user information.[3]
It does **not** provide any full-text or entity-based search across public pastes; content search must be built by the client using scraping API + custom logic.[3][1]

#### 1.2.1 POST https://pastebin.com/api/api_login.php (obtain api_user_key)

**Purpose**
Exchange a username/password and developer key for a long-lived `api_user_key` used to authenticate user-scoped operations.[3]

**Auth / execution requirements**

- Requires:
  - `api_dev_key` (developer API key associated with a Pastebin account),
  - `api_user_name` (Pastebin username),
  - `api_user_password` (plaintext password of that account).[3]

**HTTP method & path**

- Method: `POST`
- URL: `https://pastebin.com/api/api_login.php`[3]

**POST parameters (required)**

- `api_dev_key` (string)
- `api_user_name` (string)
- `api_user_password` (string)[3]

**Response variants**

- Successful: Body is a plaintext `api_user_key` string, e.g. `6c6d3fe13b19bbd6e479b705df0a607f`.[3]
- Error responses (plaintext):
  - `Bad API request, use POST request, not GET`
  - `Bad API request, invalid api_dev_key`
  - `Bad API request, invalid login`
  - `Bad API request, account not active`
  - `Bad API request, invalid POST parameters`[3]

No structured JSON or XML is provided.

#### 1.2.2 POST https://pastebin.com/api/api_post.php (multi-option)

This endpoint is multi-purpose; behavior is controlled by `api_option`.[3]

**Common parameters**

- `api_dev_key` (string, required)[3]
- `api_option` (string, required): `paste`, `list`, `delete`, `userdetails`, or `show_paste` (via `api_raw` helper).[3]

##### 1.2.2.1 api_option=paste — create a new paste

**Purpose**
Create a new paste (guest or user-scoped) with text content and metadata.[3]

**POST parameters**

- Required:
  - `api_dev_key` (string)
  - `api_option=paste`
  - `api_paste_code` (string; paste body text)[3]
- Optional:
  - `api_user_key` (string; to create under a user account)[3]
  - `api_paste_name` (string; title)[3]
  - `api_paste_format` (string; syntax code, see language list)[3]
  - `api_paste_private` (string; `0` public, `1` unlisted, `2` private)[3]
  - `api_paste_expire_date` (string; e.g. `N`, `10M`, `1H`, `1D`, `1W`, `2W`, `1M`, `6M`, `1Y`)[3]
  - `api_folder_key` (string; folder ID)[3]

**Response variants**

- Successful: Body is URL of the new paste, e.g. `https://pastebin.com/UIFdu235s`.[3]
- Errors: Plaintext `Bad API request, ...` messages for invalid options, keys, sizes, and parameters (e.g., `api_paste_code was empty`, `maximum paste file size exceeded`, etc.).[3]

This operation is **out-of-scope for Zima’s breach / alias detection**, as it is about authoring content.

##### 1.2.2.2 api_option=list — list pastes created by a user

**Purpose**
List pastes created under an authenticated user account as XML.[3]

**POST parameters**

- Required:
  - `api_dev_key`
  - `api_user_key`
  - `api_option=list`[3]
- Optional:
  - `api_results_limit` (string; default 50, min 1, max 1000)[3]

**Response**

- XML listing of `<paste>` elements with child tags:[3]
  - `paste_key` (string)
  - `paste_date` (Unix timestamp string)
  - `paste_title` (string)
  - `paste_size` (string)
  - `paste_expire_date` (Unix timestamp string or `0`)
  - `paste_private` (string; `0` public, `1` unlisted, `2` private)
  - `paste_format_long` (string; e.g., `JavaScript`)
  - `paste_format_short` (string; e.g., `javascript`)
  - `paste_url` (string)
  - `paste_hits` (string; view count)
- Alternate non-error response: `No pastes found.` if the user has no pastes.[3]

**Errors**

- Plaintext `Bad API request, invalid api_option / api_dev_key / api_user_key`.[3]

From a breach-monitoring perspective this is **user-centric** and not a discovery feed; for Zima it is only relevant if monitoring an organization’s own Pastebin account (utility).

##### 1.2.2.3 api_option=delete — delete a paste

**Purpose**
Delete a paste created by the authenticated user.[3]

**POST parameters**

- `api_dev_key` (required)
- `api_user_key` (required)
- `api_paste_key` (required)
- `api_option=delete`[3]

**Response variants**

- Success: `Paste Removed`.[3]
- Errors: `Bad API request, invalid api_option / api_dev_key / api_user_key / invalid permission to remove paste`.[3]

This is operational hygiene, not an intel source.

##### 1.2.2.4 api_option=userdetails — get user profile & settings

**Purpose**
Retrieve user profile info and account settings as XML.[3]

**POST parameters**

- `api_dev_key` (required)
- `api_user_key` (required)
- `api_option=userdetails`[3]

**Response**

- XML `<user>` element with subfields:[3]
  - `user_name`
  - `user_format_short` (default syntax)
  - `user_expiration` (default expiration code)
  - `user_avatar_url`
  - `user_private` (default paste visibility; 0 public, 1 unlisted, 2 private)
  - `user_website`
  - `user_email`
  - `user_location`
  - `user_account_type` (0 normal, 1 PRO)

**Errors**

- Plaintext `Bad API request, invalid api_option / api_dev_key / api_user_key`.[3]

This endpoint exposes an **email address and location for the Pastebin account owner**, but only for authenticated access to one’s own account; it is not an OSINT feature and is mostly out-of-scope.

##### 1.2.2.5 api_option=show_paste via https://pastebin.com/api/api_raw.php

**Purpose**
Fetch **raw content of a user’s paste**, including private ones, using `api_user_key` and `api_paste_key`.[3]

**HTTP specifics**

- URL: `https://pastebin.com/api/api_raw.php` (docs); example curl shows `api_post.php`, but text clarifies raw API endpoint.[3]
- Method: `POST`
- Required POST params: `api_dev_key`, `api_user_key`, `api_paste_key`, `api_option=show_paste`.[3]

**Response**

- Body is raw paste content (no structured fields).[3]
- Errors: `Bad API request, invalid api_option / api_dev_key / api_user_key / invalid permission to view this paste or invalid api_paste_key`.[3]

This is not suited for broad threat monitoring because it is **scoped to one authenticated user’s pastes**.

##### 1.2.2.6 Non-API raw: https://pastebin.com/raw/{key}

Docs also mention that `https://pastebin.com/raw/{paste_key}` returns raw contents of any public or unlisted paste and is “not part of the API”.[3]
However, Scraping API docs explicitly warn not to scrape `/raw/*` with a whitelisted IP.[1]
For Zima, **all large-scale monitoring should prefer scraping API**, not `/raw/*`.

***

## 2. Module Mapping Appendix

### 2.1 High-level module roles

- **breach_monitor**: Scan Pastebin scraping feed for evidence of credential leaks or PII exposures involving monitored identities (email, domain); generate breach-related signals.
- **alias_correlation**: Use paste metadata and content to correlate monitored identities with additional aliases (Pastebin usernames, handles, contextual nicknames) and contextual mentions.

Pastebin offers **no direct “search by email/domain” API**; instead, both modules must pull the recent-pastes stream via `api_scraping.php`, then fetch content and run Zima-side detection logic.[1]

### 2.2 Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---------------|-----------------|----------------------|----------------|-------------|-------------|--------------|-------|
| breach_monitor | signal_producer | scrape_recent_pastes | `GET https://scrape.pastebin.com/api_scraping.php` | direct_signal_input | email, domain | Only process pastes from scraping feed; dedupe by `key`; respect `limit` and recommended polling (e.g., 100 pastes per minute); ignore rows where `expire` is in the past at processing time. | https://pastebin.com/doc_scraping_api[1] | Provides metadata and links to raw content; no entity/search support; 2‑minute cache delay and PRO + whitelisted IP required.[1] |
| breach_monitor | signal_producer | fetch_paste_raw | `GET https://scrape.pastebin.com/api_scrape_item.php?i={key}` | direct_signal_input | email, domain | For each candidate paste from `api_scraping.php`, fetch raw content once; run Zima breach detection to decide if credentials/PII for monitored identities are present. | https://pastebin.com/doc_scraping_api[1] | Raw text body is the only place credentials/PII appear; endpoint requires same PRO + IP whitelisting and must not be confused with `/raw/{key}`.[1] |
| breach_monitor | signal_producer | fetch_paste_meta | `GET https://scrape.pastebin.com/api_scrape_item_meta.php?i={key}` | enrichment_only | email, domain | Optionally fetch per-paste metadata if `api_scraping.php` feed is not preserved; gate on pastes already flagged as containing monitored identities so as not to multiply requests. | https://pastebin.com/doc_scraping_api[1] | Field set is inferred from recent-paste JSON; use only when additional metadata is needed beyond initial feed.[1][6] |
| breach_monitor | signal_producer | dev_list_user_pastes | `POST https://pastebin.com/api/api_post.php` (`api_option=list`) | utility_only | account (pastebin account) | Only use if an organization explicitly wants to monitor or clean up its **own** Pastebin account; otherwise ignore for threat intel. | https://pastebin.com/doc_api[3] | Returns XML listing of pastes for one authenticated user; no search or OSINT across other users. |
| alias_correlation | signal_producer | scrape_recent_pastes | `GET https://scrape.pastebin.com/api_scraping.php` | direct_signal_input | email, domain, username | Same gating as breach_monitor, but instead of requiring credential patterns, only require that monitored email/domain appear in metadata or content; use `user` field as candidate alias. | https://pastebin.com/doc_scraping_api[1] | Provides `user` (author username) and `title` for alias extraction; mentions alone are not breaches and should map to alias/mention signals, not credential breaches. |
| alias_correlation | signal_producer | fetch_paste_raw | `GET https://scrape.pastebin.com/api_scrape_item.php?i={key}` | direct_signal_input | email, domain, username | When a monitored identity is suspected in metadata (e.g., from `title`) or from earlier processing, fetch raw content to extract aliases from context (nicknames, handles) and weak mentions. | https://pastebin.com/doc_scraping_api[1] | Content is unstructured; all alias logic is Zima-side and should be clearly separated from credential detection. |
| alias_correlation | signal_producer | fetch_paste_meta | `GET https://scrape.pastebin.com/api_scrape_item_meta.php?i={key}` | enrichment_only | email, domain, username | Optional: enrich alias-correlation findings with precise `size`, `expire`, `syntax`, `user` when not captured from initial feed. | https://pastebin.com/doc_scraping_api[1] | Usually redundant if initial scraping feed is persisted. |
| alias_correlation | signal_producer | dev_userdetails | `POST https://pastebin.com/api/api_post.php` (`api_option=userdetails`) | out_of_scope | account | Only returns info for authenticated Pastebin account; no OSINT over arbitrary users. Avoid for threat intel. | https://pastebin.com/doc_api[3] | Contains sensitive account email & location; using it for third-party monitoring is not appropriate. |
| breach_monitor, alias_correlation | signal_producer | raw_non_api | `GET https://pastebin.com/raw/{key}` | out_of_scope | email, domain | Do **not** use from whitelisted IP; rely on scraping API instead. | https://pastebin.com/doc_api[3]; https://pastebin.com/doc_scraping_api[1] | Docs explicitly recommend using Scraping API and warn that scraping `/raw/*` from whitelisted IP leads to blocking. |


***

## 3. Signal Contract Table

Only the **scraping API** is used as a signal source; Developers API operations are utility/out-of-scope. The table below defines Zima-level signals that should be emitted.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|-----------------|-------------|----------|----------|-------------------------|-----------------|------------|--------------|-------------------|-----------------|-------------------|------------------|----------------|---------------|-------|
| breach_monitor | breach_monitor | pastebin | `api_scraping.php` + `api_scrape_item.php` | credential_breach_found | identity_security | high | yes | Elevate to **critical** when Zima’s content analysis determines that the monitored identity’s credentials are exposed in plaintext (e.g., `email:password`, password in same line as email); keep as **high** when only hashed/obfuscated credentials or strong breach indicators without confirmed plaintext. | email, domain | true_finding | For each object returned by `GET https://scrape.pastebin.com/api_scraping.php` where Zima has not yet processed `key`, fetch raw content via `GET https://scrape.pastebin.com/api_scrape_item.php?i={key}`; if raw body contains a monitored email or domain **and** internal breach rules classify nearby text as credential data (password or password hash) for that identity, emit this signal. | From `api_scraping.php`: `key`, `full_url`, `scrape_url`, `date`, `size`, `expire`, `title`, `syntax`, `user`; plus paste raw body snapshot or stable hash (Zima internal). | From `api_scraping.php` and optional `api_scrape_item_meta.php`: `lang` filter used, polling timestamp, first N and last N characters of paste, detection metadata (e.g., line numbers, pattern type) stored as enrichment not separate signals. | `Credential data for {entity} was found in a public Pastebin paste ({paste_key}).` | derived | https://pastebin.com/doc_scraping_api[1] | Pastebin does not label breaches; all credential detection is Zima-side. A paste mention alone must not trigger this signal; require strong credential evidence. Respect 2‑minute delay, PRO + IP whitelisting, and rate guidance; dedupe strictly on `key`. |
| breach_monitor | breach_monitor | pastebin | `api_scraping.php` + `api_scrape_item.php` | pii_exposure_found_in_paste | identity_security | high | yes | Use **high** when exposed data includes sensitive PII (e.g., full name plus address, phone, national ID) with clear linkage to monitored identity; optionally downgrade to **medium** for older pastes (`date` older than threshold) or weakly-linked PII (inferred policy). | email, domain | true_finding | For each newly observed `key` from `api_scraping.php`, fetch raw content via `api_scrape_item.php`; if raw text contains a monitored email or domain and Zima’s classifiers detect high-confidence PII (addresses, phone numbers, government IDs, etc.) tied to that identity, emit this signal, even if no password is present. | Same as above: `key`, `full_url`, `scrape_url`, `date`, `size`, `expire`, `title`, `syntax`, `user`, plus raw-body snippet or structured PII extraction stored in evidence. | Same enrichment as credential_breach_found; may also store PII-type labels (e.g., `address`, `phone`) and approximate position offsets as enrichment only. | `Potential PII for {entity} was exposed in a public Pastebin paste ({paste_key}).` | inferred | https://pastebin.com/doc_scraping_api[1] | Provider has no PII fields; all PII detection is Zima-side. Severity tuning (e.g., by age using `date` or `expire`) must be calibrated from real data. |
| alias_correlation | alias_correlation | pastebin | `api_scraping.php` + `api_scrape_item.php` | identity_alias_mentioned | identity_security | low | yes | Keep **low** when only a single weak mention associates an alias with the monitored identity; consider **medium** when the same alias and identity co-occur across multiple distinct paste `key`s or when associated with clear breach indicators (inferred correlation policy). | email, domain, username | contextual_enrichment | For each newly processed paste from `api_scraping.php`, fetch raw content via `api_scrape_item.php`; if a monitored email/domain appears in content or `title`, and either (a) `user` field is non-empty and not yet known as an alias for this identity, or (b) Zima’s alias extraction finds new candidate handles/usernames near the identity, emit this alias-correlation signal. Do **not** require credential or PII patterns. | From `api_scraping.php`: `key`, `full_url`, `scrape_url`, `date`, `title`, `syntax`, `user`; plus any extracted alias strings and context snippet in evidence. | Optional `size`, `expire`, polling timestamp, detection metadata (e.g., alias extraction rule used, co-occurrence counts) as enrichment only. | `A new alias {alias} related to {entity} was observed in a public Pastebin paste ({paste_key}).` | derived | https://pastebin.com/doc_scraping_api[1] | This signal is about identity surface, not breach. A mention without credentials should not be suppressed, but severity should remain low by default. De-duplicate by `(entity, alias, key)` and consider aggregating multiple observations before escalating. |

**Why no standalone "weak mention" breach signal?**
A plain mention of an email or domain in a paste without PII or credentials is **not inherently a breach**; such mentions are better modeled as alias/mention enrichment (`identity_alias_mentioned`) rather than a breach-monitor signal. This honors the requirement to separate alias correlation, weak mentions, and clear credential exposures.[1]

***

## 4. Severity Rules

### 4.1 credential_breach_found (breach_monitor)

- **Base severity**: `high`, because any confirmed credential leak involving a monitored identity is a high-impact, actionable event.[1]
- **Critical escalation**: When Zima’s analyzers determine that the exposed credential is **plaintext** (e.g., un-hashed password adjacent to the account identifier), this meets the platform’s `critical` definition: direct credential exposure and immediate account compromise risk.
- **Medium downgrade (optional)**: For very old pastes (`date` older than a defined horizon) where credentials are clearly invalid (e.g., previously rotated), Zima may downgrade to `medium`; this is **policy-dependent and inferred**, not in provider docs.
- **Provider score usage**: Pastebin provides no risk or reputation score; severity is fully Zima-defined.

This fits the platform guide: plaintext passwords or highly exploitable leaks → `critical`; confirmed breach without plaintext (hashed only) → `high`.

### 4.2 pii_exposure_found_in_paste (breach_monitor)

- **Base severity**: `high`, as exposed PII (address, phone, IDs) tied to monitored identity matches “exposed PII” in the `high` definition.
- **Conditional adjustment**:
  - `medium` when exposure is historical or low-sensitivity PII (e.g., just a public phone number) or very old pastes.
  - Remain `high` when data is sensitive (IDs, full addresses) and recent (`date` within configured window).
- All conditions rely on Zima classifiers acting on raw content; provider exposes no PII metadata.

### 4.3 identity_alias_mentioned (alias_correlation)

- **Base severity**: `low`, since an alias link or mention is primarily surface mapping, not direct compromise evidence.
- **Possible escalation**: `medium` when:
  - The same alias and identity pair is observed in multiple distinct pastes (`key` differs), or
  - The paste is also tied to high/critical breach signals (co-occurs with `credential_breach_found` or `pii_exposure_found_in_paste`).
- In all cases, this signal’s `finding_kind` remains `contextual_enrichment`; severity reflects correlation strength, not breach severity.

### 4.4 Assessment of first-pass severity assessment

The scaffold’s rough provider severity notion (none recorded yet) should be refined as:

- Scraping API itself is **neutral**; Pastebin does not label risk.
- Zima’s usage can produce both `critical` (plaintext credentials) and `high` (hashed credentials / PII) incidents for `breach_monitor`, and `low`/`medium` enrichment for `alias_correlation`.


***

## 5. Confidence Guidance

### 5.1 Source reliability

- Pastebin is a long-standing, centralized paste hosting platform; scraping API results are authoritative for **what is currently publicly available**.[1]
- However, pastes are **user-generated and unauthenticated**; the correctness of leaked data (e.g., whether passwords are valid) is unknown and may include fakes.
- Third-party reports show that changes to the scraping API (e.g., only returning syntactically-tagged pastes) affect **coverage** and must be tracked over time.[2]

### 5.2 Freshness and staleness

- Scraping feed has about a **2-minute delay** due to caching; new leaks can appear up to that late.[1]
- `date` is the creation timestamp; `expire` can be `0` (no expiry) or a Unix timestamp; once a paste expires or is manually deleted, it may no longer be accessible even if cached locally.[1]
- Scraping API docs recommend polling 100 most recent pastes once per minute and avoiding re-fetches to limit load; this also defines a practical **discovery SLA** for Zima.[1]

### 5.3 Corroboration opportunities

For each signal type:

- **credential_breach_found**:
  - Check whether the same credentials appear in other breach sources (internal leak corpus, other dark-web providers).
  - Attempt log-in telemetry correlation (failed/successful logins) where available.
  - Compare `date` with known breach timelines; if a paste predates a known incident, treat as early evidence.
- **pii_exposure_found_in_paste**:
  - Cross-check exposed PII against organization systems for correctness.
  - Look for identical PII in other breach datasets or OSINT sources.
- **identity_alias_mentioned**:
  - Confirm alias via other platforms (e.g., same alias used in email address local-part, social media, other breach dumps).
  - Use repetition across multiple independent pastes as a strong corroboration signal.

### 5.4 Calibration TODOs

- Quantify **false positive rate** for credential detection in Pastebin pastes (e.g., regex hits that are not real passwords), and tune detection rules accordingly.
- Calibrate severity thresholds by analyzing:
  - Paste age (`date`) distribution vs. credential validity.
  - Relationship between `syntax` values and leak likelihood (e.g., `text`, `sql`, `ini` might be higher-yield).
- Track **coverage drift** when Pastebin changes scraping behavior; re-validate volume by comparing raw website metrics vs. scraping API counts over time.[2][1]
- Establish entity-level confidence scores for alias correlations based on number of pastes, co-occurrence with breach events, and cross-provider corroboration.


***

## 6. Tags

Suggested tags per signal type:

- **credential_breach_found**: `['breach', 'credential_stuffing', 'plaintext_password']` (drop `plaintext_password` tag when only hashes are seen).
- **pii_exposure_found_in_paste**: `['breach', 'pii_exposure']`.
- **identity_alias_mentioned**: `['breach', 'threat_actor']` when alias appears in threat contexts; otherwise just `['breach']` or a future `identity`-style tag.

These tags are Zima-level semantics and not present in Pastebin data.


***

## 7. Implementation Notes

### 7.1 Field paths and parsing

- **Scraping feed (`api_scraping.php`)**:
  - Preserve each JSON object as-is in the provider client; map fields directly:
    - `key` → natural identifier for deduplication.
    - `full_url`, `scrape_url` → evidence and retrieval links.
    - `date`, `expire` → Unix timestamps used for freshness and expiry handling.
    - `size` → may be useful for triaging extremely large pastes.
    - `title`, `syntax`, `user` → inputs to alias correlation and prioritization.[1]
- **Raw content (`api_scrape_item.php`)**:
  - Treat response body as opaque text blob; do not attempt to wrap in JSON.
  - Store either full text (subject to privacy policy) or a stable content hash plus sampled snippets, depending on Zima’s retention rules.
- **Optional metadata (`api_scrape_item_meta.php`)**:
  - Only call when `api_scraping.php` results are not persisted; anticipate same field set as in feed but treat any differences defensively.[1]

### 7.2 Null / empty / no-hit behavior

- If `api_scraping.php` returns an empty array (inferred no-hit scenario), modules should treat this as **no new data**, not an error.
- For each paste entry:
  - `title` and `user` may be empty strings; alias_correlation must handle missing alias gracefully and rely on content-derived aliases instead.[5][1]
  - `expire` equal to `0` means “no expiry”; otherwise, interpret as Unix timestamp when the paste will become unavailable.[1]
- If `api_scrape_item.php` returns non-2xx or an empty body, skip detection for that `key` but avoid infinite retry loops; log for diagnostics.

### 7.3 Rate limits, billing, licensing, premium constraints

- Scraping API is **PRO-only**, with one whitelisted IP per account.[1]
- Recommended rate is at most **1 request per second**; while this is a recommendation, excessive scraping can result in blocks.[1]
- Docs recommend polling **once per minute** for the 100 most recent pastes; Zima should align poll-and-fetch patterns with this guidance to avoid throttling.[1]
- Enterprise API removes syntax-only limitation and adds commercial-use permissions; using scraping API at scale for a SaaS like Zima likely requires Enterprise terms of use (business/legal concern).[1]

### 7.4 Deduplication keys & identifiers

- Use `key` from scraping feed as **primary deduplication key** per paste.[1]
- Maintain per-module high-water marks (e.g., last processed `date` or sorted `key` set); avoid rescanning the same key unless detection logic substantially changes.
- For alias_correlation, dedupe at `(entity, alias, key)` level so the same alias in the same paste does not generate multiple identical signals.

### 7.5 Evidence retention

- For compliance and remediation, store at least:
  - Paste `key`, `full_url`, `scrape_url`, `date`, `expire`, `syntax`, `user`, `title`.
  - For breach signals: minimal raw content sufficient to reproduce the detection (e.g., specific lines or hashed/partially masked credentials) subject to privacy requirements.
- Consider encrypting stored raw snippets and strictly scoping access, since they may contain highly sensitive credentials or PII.

### 7.6 Responsibility boundaries

- **Provider client** (Pastebin integration):
  - Handles authentication (PRO credentials, IP whitelisting configuration external to code).
  - Implements polling of `api_scraping.php`, fetching of raw content, retry/backoff, and basic deduplication on `key`.
  - Exposes normalized provider events (feed entries + raw content) to modules.
- **Module mapper (breach_monitor, alias_correlation)**:
  - Implements detection rules over raw content and metadata (credential regexes, PII classifiers, alias extraction).
  - Maps provider events to Zima signal schema (`signal_type`, `category`, `severity`, `summary_template`, `evidence`).
- **Correlation layer**:
  - Joins Pastebin-derived signals with signals from other breach/dark-web providers.
  - Performs alias graph building, incident grouping, and enrichment across providers.


***

{
  "provider": "pastebin",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "scrape_recent_pastes",
      "endpoint_or_artifact": "GET https://scrape.pastebin.com/api_scraping.php",
      "classification": "direct_signal_input",
      "entity_types": ["email", "domain"],
      "gating_logic": "Only process pastes from scraping feed; dedupe by key; respect limit and recommended polling (e.g., 100 pastes per minute); ignore rows where expire is in the past at processing time.",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Provides metadata and links to raw content; no entity/search support; ~2-minute cache delay and PRO + whitelisted IP required."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "fetch_paste_raw",
      "endpoint_or_artifact": "GET https://scrape.pastebin.com/api_scrape_item.php?i={key}",
      "classification": "direct_signal_input",
      "entity_types": ["email", "domain"],
      "gating_logic": "For each candidate paste from api_scraping.php, fetch raw content once; run Zima breach detection to decide if credentials/PII for monitored identities are present.",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Raw text body is the only place credentials/PII appear; endpoint uses same PRO + IP-whitelisting and must not be confused with https://pastebin.com/raw/{key}."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "fetch_paste_meta",
      "endpoint_or_artifact": "GET https://scrape.pastebin.com/api_scrape_item_meta.php?i={key}",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Optionally fetch per-paste metadata if api_scraping.php feed is not persisted; gate on pastes already flagged as containing monitored identities to avoid extra requests.",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Field set is inferred to match api_scraping.php objects; only needed when initial feed metadata is not retained."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "dev_list_user_pastes",
      "endpoint_or_artifact": "POST https://pastebin.com/api/api_post.php (api_option=list)",
      "classification": "utility_only",
      "entity_types": ["account"],
      "gating_logic": "Use only if an organization explicitly wants to monitor or clean up its own Pastebin account; ignore for generic threat intel.",
      "citation_refs": ["https://pastebin.com/doc_api"],
      "notes": "Returns XML listing of pastes for one authenticated user; no search across other users."
    },
    {
      "module": "alias_correlation",
      "provider_role": "signal_producer",
      "provider_method": "scrape_recent_pastes",
      "endpoint_or_artifact": "GET https://scrape.pastebin.com/api_scraping.php",
      "classification": "direct_signal_input",
      "entity_types": ["email", "domain", "username"],
      "gating_logic": "Same polling/dedupe as breach_monitor, but only require that a monitored email/domain appears in metadata or content; treat non-empty user field as candidate alias.",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Provides user (author username) and title for alias extraction; simple mentions are not breaches and should map to alias/mention correlation, not credential leaks."
    },
    {
      "module": "alias_correlation",
      "provider_role": "signal_producer",
      "provider_method": "fetch_paste_raw",
      "endpoint_or_artifact": "GET https://scrape.pastebin.com/api_scrape_item.php?i={key}",
      "classification": "direct_signal_input",
      "entity_types": ["email", "domain", "username"],
      "gating_logic": "When a monitored identity is suspected from metadata or prior processing, fetch raw content to extract aliases from surrounding context; do not require credential patterns.",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Content is unstructured; alias logic is entirely Zima-side and should be clearly separated from credential/PII detection."
    },
    {
      "module": "alias_correlation",
      "provider_role": "signal_producer",
      "provider_method": "fetch_paste_meta",
      "endpoint_or_artifact": "GET https://scrape.pastebin.com/api_scrape_item_meta.php?i={key}",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain", "username"],
      "gating_logic": "Optional: enrich alias-correlation findings with size, expire, syntax, user when not already captured from api_scraping.php.",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Usually redundant if initial scraping feed objects are persisted."
    },
    {
      "module": "alias_correlation",
      "provider_role": "signal_producer",
      "provider_method": "dev_userdetails",
      "endpoint_or_artifact": "POST https://pastebin.com/api/api_post.php (api_option=userdetails)",
      "classification": "out_of_scope",
      "entity_types": ["account"],
      "gating_logic": "Do not use for OSINT; only returns info for the authenticated Pastebin account owner.",
      "citation_refs": ["https://pastebin.com/doc_api"],
      "notes": "Contains email and location for a single account; not appropriate for third-party monitoring."
    },
    {
      "module": "breach_monitor,alias_correlation",
      "provider_role": "signal_producer",
      "provider_method": "raw_non_api",
      "endpoint_or_artifact": "GET https://pastebin.com/raw/{key}",
      "classification": "out_of_scope",
      "entity_types": ["email", "domain"],
      "gating_logic": "Do not use from the whitelisted IP; rely on scraping API endpoints instead.",
      "citation_refs": ["https://pastebin.com/doc_api", "https://pastebin.com/doc_scraping_api"],
      "notes": "Docs explicitly recommend using Scraping API and warn that scraping /raw/* from the whitelisted IP may lead to blocking."
    }
  ],
  "signal_contracts": [
    {
      "module": "breach_monitor",
      "source": "breach_monitor",
      "provider": "pastebin",
      "provider_method": "api_scraping.php + api_scrape_item.php",
      "signal_type": "credential_breach_found",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Elevate to critical when content analysis confirms plaintext credentials for the monitored identity (e.g., email:password on same line); keep high when only hashed/obfuscated credentials or non-plaintext indicators are present.",
      "entity_type": ["email", "domain"],
      "finding_kind": "true_finding",
      "trigger_condition": "For each new paste object from GET https://scrape.pastebin.com/api_scraping.php (unique key not yet processed), fetch raw content via GET https://scrape.pastebin.com/api_scrape_item.php?i={key}; if the raw body contains a monitored email or domain and internal breach rules classify nearby text as credential data (password or password hash) for that identity, emit this signal.",
      "evidence_fields": [
        "key",
        "full_url",
        "scrape_url",
        "date",
        "size",
        "expire",
        "title",
        "syntax",
        "user",
        "raw_body"
      ],
      "enrichment_fields": [
        "lang_filter_used",
        "poll_timestamp",
        "detection_metadata"
      ],
      "summary_template": "Credential data for {entity} was found in a public Pastebin paste ({paste_key}).",
      "evidence_status": "derived",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Pastebin does not label breaches; all credential detection is Zima-side. A mention alone must not trigger this signal; require strong credential evidence. Respect cache delay, PRO + IP whitelisting, and dedupe strictly on key."
    },
    {
      "module": "breach_monitor",
      "source": "breach_monitor",
      "provider": "pastebin",
      "provider_method": "api_scraping.php + api_scrape_item.php",
      "signal_type": "pii_exposure_found_in_paste",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Keep high when exposed PII includes sensitive data (e.g., address, phone, government ID) clearly tied to the monitored identity and the paste is recent; optionally downgrade to medium for old pastes or low-sensitivity PII based on Zima policy.",
      "entity_type": ["email", "domain"],
      "finding_kind": "true_finding",
      "trigger_condition": "For each new paste key from api_scraping.php, fetch raw content via api_scrape_item.php; if the raw text contains a monitored email or domain and classifiers detect high-confidence PII (address, phone, national ID, etc.) linked to that identity, emit this signal even if no password is present.",
      "evidence_fields": [
        "key",
        "full_url",
        "scrape_url",
        "date",
        "size",
        "expire",
        "title",
        "syntax",
        "user",
        "raw_body"
      ],
      "enrichment_fields": [
        "pii_types_detected",
        "detection_metadata",
        "poll_timestamp"
      ],
      "summary_template": "Potential PII for {entity} was exposed in a public Pastebin paste ({paste_key}).",
      "evidence_status": "inferred",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "Provider has no PII-specific fields; all PII detection is Zima-side. Severity tuning by age (date, expire) and PII type must be calibrated from real data."
    },
    {
      "module": "alias_correlation",
      "source": "alias_correlation",
      "provider": "pastebin",
      "provider_method": "api_scraping.php + api_scrape_item.php",
      "signal_type": "identity_alias_mentioned",
      "category": "identity_security",
      "severity": "low",
      "severity_is_conditional": "yes",
      "conditional_rule": "Remain low when only a single weak mention associates an alias with the monitored identity; consider medium when the same (entity, alias) pair appears across multiple distinct paste keys or when correlated with high/critical breach signals.",
      "entity_type": ["email", "domain", "username"],
      "finding_kind": "contextual_enrichment",
      "trigger_condition": "For each new paste from api_scraping.php, fetch raw content via api_scrape_item.php; if a monitored email or domain appears in content or title and either (a) user is non-empty and not yet known as an alias for this identity, or (b) alias extraction finds new candidate handles/usernames near the identity, emit this alias-correlation signal without requiring credential or PII patterns.",
      "evidence_fields": [
        "key",
        "full_url",
        "scrape_url",
        "date",
        "title",
        "syntax",
        "user",
        "raw_body"
      ],
      "enrichment_fields": [
        "size",
        "expire",
        "poll_timestamp",
        "alias_extraction_metadata"
      ],
      "summary_template": "A new alias {alias} related to {entity} was observed in a public Pastebin paste ({paste_key}).",
      "evidence_status": "derived",
      "citation_refs": ["https://pastebin.com/doc_scraping_api"],
      "notes": "This signal expands identity surface rather than indicating compromise. De-duplicate by (entity, alias, key) and consider aggregating multiple observations before escalating severity."
    }
  ],
  "confidence_guidance": [
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "credential_breach_found",
      "source_reliability": "Pastebin scraping API reliably reflects what is currently public on Pastebin, but paste content is user-generated and may contain fake or outdated credentials.",
      "freshness_considerations": "Scraping feed is cached with roughly a 2-minute delay; use date and expire fields to assess recency and whether the paste is still live when investigated.",
      "corroboration_rules": "Cross-check credentials against other breach sources and authentication telemetry where available; compare paste date with known breach timelines.",
      "calibration_todo": "Measure false positive rates for credential detection, tune regex/classifiers, and study relationship between paste age and credential validity to refine severity thresholds."
    },
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "pii_exposure_found_in_paste",
      "source_reliability": "Pastebin reliably hosts the exposed text but does not validate the correctness of PII; information may be partially fabricated or stale.",
      "freshness_considerations": "Use date and expire to differentiate recent vs historical PII exposures; treat expired or deleted pastes as lower-priority but still relevant for historical risk.",
      "corroboration_rules": "Verify exposed PII against internal records; look for the same PII values in other leaks or OSINT; treat repeated appearance across sources as higher confidence.",
      "calibration_todo": "Distinguish sensitivity levels of PII (e.g., address vs national ID) and adjust severity; monitor coverage drift if Pastebin changes scraping behavior."
    },
    {
      "module": "alias_correlation",
      "signal_type_or_use_case": "identity_alias_mentioned",
      "source_reliability": "Aliases and usernames in pastes are self-asserted and may not uniquely identify the monitored entity; single mentions are weak evidence.",
      "freshness_considerations": "Recent pastes may reflect current alias usage, but old pastes can still be useful for historical alias graphs; age should affect severity but not existence.",
      "corroboration_rules": "Increase confidence when the same alias co-occurs with the identity in multiple distinct pastes or appears in other providers' data; cross-check with other OSINT.",
      "calibration_todo": "Define scoring for alias strength based on repetition, context, and cross-provider confirmation; set thresholds for when alias signals should influence higher-level incident scoring."
    }
  ]
}
