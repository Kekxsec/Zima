---
title: "output / breach / snusbase"
aliases: ["snusbase output", "snusbase signal registry"]
tags: [zima, research, outputs, signal-registry, breach, snusbase, graph_exclude]
type: provider_research_output
provider: snusbase
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: snusbase.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
Snusbase is generally a strong breach‑intel provider for credential exposure: it offers a long‑running, API‑accessible index of many leaked databases (including hashes, some plaintext credentials, combolists, and cracked‑hash data), is widely referenced as a mainstream breach search engine, and exposes clear JSON APIs for search and tools, but it is commercial/crypto‑payment‑oriented and has hard rate limits and dataset‑quality variability that you’ll want to account for with corroboration and calibration in Zima rather than treating it as a single source of truth.

## API Surface Appendix

### `/data/stats` – Database Statistics

- **Endpoint / method**

    - `GET https://api.snusbase.com/data/stats`[docs.snusbase](https://docs.snusbase.com/)

- **Purpose**

    - Returns global information about Snusbase’s indexed datasets: total row count, available tables, and special feature flags (e.g. which tables support “view more” and “combo lookup”).[docs.snusbase](https://docs.snusbase.com/)

- **Auth / execution**

    - Does **not** require authentication (no `Auth` header).[docs.snusbase](https://docs.snusbase.com/)

- **Supported entity types**

    - Not entity-specific; global metadata only (no per‑email or per‑account view).

- **Top-level response fields**

    - `rows` (number) – total rows across all tables.[docs.snusbase](https://docs.snusbase.com/)

    - `tables` (object) – map of `table_name` → array of column names, e.g.
        `{"0001_STEALERLOGS_NA_121M_MALWARE_2023": ["email","username","password","host","_domain"], ...}`.[docs.snusbase](https://docs.snusbase.com/)

    - `features` (object) – feature flags by capability:[docs.snusbase](https://docs.snusbase.com/)

        - `view_more` (array[string]) – tables that expose “view more” (all columns) in UI/API.

        - `combo_lookup` (array[string]) – tables that back the combo-lookup feature.

- **Field presence**

    - `rows`, `tables` appear in the documented success example and are likely always present on 200 responses (derived from example, not explicitly guaranteed).[docs.snusbase](https://docs.snusbase.com/)

    - `features.view_more` and `features.combo_lookup` are documented but their presence for all deployments/tiers is not explicitly guaranteed (inferred).[docs.snusbase](https://docs.snusbase.com/)

- **Response variants**

    - **Successful hit (normal case)** – 200 with `rows`, `tables`, possibly `features` as above.[docs.snusbase](https://docs.snusbase.com/)

    - **Successful “no-hit”** – not applicable (global stats, not a search).

    - **Partial/limited** – not documented; if Snusbase changes features per tier, some keys under `features` may be absent (inferred).

- **Errors**

    - No endpoint-specific error example; generic HTTP error codes apply (see Error Handling section in docs).[docs.snusbase](https://docs.snusbase.com/)

- **Important example excerpt**

    - json

        `{   "rows": 18006941078,  "tables": {    "0001_STEALERLOGS_NA_121M_MALWARE_2023": [      "email", "username", "password", "host", "_domain"    ]  },  "features": {    "view_more": [      "0005_ZING_VN_51M_ENTERTAINMENT_052015"    ],    "combo_lookup": [      "0001_PEMIBLANC_COMBOLIST_245M_2018"    ]  } } ```[1]`


---

### `/data/search` – Database Search

- **Endpoint / method**

    - `POST https://api.snusbase.com/data/search`[docs.snusbase](https://docs.snusbase.com/)

- **Purpose**

    - Searches all or selected Snusbase datasets for specific terms (e.g. email, username, IP, password, hash, name, domain) and returns matching rows grouped by table or other keys.[docs.snusbase](https://docs.snusbase.com/)

- **Auth / execution**

    - Requires `Auth` header with activation code: `Auth: sb[...]`.[docs.snusbase](https://docs.snusbase.com/)

    - `Content-Type: application/json`.[docs.snusbase](https://docs.snusbase.com/)

- **Supported entity types (as “types”)**

    - Allowed `types` values:[docs.snusbase](https://docs.snusbase.com/)

        - `"email"`

        - `"username"`

        - `"lastip"`

        - `"password"`

        - `"hash"`

        - `"name"`

        - `"_domain"`

    - Multiple `types` can be supplied; each type is applied to all terms (documented behavior in “Example Search Queries”).[docs.snusbase](https://docs.snusbase.com/)

- **Request body parameters**

    - `terms` (array[string], required) – search terms.[docs.snusbase](https://docs.snusbase.com/)

    - `types` (array[string], required) – which columns to search against (enumeration above).[docs.snusbase](https://docs.snusbase.com/)

    - `wildcard` (boolean, optional) – enable Snusbase wildcard search (`*` any length, `_` single char). Wildcards cannot be first character in a term; they can be escaped with backslash.[docs.snusbase](https://docs.snusbase.com/)

    - `group_by` (boolean or string, optional) – grouping behavior:

        - default is `"db"` (group results by table/database).[docs.snusbase](https://docs.snusbase.com/)

        - `false` disables grouping.[docs.snusbase](https://docs.snusbase.com/)

        - other values (e.g. `"_domain"`, `"email"`) group by that column name; rows lacking that column are put under `NO_{GROUP_BY}` (e.g. `NO_EMAIL`).[docs.snusbase](https://docs.snusbase.com/)

    - `tables` (array[string], optional) – restrict search to specific table IDs; when used, all available columns from those tables are returned instead of a default subset.[docs.snusbase](https://docs.snusbase.com/)

- **Top-level response fields**

    - `took` (number) – query execution time in milliseconds.[docs.snusbase](https://docs.snusbase.com/)

    - `size` (number) – total number of matched rows (inferred from example name; not formally defined in text).[docs.snusbase](https://docs.snusbase.com/)

    - `results` (object) – map: `table_name` → array of row objects.[docs.snusbase](https://docs.snusbase.com/)

- **Row object fields (example)**

    - Example row from a breach table:[docs.snusbase](https://docs.snusbase.com/)

        - `username` (string)

        - `email` (string)

        - `lastip` (string, IP address)

        - `hash` (string, e.g. Argon2id hash)

        - `salt` (string)

        - `uid` (string or numeric identifier)

        - `created` (string, epoch timestamp as string)

        - `updated` (string, epoch timestamp as string)

    - Actual columns vary by table; for tables explicitly listed in `/data/stats.tables`, their columns are as listed (e.g. STEALERLOGS tables have `email`, `username`, `password`, `host`, `_domain`).[docs.snusbase](https://docs.snusbase.com/)

- **Field presence**

    - On a successful hit: `took`, `size`, `results` appear to be always present (derived from examples; not explicitly guaranteed).[docs.snusbase](https://docs.snusbase.com/)

    - Row-level columns are table-dependent; only “database stats” (`/data/stats`) defines which columns exist per table.[docs.snusbase](https://docs.snusbase.com/)

- **Response variants**

    - **Successful hit** – 200 with `size > 0` and `results` containing one or more table keys each mapping to an array of rows.[docs.snusbase](https://docs.snusbase.com/)

    - **Successful no-hit** – not explicitly documented; likely 200 with `size = 0` and `results` as an empty object (inferred).

    - **Grouped variants** – when `group_by` is set to a column (e.g. `"_domain"`), top-level `results` keys become group values plus possibly `NO_{GROUP_BY}` bucket for rows missing that column (documented).[docs.snusbase](https://docs.snusbase.com/)

- **Errors**

    - Generic error handling:

        - 400 for invalid/missing parameters, 401 for invalid/missing API key, 429 for rate limit exceeded; error messages provided in an `errors` array in the response body (shape not fully specified).[docs.snusbase](https://docs.snusbase.com/)

- **Important example excerpt**

    - Request:[docs.snusbase](https://docs.snusbase.com/)

        text

        `POST https://api.snusbase.com/data/search Content-Type: application/json Auth: YOUR_API_KEY_HERE {   "terms": ["example@gmail.com"],  "types": ["email"] }`

    - Response:[docs.snusbase](https://docs.snusbase.com/)

        json

        `{   "took": 31.714,  "size": 1233,  "results": {    "2123_BREACHFORUMS_BF_323K_HACKING_012026": [      {        "username": "avvd",        "email": "example@gmail.com",        "lastip": "127.0.0.9",        "hash": "$argon2i$v=19$m=65536,t=4,p=1$NVphazc1SUg3YUVxNFV3Nw$EmshtvIzcwhG8lnDTsl0XvzCyg7h8k+Qr3tgTQihvZI",        "salt": "Wlwirmmh",        "uid": "331153",        "created": "1729340505",        "updated": "1729341708"      }    ]  } }`


---

### `/tools/combo-lookup` – Combo-List Credential Lookup

- **Endpoint / method**

    - `POST https://api.snusbase.com/tools/combo-lookup`[docs.snusbase](https://docs.snusbase.com/)

- **Purpose**

    - Look up username/password combinations in Snusbase’s “combolist” datasets (large credential dumps). Returns plaintext credentials.[docs.snusbase](https://docs.snusbase.com/)

- **Auth / execution**

    - Requires `Auth` header and JSON body.[docs.snusbase](https://docs.snusbase.com/)

- **Supported entity types**

    - Provider-side `types`:

        - `"username"`

        - `"password"`[docs.snusbase](https://docs.snusbase.com/)

    - From Zima’s perspective, primary entity is typically `email` (supplied as a username), but the endpoint can also be driven by arbitrary usernames or passwords.

- **Request body parameters**

    - `terms` (array[string], required) – list of usernames or passwords to search.[docs.snusbase](https://docs.snusbase.com/)

    - `types` (array[string], required) – search dimension; must be subset of `["username","password"]`.[docs.snusbase](https://docs.snusbase.com/)

    - `wildcard` (boolean, optional) – wildcard search toggle.[docs.snusbase](https://docs.snusbase.com/)

    - `group_by` (boolean or string, optional) – grouping behavior (defaults to `"db"`, can be `false` or another column).[docs.snusbase](https://docs.snusbase.com/)

- **Top-level response fields**

    - `took` (number) – query execution time.[docs.snusbase](https://docs.snusbase.com/)

    - `size` (number) – count of matched rows (inferred).[docs.snusbase](https://docs.snusbase.com/)

    - `results` (object) – `table_name` → array of combo rows.[docs.snusbase](https://docs.snusbase.com/)

- **Row object fields (example)**

    - `username` (string)

    - `password` (string, clearly plaintext in examples).[docs.snusbase](https://docs.snusbase.com/)

- **Field presence**

    - For a hit: `took`, `size`, `results` present with at least one `table_name` key and an array of `{username, password}` objects (derived from example).[docs.snusbase](https://docs.snusbase.com/)

- **Response variants**

    - **Successful hit** – 200 with `size > 0` and one or more combos in `results`.[docs.snusbase](https://docs.snusbase.com/)

    - **Successful no-hit** – not documented; likely `size = 0` and `results` empty (inferred).

- **Errors**

    - Same global HTTP error semantics as other authenticated endpoints.[docs.snusbase](https://docs.snusbase.com/)

- **Important example excerpt**

    - json

        `{   "took": 2.905,  "size": 1194,  "results": {    "0007_COLLECTION3_COMBOLIST_300M_2019": [      {        "username": "example@gmail.com",        "password": "0981122847"      },      {        "username": "example@gmail.com",        "password": "123456"      }    ]  } } ```[1]`


---

### `/tools/hash-lookup` – Cracked Hash Lookup

- **Endpoint / method**

    - `POST https://api.snusbase.com/tools/hash-lookup`[docs.snusbase](https://docs.snusbase.com/)

- **Purpose**

    - Look up cracked passwords by hash or reverse-lookup hashes for a given plaintext password using Snusbase’s cracked password hash database.[docs.snusbase](https://docs.snusbase.com/)

- **Auth / execution**

    - Requires `Auth` header and JSON body.[docs.snusbase](https://docs.snusbase.com/)

- **Supported entity types**

    - Provider-side `types`:

        - `"hash"`

        - `"password"`[docs.snusbase](https://docs.snusbase.com/)

- **Request body parameters**

    - `terms` (array[string], required) – list of hashes or passwords to look up.[docs.snusbase](https://docs.snusbase.com/)

    - `types` (array[string], required) – `"hash"` or `"password"` (or both).[docs.snusbase](https://docs.snusbase.com/)

    - `wildcard` (boolean, optional).[docs.snusbase](https://docs.snusbase.com/)

    - `group_by` (boolean or string, optional; defaults `"db"`, can be disabled or set to another grouping key).[docs.snusbase](https://docs.snusbase.com/)

- **Top-level response fields**

    - `took` (number)

    - `size` (number)

    - `results` (object) – example uses single key `"HASHES"`.[docs.snusbase](https://docs.snusbase.com/)

- **Row object fields (example)**

    - Within `results.HASHES`:[docs.snusbase](https://docs.snusbase.com/)

        - `hash` (string)

        - `password` (string, plaintext)

- **Field presence**

    - For a hit: `took`, `size`, `results.HASHES` present, each element having both `hash` and `password` (derived from example).[docs.snusbase](https://docs.snusbase.com/)

- **Response variants**

    - **Successful hit** – 200 with `size >= 1` and at least one `{hash,password}` pair.[docs.snusbase](https://docs.snusbase.com/)

    - **Successful no-hit** – not specified; likely `size = 0` with empty `results` (inferred).

- **Errors**

    - Same global error semantics (`errors` array, HTTP status codes).[docs.snusbase](https://docs.snusbase.com/)

- **Important example excerpt**

    - json

        `{   "took": 0.102,  "size": 1,  "results": {    "HASHES": [      {        "hash": "482c811da5d5b4bc6d497ffa98491e38",        "password": "password123"      }    ]  } } ```[1]`


---

### `/tools/ip-whois` – IP WHOIS Lookup

- **Endpoint / method**

    - `POST https://api.snusbase.com/tools/ip-whois`[docs.snusbase](https://docs.snusbase.com/)

- **Purpose**

    - Provides WHOIS / geo-IP style enrichment (location, ASN, ISP, proxy/hosting/mobile flags) for IP addresses.[docs.snusbase](https://docs.snusbase.com/)

- **Auth / execution**

    - Requires `Auth` header and JSON body.[docs.snusbase](https://docs.snusbase.com/)

- **Supported entity types**

    - `ip` – passed as strings in `terms`.[docs.snusbase](https://docs.snusbase.com/)

- **Request body parameters**

    - `terms` (array[string], required) – list of IP addresses.[docs.snusbase](https://docs.snusbase.com/)

- **Top-level response fields**

    - `took` (number)

    - `size` (number)

    - `results` (object) – keyed by IP string, each value is an object with WHOIS / geo fields.[docs.snusbase](https://docs.snusbase.com/)

- **WHOIS row fields (example)**

    - `continent`, `continentCode`, `country`, `countryCode`, `region`, `regionName`, `city`, `zip`, `lat`, `lon`, `timezone`, `isp`, `org`, `as`, `asname`, `mobile`, `proxy`, `hosting`.[docs.snusbase](https://docs.snusbase.com/)

- **Response variants**

    - **Successful hit** – 200 with `size > 0` and one or more IP keys in `results`.[docs.snusbase](https://docs.snusbase.com/)

    - **No-hit** – not discussed; likely `size = 0` and/or missing entry for given IP (inferred).

- **Errors**

    - Standard HTTP codes with `errors` array on failure.[docs.snusbase](https://docs.snusbase.com/)

- **Important example excerpt**

    - json

        `{   "took": 6.4,  "size": 1,  "results": {    "12.34.56.78": {      "continent": "North America",      "continentCode": "NA",      "country": "United States",      "countryCode": "US",      "region": "OH",      "regionName": "Ohio",      "city": "Columbus",      "zip": "43215",      "lat": 39.9612,      "lon": -82.9988,      "timezone": "America/New_York",      "isp": "AT&T Enterprises, LLC",      "org": "AT&T Enterprises, LLC",      "as": "AS7018 AT&T Enterprises, LLC",      "asname": "ATT-INTERNET4",      "mobile": false,      "proxy": false,      "hosting": false    }  } } ```[1]`


---

### Error Handling & Rate Limits (Global)

- **HTTP semantics**

    - 200 OK for success; 400 Bad Request (invalid input), 401 Unauthorized (invalid/expired/missing API key), 429 Too Many Requests (rate limit exceeded).[docs.snusbase](https://docs.snusbase.com/)

    - Errors described in `errors` array in response body; safe to show to end users (exact schema not specified).[docs.snusbase](https://docs.snusbase.com/)

- **Rate limits**

    - `/data/search`: 2,048 requests every 12 hours per key.[docs.snusbase](https://docs.snusbase.com/)

    - `/tools/combo-lookup`: 4,096 requests every 12 hours per key.[docs.snusbase](https://docs.snusbase.com/)

    - All other endpoints (including `/tools/hash-lookup`, `/tools/ip-whois`, `/data/stats`): 256 requests every 2 minutes.[docs.snusbase](https://docs.snusbase.com/)

    - Responses include headers: `X-Rate-Limit`, `X-Rate-Limit-Remaining`, `X-Rate-Limit-Reset` (seconds to window reset).[docs.snusbase](https://docs.snusbase.com/)

- **Provider role and data nature**

    - Snusbase indexes public and semi‑public breach dumps, credential stuffing lists, stealer logs, and court documents, and “displays each result in full” with minimal modification.[snusbase](https://snusbase.com/)

    - They explicitly maintain “an extensive database of previously cracked password hashes,” which underpins `/tools/hash-lookup` and the password fields returned.[snusbase](https://snusbase.com/)


## Module Mapping Table (Credential Exposure)

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|credential_exposure|signal_producer|data_search|`POST /data/search`|direct_signal_input|email, username|Only treat as signal when HTTP 200, `size > 0`, and at least one row in `results` maps to the queried identity (e.g. `row.email == input_email` when `types` includes `"email"`). Ignore responses with `size == 0` or any non‑200/4xx error. (derived)|[https://docs.snusbase.com](https://docs.snusbase.com/)[docs.snusbase](https://docs.snusbase.com/)|Primary breach source: per‑database rows contain email/username, IP, hashes, sometimes plaintext passwords/stealer‑log data. Datasets and columns vary per table as defined by `/data/stats.tables` (documented).[docs.snusbase](https://docs.snusbase.com/)|
|credential_exposure|signal_producer|combo_lookup|`POST /tools/combo-lookup`|direct_signal_input|email (as username)|Invoke when searching for an email or username and `types` includes `"username"`. Treat as signal when 200 and `size > 0` and at least one `results[db][i].username` equals the queried account identifier. Ignore `size == 0`. (derived from examples)|[https://docs.snusbase.com](https://docs.snusbase.com/)[docs.snusbase](https://docs.snusbase.com/)|Returns plaintext username/password pairs from “combolist” dumps, representing direct credential exposure as used in credential‑stuffing attacks (documented).[docs.snusbase](https://docs.snusbase.com/)|
|credential_exposure|signal_producer|hash_lookup|`POST /tools/hash-lookup`|enrichment_only|hash, password|Use to enrich existing breach hits that include a `hash` value (e.g. from `/data/search`), or to normalize hash→password mappings supplied from other modules. Do **not** emit standalone signals on hash lookup alone for this module in v1. (design choice)|[https://docs.snusbase.com](https://docs.snusbase.com/)[docs.snusbase](https://docs.snusbase.com/)|Provides cracked passwords `{hash,password}` from Snusbase’s cracked password DB (documented) Use primarily to add plaintext to existing breach findings and escalate severity, not to generate separate alerts initially.|
|credential_exposure|signal_producer|ip_whois|`POST /tools/ip-whois`|enrichment_only|ip|Only call when you have an IP from a breach row (e.g. `lastip` from `/data/search`) and want geographic/ASN/proxy context. Never create a credential exposure signal purely from WHOIS data. (derived)|[https://docs.snusbase.com](https://docs.snusbase.com/)[docs.snusbase](https://docs.snusbase.com/)|Pure enrichment: location, ISP, ASN, proxy/hosting flags for IPs, no credential context by itself.[docs.snusbase](https://docs.snusbase.com/)|
|credential_exposure|signal_producer|stats|`GET /data/stats`|utility_only|n/a|Use at client / provider‑init time to cache table names, column lists, and feature flags (`view_more`, `combo_lookup`). Not used in rule‑level signal generation. (documented use as metadata)|[https://docs.snusbase.com](https://docs.snusbase.com/)[docs.snusbase](https://docs.snusbase.com/)|Helpful for understanding which tables contain `password` vs only `hash`, and for optional dataset‑specific tuning. Not entity‑scoped.|

## Signal Contract Table

### Standalone module‑level signals

Only `/data/search` and `/tools/combo-lookup` should emit signals for the `credential_exposure` module in v1. `/tools/hash-lookup` and `/tools/ip-whois` are enrichment-only; `/data/stats` is utility-only.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|credential_exposure|credential_exposure|snusbase|data_search|credential_breach_found|account_security|high|yes|Default **high** for any hit where the queried identity (email/username) appears in at least one Snusbase breach dataset row. Escalate to **critical** if the row (or all‑columns view for that table) includes a `password` column that appears to hold plaintext (e.g. STEALERLOGS tables) or later enrichment via hash/ combo lookup recovers plaintext. De‑escalate to **medium** if no credential material is present (e.g. only name/PII without password/hash). (derived from fields and dataset naming)|email|true_finding|HTTP 200; response JSON has numeric `size > 0`; `results` object contains at least one table key; within some `results[table][i]` row, `email` or `username` equals the looked‑up identity value that was sent in `terms` with the matching `types` entry. Ignore responses with `size == 0` or with no row matching the input identity. (derived from documented request/response examples)|For each matching row: table key (dataset ID), `username`, `email`, `lastip`, `hash`, `salt`, `uid`, `created`, `updated`, plus any additional columns returned when `tables` is specified (treated generically as a map). Also top‑level `took`, `size`. (row fields/table keys documented, row membership as evidence inferred)[docs.snusbase](https://docs.snusbase.com/)|Additional non‑credential columns from the same row (e.g. `host`, `_domain`, `name`, others as exposed via `/data/stats.tables`); grouping key (e.g. `_domain` or `"db"`); optionally IP WHOIS enrichment for `lastip` (continent, country, ASN, proxy/hosting/mobile flags) when `/tools/ip-whois` is invoked. (table schema documented; WHOIS enrichment documented)[docs.snusbase](https://docs.snusbase.com/)|`Credential for {{entity}} found in Snusbase breach dataset {{dataset}} (hash and/or password exposed).`|derived|[https://docs.snusbase.com](https://docs.snusbase.com/)[docs.snusbase](https://docs.snusbase.com/)|Combines any table type (forum breaches, stealer logs, etc.). Dataset names like `0001_STEALERLOGS_NA_121M_MALWARE_2023` indicate stealer‑log origin; treat those as higher‑risk (critical) when a `password` column is present. Dataset‑specific logic for age/quality should be added later using `created`/`updated` and table metadata. (stealer log table example documented)[docs.snusbase](https://docs.snusbase.com/)|
|credential_exposure|credential_exposure|snusbase|combo_lookup|credential_breach_found|account_security|critical|no|n/a – always **critical** when plaintext username/password is returned for the queried account, as this directly satisfies “direct credential exposure, plaintext passwords” in the severity guide.|email|true_finding|HTTP 200; response JSON has `size > 0`; within some `results[table][i]` row, `username` equals the queried identifier (typically an email used as username) from `terms` when `types` includes `"username"`. Ignore responses with `size == 0` or mismatched usernames. (derived from documented example where email is used as username)|For each matching row: table key (combolist dataset ID such as `0007_COLLECTION3_COMBOLIST_300M_2019`), `username`, `password` (plaintext), plus top‑level `took`, `size`. (documented)[docs.snusbase](https://docs.snusbase.com/)|Optionally: inferred password reuse flags (from correlation layer comparing Snusbase password against internal credential store), but those are not directly from Snusbase. Dataset name and any parsed attributes (e.g. year in dataset name) may be stored for later age/tier tuning (dataset naming pattern inferred from examples).[docs.snusbase](https://docs.snusbase.com/)|`Plaintext credential for {{entity}} found in Snusbase combolist dataset {{dataset}} (username/password pair exposed).`|documented|[https://docs.snusbase.com](https://docs.snusbase.com/)[docs.snusbase](https://docs.snusbase.com/)|Combolist results are highly actionable for credential‑stuffing risk. No timestamps are provided per row in the example; dataset names carry a year like `2019` which can be parsed later for staleness modelling (inferred). Avoid generating separate Zima signal types per dataset; treat all combolists as one “plaintext credential exposure” source.|

- **Evidence status notes**

    - For `/data/search`, the existence and names of fields are documented; the _use_ of `size` and row matching as signal gating is **derived/inferred** from examples.[docs.snusbase](https://docs.snusbase.com/)

    - For `/tools/combo-lookup`, the presence of plaintext `password` is explicitly shown, so its criticality is **documented** for “direct credential exposure”.[docs.snusbase](https://docs.snusbase.com/)


## Severity Rules

### `credential_breach_found` via `/data/search`

- **Base severity: high**

    - Any confirmed Snusbase hit that ties the queried identity to a breach row is at least a “confirmed breach / exposed credential context,” aligning with **high** in your calibration (even if only a hash is present, the password may be crackable or already cracked in Snusbase’s separate DB).

- **Critical escalation**

    - Escalate to **critical** when:

        - The breach row includes a `password` column that is plausibly plaintext (e.g. STEALERLOGS tables that list `password` alongside `email`, `username`, `host`, `_domain`), or[docs.snusbase](https://docs.snusbase.com/)

        - Follow‑up `/tools/hash-lookup` or `/tools/combo-lookup` returns a plaintext password for a hash or username that came from the `/data/search` hit.[docs.snusbase](https://docs.snusbase.com/)

    - This directly matches “direct credential exposure, plaintext passwords, active stealer logs” under **critical** in your guide.

- **Medium downgrade**

    - If a `/data/search` row has no `hash` or `password` column (e.g. just PII like name, username without password), treat severity as **medium**, consistent with “unverified breach / passive threat indicators / reputation degradation.”

- **First‑pass assessment**

    - Based on official docs and Snusbase marketing (full breach data including hashes and sometimes passwords), a **high** baseline for “any hit” with **critical** for plaintext/stealer‑log cases is a reasonable starting point.


### `credential_breach_found` via `/tools/combo-lookup`

- **Severity: critical**

    - Results are plaintext username/password pairs from combolists, which satisfy “direct credential exposure, plaintext passwords” and are widely used for credential stuffing.

    - No documented per‑row timestamps; absent additional staleness logic, treat all positives as **critical** in v1, with the option to downgrade extremely old sets once you layer in dataset metadata.

- **First‑pass assessment**

    - Treating combo‑lookup hits as **critical** is strongly supported by the nature of the data; this matches and slightly sharpens your generic calibration (direct plaintext credentials).


## Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|credential_exposure|`credential_breach_found` via `/data/search`|Snusbase aggregates many third‑party breach datasets and publishes full records (including hashes, sometimes passwords) with minimal modification, plus a cracked hash database. Reliability is high that “a matching record exists in at least one indexed dataset”, but underlying source quality varies by breach.|Use `created` / `updated` row timestamps where present to estimate breach age; dataset names often embed year (`..._2019`, `..._2023`), which can be parsed but is not formally documented.[docs.snusbase](https://docs.snusbase.com/) Treat age-based severity adjustments as experimental until validated.|For sensitive actions (forced password reset, account lockout), corroborate with at least one of: another breach provider, local login telemetry (failed logins from unusual IPs), or user confirmation. Use multiple hits across unrelated datasets as stronger evidence of ongoing password reuse.|Empirically bucket datasets by age and type (e.g. stealer logs vs forum breaches) and measure incident outcomes. Tune severity thresholds (critical vs high vs medium) per dataset group. Validate whether `created`/`updated` reliably reflect breach/ingestion time vs record update time.|
|credential_exposure|`credential_breach_found` via `/tools/combo-lookup`|Plaintext username/password pairs are strong evidence of real‑world credential use, but combolists may be noisy (reused or fake accounts). Still, Snusbase is regarded as a serious OSINT/breach source by practitioners.|No explicit timestamps per combo; dataset IDs encode some metadata (e.g. `COLLECTION3_COMBOLIST_300M_2019`), implying year of circulation.[docs.snusbase](https://docs.snusbase.com/) Password reuse over long periods is common, but impact may decline with age; treat all as critical initially then refine based on observed reuse rates.|Corroborate by checking whether the same username/password appears in `/data/search` breach rows or in other credential‑leak providers; also test against internal auth logs (failed/successful logins) where policy allows. Multiple combolist appearances for the same pair should increase confidence of real use.|Build a scoring model that incorporates number of combo hits, diversity of datasets, and any internal validation (e.g. password similarity to real account password where available) to calibrate confidence laddering within the fixed `critical` severity bucket (for triage and prioritization heuristics).|
|credential_exposure|Hash enrichment via `/tools/hash-lookup`|Cracked hash database is explicitly maintained by Snusbase; where it returns a plaintext password for a known hash, confidence in the value is high, though hash origin may be from old breaches.|No explicit age metadata on individual cracked entries. Treat them as at least as old as their earliest source dataset; condition age via the originating `/data/search` dataset’s metadata (name, timestamps).|Only raise severity from high→critical when a cracked password matches the same account in at least one breach row; avoid creating standalone hash‑only alerts. Optionally corroborate by checking if the cracked password matches current internal credentials (under strict security controls).|Log which datasets and hash types most frequently yield cracked passwords and how often they map to still‑valid credentials. Use this to decide if some old hash sets should no longer escalate to critical (e.g. if real‑world password reuse from those becomes rare).|
|credential_exposure|IP enrichment via `/tools/ip-whois`|WHOIS/geo data is largely commodity and not core to credential evidence. Snusbase appears to proxy an IP intelligence service, and the example fields match typical IP geo APIs.[docs.snusbase](https://docs.snusbase.com/) Reliability is sufficient for enrichment but not for standalone decisions.|IP geo/ASN/proxy characteristics can change over time; treat WHOIS results as point‑in‑time hints only. Long‑term storage is fine for investigation, but do not build static allow/deny lists solely from this data.|Only use IP WHOIS to contextualize breach IPs (e.g. last observed login country, likely ISP). Where possible, corroborate with other IP intelligence providers if you’re making high‑impact decisions (e.g. terminating unusual sessions).|Decide whether you want to standardize on a single IP intelligence provider; if you do, route Snusbase’s IPs to that canonical service instead of relying on `/tools/ip-whois`. Otherwise, treat this endpoint as an optional, low‑priority enrichment path.|

## Provider Summary

### Strongest signal types

- **Direct breach hits via `/data/search`**: link identities (primarily emails/usernames) to specific breach datasets, with per‑dataset columns such as `hash`, `salt`, `lastip`, and possibly plaintext `password` in some tables (e.g. stealer logs).[docs.snusbase](https://docs.snusbase.com/)

- **Plaintext credentials via `/tools/combo-lookup`**: provide username/password pairs from large combolists, ideal for identifying direct credential exposure and credential‑stuffing attacks.

- **Cracked hashes via `/tools/hash-lookup`**: convert hashes into plaintext passwords, allowing escalation of hashed-only breaches into confirmed plaintext credentials.


### What Snusbase should _not_ be used for (within this module)

- **Do not treat `/data/stats` as a signal source**: it is metadata only (rows, tables, features), useful for configuration and tuning, not security findings.[docs.snusbase](https://docs.snusbase.com/)

- **Do not create standalone credential_exposure signals from `/tools/ip-whois`**: WHOIS/geo/ASN/proxy flags are pure enrichment and should not drive alerts by themselves in this module.[docs.snusbase](https://docs.snusbase.com/)

- **Do not treat every `password` field as definitely plaintext unless context supports it**: for `/data/search`, column presence is documented but the representation (hash vs plaintext) depends on dataset; assume plaintext only where stealer/combolist context is clear (e.g. STEALERLOGS tables or explicit combolist/hash‑lookup outputs)


### API/auth/rate-limit/licensing cautions

- **Auth handling**

    - Activation codes must be passed via `Auth` header (`Auth: sb[...]`), and Snusbase warns that misuse can result in termination; keys must never be exposed in client‑side code.[docs.snusbase](https://docs.snusbase.com/)

- **Rate limiting**

    - `/data/search`: 2,048 requests per 12h; `/tools/combo-lookup`: 4,096 requests per 12h; all others: 256 per 2 minutes.[docs.snusbase](https://docs.snusbase.com/)

    - Your client should respect `X-Rate-Limit`, `X-Rate-Limit-Remaining`, and `X-Rate-Limit-Reset` headers and apply backoff; consider central per‑provider budgeting in Zima.

- **Licensing / ToS**

    - Snusbase is a paid service (“API Included… free of charge to any paying member up to 2048 requests per day”).[snusbase](https://snusbase.com/)

    - They explicitly state users are responsible for their key and usage, so Zima should centralize key storage and access control.


### Provider role in Zima’s current stage

- **Overall classification**

    - Snusbase should be treated as a **signal‑producing breach provider** for the `credential_exposure` module, with `/data/search` and `/tools/combo-lookup` as primary signal inputs, and `/tools/hash-lookup` and `/tools/ip-whois` as enrichment‑only.

- **Build prioritization**

    - For a Tier‑1/core build:

        - Implement `/data/search` → `credential_breach_found` with conditional severity rules (hashed vs plaintext/stealer log).

        - Implement `/tools/combo-lookup` → `credential_breach_found` (always critical).

        - Implement `/tools/hash-lookup` as enrichment that can flip `/data/search` hits from high→critical when plaintext is recovered.

        - Treat `/tools/ip-whois` as optional enrichment only, wired through a generic IP‑intel abstraction if you have one.


## Implementation Notes

- **Field paths to preserve**

    - `/data/search`: entire `results` object including table keys and full row maps; `took`, `size`.[docs.snusbase](https://docs.snusbase.com/)

    - `/tools/combo-lookup`: `results` (table→`[{username,password}]`), `took`, `size`.[docs.snusbase](https://docs.snusbase.com/)

    - `/tools/hash-lookup`: `results.HASHES[]` (`hash`, `password`), `took`, `size`.[docs.snusbase](https://docs.snusbase.com/)

    - `/tools/ip-whois`: `results[ip]` object with geo/ASN/proxy fields.[docs.snusbase](https://docs.snusbase.com/)

    - `/data/stats`: `tables`, `features.view_more`, `features.combo_lookup` (for pre‑computing which tables have `password` columns).

- **Null / empty / no‑hit behavior**

    - Treat any 200 response with `size == 0` (or empty `results`) as “no finding”; mapper should return no signal for the current entity (behavior inferred from schema, as no explicit “no‑hit” example is given).[docs.snusbase](https://docs.snusbase.com/)

    - Treat any 4xx/5xx or malformed JSON as upstream error; surface to logs/metrics but do not generate signals.

- **Rate limits & billing**

    - Implement client‑side rate‑limit handling using the documented headers; consider per‑provider queueing to avoid 429s.[docs.snusbase](https://docs.snusbase.com/)

    - Since API quotas are tied to paying accounts, centralize keys and rate tracking in the provider client, not in individual modules.

- **Deduplication keys / identifiers**

    - Candidate natural identifiers for dedupe:

        - `(provider="snusbase", table_name, uid)` when `uid` is present in `/data/search` rows (inferred from example).[docs.snusbase](https://docs.snusbase.com/)

        - Fallback: `(provider, table_name, email/username, hash)` when `uid` is absent.

        - For combolists: `(provider, table_name, username, password)` to avoid repeating identical combos from the same dataset.

    - Correlation layer should further dedupe across providers based on “account identity + password similarity”.

- **Client vs mapper vs correlation responsibilities**

    - **Provider client**

        - Manage authentication, rate limits, error normalization.

        - Optionally expose a “search_breaches(email)” and “lookup_combos(username)” abstraction that hides raw endpoint details.

        - Cache `/data/stats` to understand which tables have `password` columns and which are combolist or stealer logs.

    - **Module mapper (`credential_exposure`)**

        - Implement trigger logic and field extraction for `credential_breach_found` from `/data/search` and `/tools/combo-lookup`.

        - Decide severity per rules above (including re‑running mapping after enrichment updates).

        - Map Snusbase JSON to Zima normalized evidence/enrichment fields without losing raw per‑row maps.

    - **Correlation layer**

        - Combine Snusbase signals with other breach providers and internal telemetry.

        - Handle higher‑order logic (e.g. password reuse across multiple services, user risk scoring, suppression of extremely old/low‑impact breaches).


## Structured JSON

json

`{   "provider": "snusbase",  "provider_category": "breach",  "provider_role": "signal_producer",  "module_mappings": [    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "data_search",      "endpoint_or_artifact": "POST https://api.snusbase.com/data/search",      "classification": "direct_signal_input",      "entity_types": ["email", "username"],      "gating_logic": "HTTP 200, size > 0, and at least one row in results has email or username equal to the queried identity. Ignore size == 0 or error responses.",      "citation_refs": ["https://docs.snusbase.com"],      "notes": "Primary breach search endpoint; per-table schemas vary. Used to detect that an identity appears in one or more Snusbase datasets."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "combo_lookup",      "endpoint_or_artifact": "POST https://api.snusbase.com/tools/combo-lookup",      "classification": "direct_signal_input",      "entity_types": ["email"],      "gating_logic": "HTTP 200, size > 0, and at least one row in results has username equal to the queried account (typically email).",      "citation_refs": ["https://docs.snusbase.com"],      "notes": "Returns plaintext username/password pairs from combolist datasets; direct credential exposure."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "hash_lookup",      "endpoint_or_artifact": "POST https://api.snusbase.com/tools/hash-lookup",      "classification": "enrichment_only",      "entity_types": ["hash", "password"],      "gating_logic": "Invoke when enriching existing breach hits that include hashes or when normalizing external hash/password signals; do not create standalone signals in v1.",      "citation_refs": ["https://docs.snusbase.com"],      "notes": "Provides cracked hash -> password mappings; used to escalate hashed-only findings to plaintext exposure."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "ip_whois",      "endpoint_or_artifact": "POST https://api.snusbase.com/tools/ip-whois",      "classification": "enrichment_only",      "entity_types": ["ip"],      "gating_logic": "Only called when breach rows contain IPs (e.g. lastip) and enrichment is needed. Never generates standalone credential exposure signals.",      "citation_refs": ["https://docs.snusbase.com"],      "notes": "WHOIS/geo/ASN/proxy enrichment for IPs; network context only."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "stats",      "endpoint_or_artifact": "GET https://api.snusbase.com/data/stats",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Used at client init or periodic refresh to understand datasets and features; not per-entity.",      "citation_refs": ["https://docs.snusbase.com"],      "notes": "Global metadata: total rows, table names and columns, feature flags for view_more and combo_lookup."    }  ],  "signal_contracts": [    {      "module": "credential_exposure",      "source": "credential_exposure",      "provider": "snusbase",      "provider_method": "data_search",      "signal_type": "credential_breach_found",      "category": "account_security",      "severity": "high",      "severity_is_conditional": "yes",      "conditional_rule": "Default high. Escalate to critical when a matching row (or its all-columns variant) includes a password column that appears to be plaintext (e.g. stealer-log datasets) or when hash/combo enrichment recovers plaintext; downgrade to medium if the row has no hash or password fields.",      "entity_type": "email",      "finding_kind": "true_finding",      "trigger_condition": "HTTP 200 response; JSON body has numeric size > 0; results contains at least one table key; within some results[table][i], email or username equals the input identity value supplied in terms with matching types.",      "evidence_fields": [        "results[table][i].username",        "results[table][i].email",        "results[table][i].lastip",        "results[table][i].hash",        "results[table][i].salt",        "results[table][i].uid",        "results[table][i].created",        "results[table][i].updated",        "table (results map key)",        "took",        "size"      ],      "enrichment_fields": [        "all additional columns returned for the table via /data/search and /data/stats",        "group_by key (e.g. db, _domain)",        "optional IP WHOIS enrichment for lastip"      ],      "summary_template": "Credential for {{entity}} found in Snusbase breach dataset {{dataset}} (hash and/or password exposed).",      "evidence_status": "derived",      "citation_refs": ["https://docs.snusbase.com"],      "notes": "Covers all Snusbase breach datasets. Per-table schemas from /data/stats define whether password columns exist; stealer-log and similar tables should be treated as higher risk when password is present."    },    {      "module": "credential_exposure",      "source": "credential_exposure",      "provider": "snusbase",      "provider_method": "combo_lookup",      "signal_type": "credential_breach_found",      "category": "account_security",      "severity": "critical",      "severity_is_conditional": "no",      "conditional_rule": "",      "entity_type": "email",      "finding_kind": "true_finding",      "trigger_condition": "HTTP 200 response; JSON body has size > 0; within some results[table][i], username equals the queried identifier (typically an email) supplied in terms when types includes \"username\".",      "evidence_fields": [        "results[table][i].username",        "results[table][i].password",        "table (results map key)",        "took",        "size"      ],      "enrichment_fields": [        "dataset name attributes (e.g. collection label and apparent year embedded in table name)",        "correlation-layer password reuse flags (not directly from Snusbase)"      ],      "summary_template": "Plaintext credential for {{entity}} found in Snusbase combolist dataset {{dataset}} (username/password pair exposed).",      "evidence_status": "documented",      "citation_refs": ["https://docs.snusbase.com"],      "notes": "Direct plaintext exposure from combolist datasets; strong indicator of credential-stuffing risk. Dataset names include apparent year tags (e.g. 2019) that can later be used for age scoring."    }  ],  "confidence_guidance": [    {      "module": "credential_exposure",      "signal_type_or_use_case": "credential_breach_found via /data/search",      "source_reliability": "High that a matching record exists in at least one indexed breach dataset, but dataset quality and provenance vary; Snusbase indexes many leaked databases and displays full records with minimal modification.",      "freshness_considerations": "Use created/updated timestamps and table naming patterns to estimate age; no explicit freshness SLA is documented. Older datasets may still matter due to password reuse.",      "corroboration_rules": "For sensitive actions, corroborate with at least one other breach provider or internal telemetry (e.g. unusual login attempts, user confirmation). Multiple independent datasets for the same identity increase confidence.",      "calibration_todo": "Empirically study incident outcomes per dataset family (forum vs stealer logs vs others) and age buckets to tune severity mapping and de-prioritize very old, low-impact breaches."    },    {      "module": "credential_exposure",      "signal_type_or_use_case": "credential_breach_found via /tools/combo-lookup",      "source_reliability": "Plaintext username/password pairs are strong evidence but combolists may include noise. Snusbase is widely used for OSINT and pentesting, suggesting generally good fidelity.",      "freshness_considerations": "No per-row timestamps; use apparent year from dataset names as a proxy. Password reuse across years is common, but impact likely declines with age.",      "corroboration_rules": "Prefer to corroborate via other providers or internal auth telemetry when performing disruptive actions. Multiple combolist appearances of the same pair should increase confidence.",      "calibration_todo": "Build metrics around how often Snusbase combolist passwords match current account passwords or lead to successful credential-stuffing detections to refine prioritization within the critical bucket."    },    {      "module": "credential_exposure",      "signal_type_or_use_case": "hash enrichment via /tools/hash-lookup",      "source_reliability": "Where a password is returned for a hash, confidence that the mapping is correct is high given Snusbase’s explicit cracked-hash DB.",      "freshness_considerations": "Age is inherited from source breaches; no explicit age metadata per crack. Consider treating very old hashes differently once you have data.",      "corroboration_rules": "Use hash-lookup to escalate existing breach findings rather than generate standalone signals. Optionally verify whether cracked passwords still match internal credentials under controlled conditions.",      "calibration_todo": "Track how often cracked passwords from specific datasets are still valid; adjust criticality for very old hashes accordingly."    },    {      "module": "credential_exposure",      "signal_type_or_use_case": "IP enrichment via /tools/ip-whois",      "source_reliability": "WHOIS/geo-IP data is generally reliable but not security-critical by itself; Snusbase’s responses mirror common IP info APIs.",      "freshness_considerations": "IP allocation and hosting/proxy status change over time; treat as point-in-time enrichment only.",      "corroboration_rules": "Use only to contextualize breach IPs (e.g. country, ISP, proxy flags) and never as a standalone credential exposure signal.",      "calibration_todo": "Decide whether Snusbase WHOIS should be your primary IP enrichment or if IPs should be normalized through a separate, dedicated IP-intel provider."    }  ] }`
