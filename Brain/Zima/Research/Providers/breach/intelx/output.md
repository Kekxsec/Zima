---
title: "output / breach / intelx"
aliases: ["intelx output", "intelx signal registry"]
tags: [zima, research, outputs, signal-registry, breach, intelx, graph_exclude]
type: provider_research_output
provider: intelx
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: intelx.md
obsidianUIMode: preview
---
# IntelX (intelx.io) Integration for Zima: Breach, Dark Web Identity, and Stealer Log Use Cases

## 1. API Surface Appendix

### 1.1 Authentication, Instances, Limits (Search API)

- **Auth mechanism (Search API):**
  - API key is a UUID, passed preferably via `x-key` HTTP header or alternatively as `&k=[key]` URL parameter.[1]
  - Key is tied to organization; unauthorized or bucket‑denied access returns HTTP 401, lack of credits returns HTTP 402.[1]
- **Instances:**
  - `public.intelx.io` – non‑registered users.
  - `free.intelx.io` – free signed‑up users.
  - `2.intelx.io` – paid users.[2]
- **General limits (Search API):**
  - Recommended max 1 request/second per key unless license states otherwise.[1]
  - Example public key limits (legacy but indicative): searches 50/day, phonebook lookups 20/day, max results per search 40, preview only first 1000 chars for some buckets.[1]
  - Current documented limits for `/intelligent/search` (Search API): max results per bucket 200 (free) / 1000 (paid); max concurrent searches 5 (free) / 10 (paid); search timeout 1–2 minutes; results kept 3–10 minutes.[3]

### 1.2 Authentication, Instances, Limits (Leaks API / Identity Portal)

- **Auth mechanism (Leaks API):**
  - API URL `https://3.intelx.io/`.[4]
  - Same `x-key` header or `&k=` parameter; key must have “Identity Portal” license; otherwise HTTP 401.[4]
- **Search limits (Leaks API):**
  - For `/live/search/internal` (used by Identity Portal & Leaks API): max results per bucket 10 000; max concurrent searches 2; search timeout 5 minutes; results kept 10 minutes.[3]
- **ZIP export limits (notably for Stealer Logs):**
  - For `identity.intelx.io (Stealer Logs)`, export ZIP limits: max uncompressed data 100 MB, max 200 files per export, max file size 20 MB, internal file fetch timeout 4 seconds (files not fetched in time appear as dummy “[timeout]” files).[3]

### 1.3 Buckets and Data Categories

Search and Leaks APIs use a **bucket** field to indicate data category.[4][1]

Key buckets relevant to breach / dark web identity use cases:[5][4]

- `leaks.public.general` – public data leaks (e.g., Collection 1, Dropbox dumps).
- `leaks.private.general` – private data leaks.
- `pastes` – paste sites.
- `darknet.tor` – Tor hidden services.
- `darknet.i2p` – I2P eepsites.
- `whois` – WHOIS data.
- `dumpster` and `dumpster.*` – miscellaneous high‑value or SSN‑related web data.
- Various `web.public.*` buckets – public web snapshots (KP, RU, DE, COM, etc.).

For Identity Portal marketing, categories include Paste sites, Darknet, Wikileaks/Cryptome, Data Leaks, Whois Data, Dumpster, and Public Web, aligning with buckets above.[5]

### 1.4 /intelligent/search (Search API)

- **Endpoint:** `POST /intelligent/search`.[1]
- **Purpose:** Submit a selector‑based search across buckets; returns a **Search ID** used to retrieve results.[1]
- **Supported selector types (term field):**
  - Strong selectors only (generic terms rejected with `softselectorwarning=true`).[1]
  - Email address, domain (incl. wildcards like `*.example.com`), URL, IPv4/IPv6, CIDR, phone number, Bitcoin address, MAC address, IPFS hash, UUID, Storage ID, System ID, Simhash, credit card number, IBAN.[5][1]
- **Auth / execution:** Requires Search API key on one of the instances (`public`, `free`, `2`); request limits per section 1.1.[2][3][1]
- **Request body (IntelligentSearchRequest, documented):**[1]
  - `term` (string, required) – selector.
  - `buckets` (array<string>) – specific buckets to search; empty means all allowed buckets.
  - `lookuplevel` (int) – should be 0.
  - `maxresults` (int) – max results **per bucket**.
  - `timeout` (int, seconds) – 0 for default.
  - `datefrom`, `dateto` (string, optional) – both must be supplied if filtering by date.
  - `sort` (int) – 0 no sort; 1 X‑Score ascending; 2 X‑Score descending; 3 date ascending; 4 date descending.[1]
  - `media` (int) – optional filter by media type; 0 = not set; see media enum below.[1]
  - `terminate` (array<UUID>) – IDs of previous searches (normal or phonebook) to terminate when starting this one.[1]
- **Response (IntelligentSearchRequestResponse, documented):**[1]
  - `id` (UUID, always present on success) – Search ID.
  - `softselectorwarning` (bool) – true if the selector is considered “soft” (generic term).
  - `status` (int) – `0` success, `1` invalid term, `2` max concurrent searches reached.[1]
- **Status / errors:**
  - 200 with JSON on success.
  - 400 invalid JSON or missing parameters.
  - 401 unauthorized (including bucket‑level denial).
  - 402 payment required when credits exhausted.[1]
- **No‑hit behavior:** A syntactically valid search that finds no results still returns `status:0` and a Search ID; the later `/intelligent/search/result` call will indicate no results via its own `status` and/or empty `records`.

### 1.5 /intelligent/search/result (Search API)

- **Endpoint:** `GET /intelligent/search/result?id=[UUID]&offset=[optional]&limit=[optional]&previewlines=[optional]`.[1]
- **Purpose:** Retrieve search results (items) for a given Search ID.[1]
- **Auth / execution:** Same as `/intelligent/search` (Search API key, instance‑specific limits).[3][1]
- **Response (IntelligentSearchResult, documented):**
  - Top‑level:
    - `records` (array<Item>) – the actual results; may be empty.[1]
    - `status` (int):
      - `0` – success with results.
      - `1` – no future results; search terminated; **may still include final records**.
      - `2` – search ID not found.
      - `3` – no results yet, but keep trying.[1]
  - Each **Item** has fields (most appear in example):[1]
    - `systemid` (UUID, required) – unique identifier of item.
    - `storageid` (string, required if `instore=true`) – storage identifier used with `/file/*` functions.
    - `instore` (bool, required) – whether data is stored and retrievable.
    - `size` (int) – size in bytes of data.
    - `accesslevel` (int) – 4 indicates only preview available for the API key.[1]
    - `type` (int) – low‑level data type enum:
      - `0` binary/unspecified.
      - `1` plain text.
      - `2` picture.
      - `3` video.
      - `4` audio.
      - `5` document (office/PDF etc.).
      - `6` executable.
      - `7` container file (ZIP/RAR/TAR etc.).
      - `1001` user.
      - `1002` leak.
      - `1004` URL.
      - `1005` forum.[1]
    - `media` (int) – high‑level data type enum (paste, forum, website copy, PDF, text, container, etc.).[1]
    - `added` (ISO 8601) – when item was indexed.
    - `date` (ISO 8601) – original record date if known, else equals `added`.[1]
    - `name` (string) – title or filename.
    - `description` (string) – typically unused.
    - `xscore` (int 0–100) – relevance score.[1]
    - `simhash` (int) – similarity hash.
    - `bucket` (string) – data category bucket (see 1.3).[1]
    - `keyvalues` (nullable) – not used.
    - `tags` (nullable) – additional information; in Leaks API examples includes `class` / `value` pairs (e.g., `{"class":4,"value":"email"}`).[4][1]
    - `relations` (nullable) – identifiers of related items; in example, list of `target` + `relation` numeric code.[1]
    - Additional human‑translated fields: `accesslevelh`, `mediah`, `simhashh`, `typeh`, `tagsh` (string/nullable); these are for UI and are not necessary for machine logic.[1]
    - `friends` (array<ItemFriend>) – linked items (e.g., paste user plus paste document); each has nested `inline` with the same item structure.[1]
    - `randomid` (UUID) – random identifier.[1]
- **Hit / no‑hit behavior:**
  - **No more results:** `status:1` with possibly empty `records`.[1]
  - **Search still running:** `status:3` with empty `records`, client should poll until `status` is 0 or 1.[1]
  - **Invalid search:** `status:2` or HTTP 400.

### 1.6 /intelligent/search/terminate (Search API)

- **Endpoint:** `GET /intelligent/search/terminate?id=[UUID]`.[1]
- **Purpose:** Terminate an active search (freeing resources); no effect if already terminated.[1]
- **Response:** 200 with empty body on success.[1]
- **Use in Zima:** Utility‑only; no direct security semantics.

### 1.7 /intelligent/search/export (Search API)

- **Endpoint:** `GET /intelligent/search/export?id=[search id]&f=[format]&l=[optional limit]`.[6]
- **Purpose:** Export search results as CSV summary or ZIP archive containing CSV + data files.[6]
- **Parameters:**
  - `id` (required) – Search ID from `/intelligent/search`.
  - `f` (required) – format: `0` CSV summary; `1` ZIP containing `Info.csv` + binary files `[systemid].bin` (subject to export limits).[7][6]
  - `l` (optional) – result limit, default 1000, with hard cap.[6]
- **Response:**
  - 200 with file payload and `Content-Disposition` suggesting filename like `Search [Date].csv`.[6]
  - 204 if Search ID not found (no body).
  - 400 invalid/missing parameters.[6]
- **CSV columns:** `Name`, `Date`, `Bucket`, `Media`, `Content Type`, `Size`, `System ID`.[6]
- **Use in Zima:** Bulk export / reporting; potentially utility for offline enrichment.

### 1.8 /phonebook/search (Search API)

- **Endpoint:** `POST /phonebook/search`.[6][1]
- **Purpose:** Start a “phonebook” search to enumerate selectors (domains, emails, URLs) derived from data such as WHOIS, leaks, and other structured sources; used by phonebook.cz.[8][6]
- **Request body (IntelligentSearchRequest subset, plus `target`):**[6][1]
  - Reuses `term`, `maxresults`, `terminate`, `timeout`, etc., similar to `/intelligent/search`.
  - `target` (int) – output selector type:
    - `1` domain names.
    - `2` email addresses.
    - `3` URLs.[6]
- **Auth / licensing:**
  - Only available to paid users (Search API on `2.intelx.io`).[2][6]
  - Consumption counts against phonebook lookup allowances.[5][1]
- **Response:**
  - 200 with JSON containing at least `id` and `status` (same structure as `IntelligentSearchRequestResponse`). Third‑party client code (subfinder) decodes `{id,status}` exactly.[9][1]
  - 400 invalid JSON.
  - 401 unauthorized for buckets.
  - 402 no credits.[6]

### 1.9 /phonebook/search/result (Search API)

- **Endpoint:** `GET /phonebook/search/result?id=[UUID]&offset=[optional]&limit=[optional]`.[6][1]
- **Purpose:** Fetch selectors discovered by a phonebook search.[6]
- **Auth / execution:** Same as `/phonebook/search` (Search API key, paid instance, phonebook credit limits).[2][1]
- **Response (PhoneBookSearchResult):**
  - Top‑level:
    - `selectors` (array<Selector>) – documented and confirmed via open‑source clients.[10][9][6]
    - `status` (int) – same enum as `/intelligent/search/result`: 0 success with results, 1 completed, 2 search ID not found, 3 keep trying.[11][1]
  - Each **Selector** object (derived from docs and client code):
    - `selectorvalue` (string) – the actual selector, e.g., `user@example.com`, `sub.example.com`, URL.[10][9]
    - `selectortype` (int) – output entity type:[6]
      - `1` email.
      - `2` domain.
      - `3` URL (various schemes: `http`, `https`, `ftp`, `magnet`, etc.).
      - `23` URL query (URL incl. query part, such as `?id=12`).
- **Hit / no‑hit behavior:**
  - `status:0` with `selectors` array; `status:1` with possibly final selectors; `status:3` with empty array when still running; `status:2` when ID invalid.[11][10][1]

### 1.10 /file/read (Search API)

- **Endpoint:** `GET /file/read?type=[download type]&storageid=[storage identifier]&systemid=[system identifier]&bucket=[optional bucket]`.[1]
- **Purpose:** Download raw item data (binary or binary with content‑disposition); used for full content retrieval of leaks, pastes, stealer logs, etc.[12][1]
- **Parameters:**
  - `type` (int): `0` raw binary; `1` raw binary with `Content-Disposition` and optional `&name` parameter to set filename.[1]
  - One of `storageid` or `systemid` is required; for type 0 binary, `storageid` is preferred for performance.[1]
  - Optional `bucket` to disambiguate.[1]
- **Response:**
  - 200 with raw data payload (content‑type and filename vary by type/media).[1]
  - 400 invalid input.
  - 404 not found.
  - 204 with content‑disposition but item unavailable for some combinations.[1]
- **Limits:** Size limit for `/file/read` is 50 MB (free) / 100 MB (paid).[3]

### 1.11 /file/view (Search API)

- **Endpoint:** `GET /file/view?f=[format]&storageid=[storage identifier]&bucket=[optional bucket]`.[1]
- **Purpose:** Browser‑friendly view of an item; content is sanitized and may be transformed (e.g., HTML/sanitized text or images).[1]
- **Parameters:**
  - `f` (int format): 0 text view, 1 hex view, 2 auto, 3 picture, 5 HTML inline, 6 text view of PDF, 7 text view of HTML, 8 text view of Word files; other codes as documented.[1]
  - `storageid` and optional `bucket` as above.[1]
- **Response:** 200 with transformed content; 400 invalid; 404 not found.[1]
- **Limits:** Size limit for `/file/view` is 20 MB (free) / 30 MB (paid).[3]

### 1.12 /file/preview (Search API)

- **Endpoint:** `GET /file/preview?c=[ContentType]&m=[MediaType]&f=[TargetFormat]&sid=[StorageId]&b=[Bucket]&e=[0|1]&l=[MaxLines]`.[1]
- **Purpose:** Lightweight preview of items (text up to 1000 chars / 12+ lines, or scaled images); used by UI and suitable for context snippets.[1]
- **Parameters:**
  - `c` – content type of source item.
  - `m` – media type (must match `media` from item).[1]
  - `f` – target format: `0` text, `1` picture (for images only).[1]
  - `sid` – storage ID.
  - `b` – bucket.
  - `e` – HTML escaping flag (default true if omitted).
  - `l` – optional max line count (for text preview).[1]
- **Response:**
  - 200 with preview data (text or image thumbnail).
  - 400 invalid input.[1]
- **Behavior:** For text‑like media (HTML, PDF, Word), converts to text and truncates to 1000 chars; for pictures, returns scaled JPG.[1]

### 1.13 /file/treeview (Search API supplement)

- **Endpoint:** `GET /file/treeview?storageid=[storage identifier]&bucket=[bucket]` or `GET /file/treeview?systemid=[system ID]&bucket=[bucket]`.[6]
- **Purpose:** Retrieve a JSON array of items representing the “Tree View” structure—other items linked to a given item, such as files in the same container or related archived websites.[6]
- **Auth / licensing:** Only available to users with valid API, Identity, or Enterprise license.[6]
- **Use cases mentioned:**
  - Stealer logs containing many files inside a single container (ZIP/RAR).
  - Container files representing a single leak.
  - Large files broken into multiple parts.
  - Archived website copies grouped by domain or URL.[6]
- **Response:**
  - JSON array of items with only the following fields populated: `systemid`, `name`, `date`, `media`, `type`, `size` (others empty).
  - Example shows standard item schema, but only subset filled.[6]

### 1.14 Leaks API: /live/search/internal and /live/search/result

These endpoints power the Identity Portal “Search Data Leaks” tab and are part of the **Leaks API** (separate from the Search API).[4]

#### /live/search/internal

- **Endpoint:** `GET https://3.intelx.io/live/search/internal` with query parameters.[4]
- **Purpose:** Start a Leaks API search for a selector; returns a **search job ID** similar to `/intelligent/search` but specifically for leak‑line analysis.[4]
- **Parameters (query):**
  - `selector` – must be email address, domain, social security number, or credit card number.[4]
  - `limit` – approximate result limit; API may return more than this; strict upper bound must be enforced client‑side.[4]
  - `bucket` – optional filter to a specific bucket (e.g., `leaks.public.general`).[4]
  - `skipinvalid` (bool) – skip invalid items.
  - `analyze` (bool) – whether to analyze results.
  - `terminate` – optional previous search ID(s) to terminate.
  - `datefrom`, `dateto` – optional date range filters; note that item dates may be backdated to original breach date.[4]
- **Response:**
  - JSON `{"status": int, "id": "UUID"}`. Example `"status":0` (success) with `id` used in `/live/search/result`.[4]

#### /live/search/result

- **Endpoint:** `GET https://3.intelx.io/live/search/result?id=[UUID]&format=[0|1]`.[4]
- **Purpose:** Fetch results of a Leaks API search job, either as HTML‑encoded text lines or structured records.[4]
- **Response structure:**
  - Top‑level JSON:
    - `status` (int) – semantics:
      - `0` – results in this response; client should continue fetching until terminal state.[4]
      - `1` – no results in this response but client should keep polling.[4]
      - `2` – terminated; may still have final results in this response.
      - `3` – search ID not found.[4]
    - `text` (string) – HTML‑encoded snippet; used when `format=0`.
    - `records` (array<Record>) – used when `format=1` for machine processing.[4]
  - **Format 0 example:** `text` contains HTML where System ID is linked and the matched selector highlighted.[4]
  - **Format 1 record structure for “Search data and return lines”:**
    - `linea` (string) – full line of text (UTF‑8, decoded) where selector appears.[4]
    - `lineraw` (string) – base64‑encoded original line.
    - `positionline` (int) – position/index of line within the file.
    - `positionsize` (int) – size of the line or matched segment.
    - `item` (object) – complete item metadata identical to `/intelligent/search/result` items (systemid, storageid, size, accesslevel, type, media, added, date, name, xscore, bucket, tags, etc.). The example shows `bucket` values like `leaks.public.general` and `leaks.private.general` and tags containing `{"class":4,"value":"email"}`.[4]

### 1.15 Leaks API: Export Leaked Accounts

This function powers the Identity Portal “Export Leaked Accounts” tab and is core for credential exposure.[5][4]

#### /accounts/csv

- **Endpoint:** `GET https://3.intelx.io/accounts/csv?selector=[domain_or_email]&k=[KEY]`.[4]
- **Purpose:** Start an **asynchronous export** of leaked accounts for a selector (domain or email), returning a search job ID.[4]
- **Input constraints:**
  - `selector` must be domain or email; other selector types are not supported for this function.[4]
- **Response:**
  - JSON `{"status": int, "id": "UUID"}`, same semantics as `/live/search/internal`.
  - Clients must then use `/live/search/result` with the returned `id` and `format=1` to fetch account records.[4]

#### /live/search/result (for Export Leaked Accounts)

When used with an ID from `/accounts/csv` and `format=1`, the `records` array has a **different structure** from the “search data and return lines” variant.[4]

- **Record fields (per leaked account):**
  - `user` (string) – leaked account identifier (typically email or username).[4]
  - `password` (string) – leaked password in plaintext or hash representation.
  - `passwordtype` (string) – classification such as `Plaintext` or hash type indicator.[4]
  - `bucket` (string) – bucket from which the account originates, e.g. `leaks.public.general`.[4]
  - `date` (string, ISO 8601) – date associated with this leak record; example shows timezone offset.[4]
  - `sourceshort` (string) – short source label, e.g. breach/dump name (“Collection 1”).[4]
  - `sourcelong` (string) – detailed source path, e.g. archive and file path within collection.[4]
  - `systemid` (UUID) – System ID of the underlying item in the Search API, usable with `/file/*`.[4]
- **Semantics:** Each record is already classified by IntelX as a **leaked account**, including password and source metadata; Identity Portal marketing describes this as reading all relevant data in real time, converting to text, and analyzing to decide whether a line represents a leaked account.[5][4]

#### Synchronous Export (deprecated for large jobs)

- **Endpoint:** `GET https://3.intelx.io/accounts/1?selector=[selector]&timeout=[seconds]&k=[KEY]`.[4]
- **Purpose:** Synchronous export of leaked accounts; documentation recommends using asynchronous `/accounts/csv` instead because synchronous export may miss results not available within timeout.[4]

### 1.16 Leaks API: Terminate Search

- **Endpoint:** `/live/search/terminate` (exact path documented but not shown in detail in snippet; same semantics as Search API terminate).[4]
- **Purpose:** Terminate active Leaks API jobs created by `/live/search/internal` or `/accounts/csv`.[4]
- **Use in Zima:** Utility‑only.

### 1.17 Identity Portal Features: Export Stealer Log (Leaks API)

- **Feature description (blog / product):** Identity Portal exposes an “Export Stealer Log” function, which lets users enter a System ID and download all files belonging to a single stealer log as a ZIP archive, preserving folder structure.[12][5]
- **API details:**
  - Implemented as part of the **Leaks API** and uses its own credits, separate from Search API credits.[12][3]
  - ZIP export limits for stealer logs are documented separately (100 MB uncompressed, 200 files per export, etc.).[3]
  - The exact HTTP endpoint path and JSON structure are **not documented publicly**; only the UI workflow is described (user supplies System ID).[12]
- **Implication for Zima:** This feature is highly relevant for **stealer_log_exposure** but cannot be integrated with precise API contracts without internal documentation; any use must currently treat it as a binary ZIP download keyed by System ID, with unknown JSON envelope.


## 2. Module Mapping Appendix

### 2.1 Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|--------|---------------|-----------------|----------------------|----------------|-------------|-------------|--------------|-------|
| darkweb_identity_monitor | signal_producer | leaks_search_lines | `/live/search/internal` + `/live/search/result` (format=1, line records) | direct_signal_input (for non‑credential identity leak lines), enrichment_only (for general context) | email, domain | Require selector to be email or domain as per Leaks API; only treat results where `records[].item.bucket` is one of `leaks.*`, `darknet.*`, `pastes`, or `whois` as in‑scope; exclude purely public‑web buckets unless policy says otherwise. | [https://es.scribd.com/document/871852043/Leaks-API][4] | Provides structured leak lines (`linea`) with full Search API item metadata; good for detecting identity mentions and non‑credential leaks; raw lines may contain credentials and PII that Zima can parse further. |
| darkweb_identity_monitor | signal_producer | leaks_export_accounts | `/accounts/csv` + `/live/search/result` (format=1, leaked accounts) | direct_signal_input | email, domain | Require selector to be email or domain; only treat `records[].bucket` in `leaks.*` as credential breaches; rely on `user`, `password`, `passwordtype` to decide whether this is credential exposure vs. hash‑only vs. unknown; filter out empty or obviously placeholder passwords. | [https://es.scribd.com/document/871852043/Leaks-API][4][https://intelx.io/product][5] | Primary signal source for leaked credentials; IntelX already aggregates and normalizes accounts across large leak corpus. |
| darkweb_identity_monitor | signal_producer | search_api_items | `/intelligent/search` + `/intelligent/search/result` | enrichment_only (supporting evidence, backup to Leaks API) | email, domain, ip, url | Use only when Leaks API unavailable or to cross‑check; restrict to buckets `leaks.*`, `pastes`, `darknet.*`; treat `type=1002` (Leak) and text `type=1` in `leaks.*` buckets as likely breach items; do not emit standalone signals from Search API alone unless Leaks API cannot be used. | [https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf][1][https://intelx.io/product][5] | Provides full item metadata and enables `/file/*` retrieval; but Identity Portal already performs leak‑account extraction, so Search API is better as enrichment and fallback, not primary signal. |
| darkweb_identity_monitor | signal_producer | phonebook_selectors | `/phonebook/search` + `/phonebook/search/result` | enrichment_only | email, domain, url | Only call for domain‑level monitoring where selector is a domain; parse `selectors[].selectortype` to distinguish email/domain/URL; do not generate standalone “breach” signal solely from phonebook membership; use as discovery/enrichment for additional email addresses/domains/URLs tied to target. | [https://help.intelx.io/api/search/][6][https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf][11][https://sn0int.com/r/kpcyrd/intelx-domain][10] | Phonebook is primarily a discovery tool; presence of an email or domain here could come from WHOIS or benign sources as well as leaks; standalone risk is ambiguous. |
| darkweb_identity_monitor | signal_producer | search_preview | `/file/preview` | enrichment_only | email, domain | Only request previews for items tied to existing leak/identity signals to provide UI snippets; never treat preview existence alone as signal; honor 1000‑char limit and HTML‑escaping when storing. | [https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf][1] | Useful to show the exact line or surrounding context where the email/domain appears, but not a separate finding. |
| darkweb_identity_monitor | signal_producer | search_file_view | `/file/view` | enrichment_only | email, domain | Use for analyst drill‑down; respect `accesslevel` and size limits; only fetch for items that already underlie a signal; do not scan arbitrary files to avoid credit exhaustion. | [https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf][1][https://help.intelx.io/api/limits/][3] | Full view is heavier than preview and may be blocked for some buckets; treat as optional enrichment path. |
| darkweb_identity_monitor | signal_producer | leaks_stealer_export | (undocumented) Leaks API stealer‑log ZIP export | enrichment_only, utility_only | email, domain | Only callable when System ID of relevant leak/stealer log is already known; treat exported ZIP as evidence bundle linked to existing leaked‑account or line‑level signals, not as an independent detection source. | [https://blog.intelx.io/2026/02/08/export-stealer-log/][12][https://intelx.io/product][5][https://help.intelx.io/api/limits/][3] | Lack of public HTTP/JSON spec makes this unsuitable for direct automation beyond “download ZIP by System ID”; see stealer_log_exposure notes. |
| stealer_log_exposure | signal_producer | leaks_export_accounts | `/accounts/csv` + `/live/search/result` | enrichment_only | email, domain | Same as darkweb_identity_monitor, but module may apply stricter logic: flag potential stealer logs when `sourceshort` or `sourcelong` patterns match known infostealer dumps; however, there is no documented stealer‑log flag; treat any such pattern‑based classification as inferred and keep module in enrichment mode until calibrated. | [https://es.scribd.com/document/871852043/Leaks-API][4][https://blog.intelx.io/2026/02/08/export-stealer-log/][12] | In practice many stealer logs surface as leaks with characteristic file naming, but the API does not expose a first‑class “stealer log” field; avoid emitting hard “stealer log” signals solely based on IntelX metadata. |
| stealer_log_exposure | signal_producer | search_api_items_treeview | `/intelligent/search` + `/intelligent/search/result` + `/file/treeview` | enrichment_only (current) | email, domain | Use Search API to find items with container `type=7` and relevant buckets (e.g. `leaks.*`), then Tree View to enumerate linked items; apply local heuristics on filenames and directory structure to infer stealer logs; until IntelX exposes stealer‑log metadata, keep any detections as supporting evidence, not standalone signals. | [https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf][1][https://help.intelx.io/api/search/][6][https://blog.intelx.io/2026/02/08/export-stealer-log/][12] | Tree View documentation explicitly mentions stealer logs as one use case, but does not provide schema for labeling a specific item as a “stealer log”; classification must be implemented in Zima using heuristics. |
| stealer_log_exposure | signal_producer | leaks_stealer_export | (undocumented) Leaks API stealer‑log ZIP export | utility_only | email, domain | Only use to pull complete ZIP for a System ID that Zima has already flagged (based on other logic) as stealer‑log‑like; no triggering directly from this endpoint. | [https://blog.intelx.io/2026/02/08/export-stealer-log/][12][https://help.intelx.io/api/limits/][3] | Good high‑fidelity evidence for analysts; not safe as detection primitive until IntelX publishes an explicit API contract for what constitutes a “Stealer Log”. |
| stealer_log_exposure | signal_producer | search_file_read | `/file/read` | enrichment_only | email, domain | Use when module needs to parse container files or raw log text to detect infostealer patterns; given credit and size limits, restrict to items already narrowed by search/Tree View; do not exhaust credits by scanning arbitrary large dumps. | [https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf][1][https://help.intelx.io/api/limits/][3] | All stealer‑log semantics come from Zima’s own parsers applied to raw bytes, not from an IntelX field. |
| stealer_log_exposure | signal_producer | phonebook_selectors | `/phonebook/search` + `/phonebook/search/result` | out_of_scope | email, domain | Do not use phonebook enumerations as stealer‑log signals; they represent selectors, not log artifacts. | [https://help.intelx.io/api/search/][6] | Phonebook is about selectors, not log content. |

**Summary for modules:**
- **darkweb_identity_monitor:** IntelX is a **signal producer** via Leaks API leaked‑account export and, secondarily, line‑level leak search; Search API and Phonebook are enrichment/fallback.
- **stealer_log_exposure:** IntelX is **enrichment‑heavy** today; there is no documented stealer‑log flag, so Zima should not yet emit hard stealer‑log signals from IntelX alone.


## 3. Signal Contract Table

Only signal types that should be emitted as standalone findings are included here. Given the lack of a first‑class stealer‑log flag, no IntelX‑driven standalone signals are defined for `stealer_log_exposure` at this stage.

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|--------|--------|----------|-----------------|------------|----------|----------|-------------------------|------------------|------------|--------------|-------------------|-----------------|-------------------|------------------|----------------|--------------|-------|
| darkweb_identity_monitor | darkweb_identity_monitor | intelx | leaks_export_accounts (`/accounts/csv` + `/live/search/result` format=1) | credential_breach_found | identity_security | critical | yes | Critical when `passwordtype` indicates plaintext or unsalted/weak hash; downgrade to high when password is hashed with strong scheme and no plaintext is present; downgrade further if leak is very old per `date`. | email | true_finding | For a monitored email: at least one record in `records[]` where `user` equals or maps to the monitored email (case‑normalized), `bucket` starts with `leaks.` and `password` is non‑empty. | `user`, `password`, `passwordtype`, `bucket`, `date`, `sourceshort`, `sourcelong`, `systemid` from Leaks API records. | Optionally mirror Search‑API item metadata referenced by `systemid` via `/intelligent/search/result` for the same selector (e.g., `name`, `xscore`, `tags`, `relations`). | "Leaked credentials for {entity} were found in IntelX leaks data ({sourceshort}, {passwordtype})." | documented (fields and examples in Leaks API manual) | [https://es.scribd.com/document/871852043/Leaks-API][4][https://intelx.io/product][5] | Direct account‑level evidence with password semantics supplied by IntelX; Zima should still validate that `user` maps to the monitored email (e.g., case folding, alias handling). |
| darkweb_identity_monitor | darkweb_identity_monitor | intelx | leaks_export_accounts (`/accounts/csv` + `/live/search/result` format=1) | domain_credential_breach_found | identity_security | high | yes | High when multiple leaked accounts are found for a monitored domain with any password type; escalate to critical for the specific **email‑level** signals which this domain‑level signal may summarize; lower to medium for small numbers of stale leaks (e.g. only very old `date` values). | domain | true_finding | For a monitored domain: at least N (configurable) records where `user` is an email in that domain (e.g., ends with `@example.com`), `bucket` starts with `leaks.`, and `password` non‑empty. | `user`, `passwordtype`, `bucket`, `date`, `sourceshort`, `sourcelong`, `systemid` for representative subset of accounts; count N of total accounts. | Aggregate statistics such as total leaked accounts for domain, earliest/latest leak dates derived from `date` (these are computed, not direct provider fields). | "Multiple leaked accounts for domain {entity} were found across IntelX leak datasets (e.g. {sample_user}, {sourceshort})." | documented (record schema) + derived triggering on domain match | [https://es.scribd.com/document/871852043/Leaks-API][4][https://intelx.io/product][5] | Represents organization‑level exposure; downstream correlation can spawn individual `credential_breach_found` signals per email. |
| darkweb_identity_monitor | darkweb_identity_monitor | intelx | leaks_search_lines (`/live/search/internal` + `/live/search/result` format=1, line records) | darkweb_identity_line_leak | dark_web | medium | yes | Increase to high when `linea` clearly exposes sensitive PII (e.g., address, phone, SSN) or authentication artifacts other than passwords; lower to low when line context appears benign (e.g., public WHOIS data only) or very old by `item.date`. | email | true_finding | For monitored email: at least one `records[]` entry where `linea` contains the normalized email address and `item.bucket` is in `leaks.*`, `darknet.*`, or `pastes`, regardless of whether the line was converted into a leaked account by `/accounts/csv`. | `linea`, `lineraw`, `positionline`, `positionsize`, and `item.systemid`, `item.bucket`, `item.name`, `item.date`, `item.type`, `item.media`. | Optional `tags` from `item.tags`, and limited `/file/preview` snippet for richer context, if different from `linea`. | "The email {entity} appears in leaked data indexed by IntelX (bucket {item.bucket}), including the line: {linea}." | documented (record schema and example) | [https://es.scribd.com/document/871852043/Leaks-API][4] | Captures cases where IntelX has a leak line but it might not have been converted into a normalized account record (e.g. non‑standard formatting), or where PII exposure is the main risk. |
| darkweb_identity_monitor | darkweb_identity_monitor | intelx | phonebook_selectors (`/phonebook/search` + `/phonebook/search/result`) | darkweb_identity_enumerated_selector | identity_security | low | yes | Keep low by default; only promote to medium if correlated with independent breach evidence (e.g., the same email/domain also appears in Leaks API results or other providers); never treat phonebook hit alone as a breach. | domain | contextual_enrichment | For a monitored domain: `/phonebook/search/result` returns at least one selector where `selectortype=1` (email) or `2` (domain) and `selectorvalue` is associated with the monitored domain (e.g., `@example.com` emails or subdomains). | `selectorvalue`, `selectortype`, `status` from PhoneBookSearchResult; request parameters including `term` and `target`. | Downstream enrichment fields such as classification of selector as primary/secondary domain, email role guesses (e.g., `admin@`, `support@`). | "Additional selectors related to {entity} were discovered via IntelX Phonebook (e.g., {selectorvalue})." | derived from documented fields + third‑party client code | [https://help.intelx.io/api/search/][6][https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf][11][https://sn0int.com/r/kpcyrd/intelx-domain][10] | Designed as weak, context‑only signal that can help expand monitoring surface but not by itself indicate compromise. |

**Notes on omitted signals:**
- No standalone IntelX‑based signals are defined for `stealer_log_exposure` until IntelX exposes either a documented stealer‑log flag or a dedicated Leaks API endpoint with explicit semantics. Any stealer‑log insights from IntelX should be treated as enrichment on top of stronger primary signals (e.g., leaked credentials or local endpoint telemetry).


## 4. Severity Rules

### 4.1 credential_breach_found (email)

- **Base severity:**
  - **Critical** when `passwordtype` indicates `Plaintext` or clearly weak/unsalted hash (e.g., IntelX marks it as plaintext in examples such as `"passwordtype": "Plaintext"`).[4]
- **Conditional logic:**
  - **High** when only strong password hashes are present (e.g., recognized salted or modern hash algorithms), but no plaintext; credential exposure is real but exploitation requires cracking.
  - **Medium** when only a small number of ancient leaks exist (e.g., item `date` many years old) and there is corroborating evidence that credentials have been rotated (this requires correlation with other systems; IntelX alone only gives dates).[4]
- **Justification vs. Zima calibration:**
  - The presence of a password string and account identifier is **direct credential exposure**, matching the “critical” category for plaintext and active secrets.[4]
  - Hashed credentials without plaintext still represent a **confirmed breach**, aligning with “high”.

### 4.2 domain_credential_breach_found (domain)

- **Base severity:**
  - **High** because it reflects a **confirmed breach** impacting multiple accounts at the monitored domain, but individual risk must be managed at account level.
- **Conditional logic:**
  - Escalate to **critical** only at the **email‑level** signals; keep domain‑level findings at high to avoid double‑counting.
  - Lower to **medium** if only a handful of very old leaks exist and all are hash‑only; treat as reputation/attack‑surface signal.[4]
- **Justification:** Aggregated domain leakage is a clear, but not necessarily currently exploitable, organizational risk.

### 4.3 darkweb_identity_line_leak (email)

- **Base severity:**
  - **Medium** because it typically shows **passive threat indicators** (mentions, line‑level exposure) rather than clearly exploitable credentials.[4]
- **Conditional logic:**
  - If `linea` parses as containing a password or authentication token (e.g., `user@example.com:password` pattern) and there is **no corresponding `/accounts/csv` record**, Zima may consider upgrading to **high/critical** depending on internal parsing; however, that logic is **derived** and outside the documented IntelX semantics.
  - If `item.bucket` is purely public WHOIS or non‑sensitive context (e.g., bucket `whois` or `web.public.*`), severity should be **low** or downgraded to enrichment‑only.
- **Justification:** The Leaks API documentation explicitly aims this API at listing lines where selectors appear, not at classifying them as accounts; risk therefore depends heavily on Zima’s own parsing.[4]

### 4.4 darkweb_identity_enumerated_selector (domain)

- **Base severity:**
  - **Low** because a selector recorded in phonebook data may come from benign sources like WHOIS and not necessarily from a compromise.[8][6]
- **Conditional logic:**
  - Only elevate beyond low when other providers or IntelX Leaks API independently confirm breaches involving those selectors; this is correlation logic, not IntelX semantics.

### 4.5 Assessment vs. first‑pass provider severity

- IntelX does **not** expose a single numeric severity; instead, it exposes structural context (bucket, type, passwordtype, date) from which Zima can derive severity.[4][1]
- The recommended mapping above aligns well with Zima’s calibration guide:
  - Leaked plaintext credentials → **critical**.
  - Confirmed breach with hashed credentials → **high**.
  - Line‑level identity exposure and mentions → **medium/low** depending on context.
  - Selector enumeration via Phonebook → **low/info**.


## 5. Confidence Guidance

### 5.1 Confidence Guidance Table

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|--------|-------------------------|--------------------|--------------------------|---------------------|------------------|
| darkweb_identity_monitor | credential_breach_found (email) | IntelX operates a large, curated leak corpus with explicit account‑level extraction (user/password/passwordtype) and source details (`sourceshort`, `sourcelong`); Identity Portal marketing emphasizes real‑time parsing across >200 billion records, indicating mature backend logic.[5][4] | `date` reflects either original publication date or index date; Leaks API notes that items can be backdated to original publish time, so Zima must treat dates cautiously and avoid assuming recency from index behavior alone.[4] | Cross‑check leaked accounts against other breach providers and local auth logs; verify whether the account still exists and whether password reuse is plausible; use IntelX `systemid` to fetch `/file/preview` for manual validation when signals are high‑impact. | Build empirical stats on IntelX leak overlap vs. other providers, per bucket and per passwordtype; tune how often IntelX‑only leaks still correspond to valid credentials in your environment to adjust confidence bands. |
| darkweb_identity_monitor | domain_credential_breach_found (domain) | Domain aggregation is derived from the same Leaks API accounts data; reliability is high for counting exposures but depends on accurate email parsing and domain matching in Zima’s own logic.[4] | Organizations with long histories may have many old leaks; Zima should weight older leaks less heavily at domain level and prefer recent `date` values for current‑risk estimation.[4] | Correlate with internal password rotation policies and historical incident records; check whether high‑volume breaches are already known and mitigated; compare counts with other breach services to detect under‑/over‑coverage. | Build histograms of leak counts per domain vs. incident history to map count ranges to practical risk; adjust domain‑level severity threshold N and decay curves for old leaks. |
| darkweb_identity_monitor | darkweb_identity_line_leak (email) | The Leaks API line‑level search reuses Search API item schema and returns precise line and bucket; structure is well‑documented, but whether a given line truly reflects sensitive information depends on Zima’s own parsers.[4][1] | Staleness is similar to other leaks; individual lines can persist indefinitely even if underlying risk has changed (password rotation, account closure); there is no “seen last active” notion at line level beyond item `date` and bucket context.[4] | Prefer to emit strong signals only when lines parse into recognizable credential/PII patterns; corroborate with `/accounts/csv` results and possibly other providers or internal telemetry before escalating severity. | Implement and tune pattern‑matching for credentials and PII on `linea`, then sample alerts for analyst review; track false‑positive rate and adjust patterns and bucket filters. |
| darkweb_identity_monitor | darkweb_identity_enumerated_selector (domain) | Phonebook is documented as a selector discovery tool; it aggregates data from multiple sources (incl. WHOIS and leaks), but IntelX does not classify selectors as compromised vs. benign here.[6][8] | Phonebook data may lag behind newest leaks and may retain outdated selectors indefinitely; there is no recency field per selector beyond what can be inferred from later correlations. | Treat phonebook hits as low‑confidence enrichment until the same selectors appear in Leaks API or other providers; do not use as sole trigger for response. | Measure how often phonebook‑discovered selectors later show up in verified breaches; if correlation is strong for certain buckets or TLDs, you may raise confidence selectively. |
| stealer_log_exposure | Any IntelX‑based stealer log heuristics | IntelX explicitly mentions stealer logs in Tree View and Identity Portal features, but does not expose a structured “stealer_log” field in public API docs; any stealer‑log detection today would rely on filename patterns, bucket combinations, and external knowledge, not provider guarantees.[6][12] | Stealer logs often represent very recent compromises, but IntelX’s indexing time may lag; additionally, IntelX’s export limits for stealer logs (100 MB, 200 files) can truncate large logs, affecting completeness.[3][12] | Corroborate any IntelX‑flagged stealer logs with local endpoint telemetry (infostealer detections, unusual logins, browser artifact analysis) and other dark‑web sources; avoid acting solely on IntelX stealer‑log heuristics without corroboration. | Defer defining IntelX‑driven stealer_log_exposure signals until IntelX exposes an explicit stealer‑log flag or stable Leaks API endpoint; in the meantime, run pilots that compare IntelX stealer‑log candidates (via heuristics) against confirmed malware cases to estimate precision. |


## 6. Tags

Suggested tags for each defined signal type (from the provided tag set):

- **credential_breach_found:** `breach`, `dark_web`, `credential_stuffing`, `plaintext_password` (when applicable).
- **domain_credential_breach_found:** `breach`, `dark_web`, `credential_stuffing`.
- **darkweb_identity_line_leak:** `breach`, `dark_web`, `pii_exposure` (when line contains PII), `phishing` (if context suggests phishing kits or lists).
- **darkweb_identity_enumerated_selector:** `dark_web`, `breach` (only if correlated), possibly `spam` when selectors are primarily harvested for spam campaigns.

These tags should be applied conditionally based on bucket (`leaks.*` vs `whois`), parsed content, and correlation with other providers.


## 7. Implementation Notes

### 7.1 Field Paths and Parsing Requirements

- Preserve Leaks API record fields **exactly** as documented:
  - `user`, `password`, `passwordtype`, `bucket`, `date`, `sourceshort`, `sourcelong`, `systemid`.[4]
- From “Search data and return lines”, retain at minimum:
  - `linea`, `lineraw`, `positionline`, `positionsize`, `item.systemid`, `item.bucket`, `item.name`, `item.date`, `item.type`, `item.media`, `item.tags`.[4]
- From Search API items (`/intelligent/search/result`), fields critical for correlation and drill‑down:
  - `systemid`, `storageid`, `bucket`, `date`, `name`, `type`, `media`, `xscore`, `tags`, `relations`, `friends`.[1]
- From Phonebook selectors:
  - `selectorvalue`, `selectortype`, top‑level `status`.[10][6]

All these should be available in `evidence` for signals touching them to allow future deduplication and re‑evaluation.

### 7.2 No‑hit / empty behavior

- `/intelligent/search/result` and `/phonebook/search/result` return structured `status` codes; Zima should treat `status` 1 (no future results) with empty arrays as a clean no‑hit, and `status` 3 as “still running – keep polling” with backoff respecting API limits.[11][1]
- Leaks API `/live/search/result` shares similar semantics, with `status` 1 meaning “no results in this response but continue polling”, and 2 or 3 indicating termination or not‑found.[4]
- For `/accounts/csv`, the existence of an `id` with `status:0` merely indicates job creation; only `records` in `live/search/result` constitute evidence.

### 7.3 Rate limits, billing, licensing

- Use Search API and Leaks API **separately**; they have separate credit pools and instances.[2][3]
- Phonebook lookups and Leaks API exports can be credit‑expensive; domain‑level scheduled scans should respect daily caps for the configured license tier (e.g., API vs Identity Portal vs Enterprise).[5][3]
- For heavy use (e.g., bulk domain scans), Zima should prefer batch export methods (`/intelligent/search/export`, `/accounts/csv`) over scanning individual items via `/file/read`.

### 7.4 Deduplication and natural identifiers

- **System ID** is the canonical identifier for items across Search and Leaks APIs; signals should use it as a natural deduplication key for a given leak file.[4][1]
- For leaked accounts, `(selector, user, bucket, systemid)` forms a good compound key; `sourceshort` + `sourcelong` can provide human‑readable grouping.
- For line‑level leaks, `(selector, item.systemid, positionline, linea)` is a natural key to avoid multiple alerts for the same line.
- For Phonebook selectors, `(term, selectorvalue, selectortype)` (plus `target` from request) deduplicates enumerated selectors.

### 7.5 Client vs. mapper vs. correlation layer

- **Provider client (intelx SDK wrapper):**
  - Handle authentication, retry, backoff, rate‑limit error mapping, and decode JSON into internal structs closely mirroring IntelX types.
  - Implement generic polling logic for Search API and Leaks API jobs based on `status` codes and documented timeouts.[3][4][1]
- **Module mapper (darkweb_identity_monitor):**
  - Convert Leaks API `records` into Zima’s normalized signals, applying trigger conditions and severity rules described above.
  - Maintain per‑selector state to prevent re‑alerting on the same leaked accounts unless new `systemid`/`date` or new buckets appear.
  - Enrich signals with optional Search API and `/file/preview` evidence.
- **Correlation layer:**
  - Merge IntelX‑derived signals with other breach providers and internal telemetry (SSO logs, password reuse checks); decide when to collapse many email‑level signals into domain‑level incidents and vice versa.
  - For stealer‑log‑related enrichment, maintain mapping between IntelX items and local endpoint incidents, but defer automated detection until IntelX exposes explicit stealer‑log semantics.

### 7.6 Future stealer_log_exposure integration

- Monitor IntelX docs (Leaks API and Search API supplement) for:
  - A dedicated stealer‑log bucket or tag class/value pair.
  - Fields exposed via Tree View or Leaks API that explicitly label a container as “Stealer Log”.[12][6]
- Once available, Zima can define a new `stealer_log_credential_exposed` signal using those fields as direct triggers, with **critical** severity when leaked credentials for monitored identities are present in such logs.


## 8. Provider Summary

- **Strongest signal types:**
  - Account‑level leaked credentials via Leaks API `/accounts/csv` + `/live/search/result` (user/password/passwordtype/bucket/source).
  - Domain‑level aggregation of leaked accounts for `identity.intelx.io` selectors.
  - Line‑level leak evidence for selectors via Leaks API `/live/search/internal` and `/live/search/result` (linea + full item metadata).
- **What IntelX should not be used for in Zima (today):**
  - First‑class stealer‑log detection, because there is no publicly documented stealer‑log flag or endpoint that declares “this is a stealer log” at the API level.
  - Standalone risk assessment from Phonebook data; it is better treated as enrichment for discovery.
- **API/auth/rate‑limit/licensing cautions:**
  - Separate keys and limits for Search API (public/free/2) vs. Leaks API (3/4), with distinct credit pools and instance URLs.[2][3][4]
  - Heavy Leaks API queries (especially `/accounts/csv` for large domains) can process gigabytes of data and run for minutes; Zima must respect timeouts and consider asynchronous polling strategies.[5][4]
  - Export ZIP limits for stealer logs and general ZIP exports constrain how much evidence can be pulled in one shot.[12][3]
- **Overall treatment in current Zima stage:**
  - For **darkweb_identity_monitor**, IntelX should be treated as a **core signal‑producing provider**, with Leaks API as primary and Search API/Phonebook for enrichment.
  - For **stealer_log_exposure**, IntelX should for now be treated as **enrichment/utility‑only**, pending a documented stealer‑log classification in the API; Zima can still use IntelX to pull supporting evidence and context for stealer logs detected by other means.


{
  "provider": "intelx",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "signal_producer",
      "provider_method": "leaks_search_lines",
      "endpoint_or_artifact": "/live/search/internal + /live/search/result?format=1",
      "classification": "direct_signal_input",
      "entity_types": ["email", "domain"],
      "gating_logic": "Selector must be email or domain; only treat records where records[].item.bucket starts with leaks., darknet., pastes, or whois as in-scope; treat other buckets as enrichment-only.",
      "citation_refs": [
        "https://es.scribd.com/document/871852043/Leaks-API"
      ],
      "notes": "Provides structured leak lines (linea) with full Search API item metadata for identity mentions and non-credential leaks."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "signal_producer",
      "provider_method": "leaks_export_accounts",
      "endpoint_or_artifact": "/accounts/csv + /live/search/result?format=1",
      "classification": "direct_signal_input",
      "entity_types": ["email", "domain"],
      "gating_logic": "Selector must be email or domain; for signals, require records[].bucket starting with leaks. and non-empty password; map user to monitored email/domain.",
      "citation_refs": [
        "https://es.scribd.com/document/871852043/Leaks-API",
        "https://intelx.io/product"
      ],
      "notes": "Primary source for leaked credentials (user/password/passwordtype) with bucket and source metadata."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "signal_producer",
      "provider_method": "search_api_items",
      "endpoint_or_artifact": "/intelligent/search + /intelligent/search/result",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain", "ip", "url"],
      "gating_logic": "Use only when Leaks API is unavailable or for enrichment; restrict to buckets leaks.*, pastes, darknet.*; treat type=1002 (leak) and text type=1 in leaks.* as likely breach-related for context, but do not emit standalone signals.",
      "citation_refs": [
        "https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf",
        "https://intelx.io/product"
      ],
      "notes": "Used to fetch item metadata and enable /file/* retrieval to back Leaks API signals."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "signal_producer",
      "provider_method": "phonebook_selectors",
      "endpoint_or_artifact": "/phonebook/search + /phonebook/search/result",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain", "url"],
      "gating_logic": "Only for domain-level monitoring; parse selectors[].selectortype to distinguish email/domain/URL; never treat a phonebook hit alone as breach.",
      "citation_refs": [
        "https://help.intelx.io/api/search/",
        "https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf",
        "https://sn0int.com/r/kpcyrd/intelx-domain"
      ],
      "notes": "Discovery of related selectors (emails, domains, URLs); used to expand monitoring surface."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "signal_producer",
      "provider_method": "search_preview",
      "endpoint_or_artifact": "/file/preview",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Only fetch for items already underlying a signal; preview existence alone never triggers a signal.",
      "citation_refs": [
        "https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf"
      ],
      "notes": "Short text/image snippets for UX; limited to ~1000 chars / 12+ lines for text."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "signal_producer",
      "provider_method": "search_file_view",
      "endpoint_or_artifact": "/file/view",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Only for analyst drill-down on items tied to existing signals; respect accesslevel and size limits.",
      "citation_refs": [
        "https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf",
        "https://help.intelx.io/api/limits/"
      ],
      "notes": "Heavier full-content view than preview; credit- and size-limited."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "signal_producer",
      "provider_method": "leaks_stealer_export",
      "endpoint_or_artifact": "Leaks API stealer-log ZIP export (undocumented path)",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Only callable when System ID of relevant leak/stealer log is known and already tied to a signal.",
      "citation_refs": [
        "https://blog.intelx.io/2026/02/08/export-stealer-log/",
        "https://intelx.io/product",
        "https://help.intelx.io/api/limits/"
      ],
      "notes": "Binary ZIP evidence bundle; HTTP/JSON schema not publicly documented."
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "leaks_export_accounts",
      "endpoint_or_artifact": "/accounts/csv + /live/search/result?format=1",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Same as darkweb_identity_monitor; module may apply additional heuristics on sourceshort/sourcelong to guess stealer logs, but not as primary triggers.",
      "citation_refs": [
        "https://es.scribd.com/document/871852043/Leaks-API",
        "https://blog.intelx.io/2026/02/08/export-stealer-log/"
      ],
      "notes": "Supplies credential exposure context that may originate from stealer logs, but without explicit stealer-log flag."
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "search_api_items_treeview",
      "endpoint_or_artifact": "/intelligent/search + /intelligent/search/result + /file/treeview",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Use Search API to find container files (type=7) in relevant buckets, then /file/treeview to enumerate children; apply local heuristics on filenames/paths to classify stealer logs; do not emit standalone signals yet.",
      "citation_refs": [
        "https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf",
        "https://help.intelx.io/api/search/",
        "https://blog.intelx.io/2026/02/08/export-stealer-log/"
      ],
      "notes": "Treeview docs mention stealer logs as a use case, but there is no structured stealer-log flag in the API."
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "leaks_stealer_export",
      "endpoint_or_artifact": "Leaks API stealer-log ZIP export (undocumented path)",
      "classification": "utility_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Only download ZIP for System IDs already flagged as stealer-log-like by Zima heuristics or other telemetry.",
      "citation_refs": [
        "https://blog.intelx.io/2026/02/08/export-stealer-log/",
        "https://help.intelx.io/api/limits/"
      ],
      "notes": "Used purely for evidence collection; not a detection primitive."
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "search_file_read",
      "endpoint_or_artifact": "/file/read",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Parse raw container/log bytes only for items already identified via Search/Treeview; avoid scanning arbitrary large dumps to preserve credits.",
      "citation_refs": [
        "https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf",
        "https://help.intelx.io/api/limits/"
      ],
      "notes": "All stealer-log semantics here come from Zima’s own parsers; IntelX just provides storage and retrieval."
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "phonebook_selectors",
      "endpoint_or_artifact": "/phonebook/search + /phonebook/search/result",
      "classification": "out_of_scope",
      "entity_types": ["email", "domain"],
      "gating_logic": "Do not use phonebook enumerations as stealer-log indicators.",
      "citation_refs": [
        "https://help.intelx.io/api/search/"
      ],
      "notes": "Phonebook enumerates selectors, not log artifacts; no direct stealer-log semantics."
    }
  ],
  "signal_contracts": [
    {
      "module": "darkweb_identity_monitor",
      "source": "darkweb_identity_monitor",
      "provider": "intelx",
      "provider_method": "leaks_export_accounts",
      "signal_type": "credential_breach_found",
      "category": "identity_security",
      "severity": "critical",
      "severity_is_conditional": "yes",
      "conditional_rule": "Critical when passwordtype indicates plaintext or weak/unsalted hash; high when only strong hashes; medium for very old leaks where credentials are likely rotated.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "For a monitored email, at least one /live/search/result record (format=1) from an /accounts/csv job where user equals the monitored email (case-normalized), bucket starts with \"leaks.\" and password is non-empty.",
      "evidence_fields": [
        "user",
        "password",
        "passwordtype",
        "bucket",
        "date",
        "sourceshort",
        "sourcelong",
        "systemid"
      ],
      "enrichment_fields": [
        "correlated Search API item fields via systemid (name, xscore, tags, relations)"
      ],
      "summary_template": "Leaked credentials for {entity} were found in IntelX leaks data ({sourceshort}, {passwordtype}).",
      "evidence_status": "documented",
      "citation_refs": [
        "https://es.scribd.com/document/871852043/Leaks-API",
        "https://intelx.io/product"
      ],
      "notes": "Direct evidence of credential exposure; IntelX already classifies leaked accounts with password semantics."
    },
    {
      "module": "darkweb_identity_monitor",
      "source": "darkweb_identity_monitor",
      "provider": "intelx",
      "provider_method": "leaks_export_accounts",
      "signal_type": "domain_credential_breach_found",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "High when multiple leaked accounts are found for the monitored domain; medium for few, very old, hash-only leaks; per-email credential_breach_found signals can be escalated to critical independently.",
      "entity_type": "domain",
      "finding_kind": "true_finding",
      "trigger_condition": "For a monitored domain, at least N records (configurable) where user is an email at that domain, bucket starts with \"leaks.\" and password is non-empty.",
      "evidence_fields": [
        "user",
        "passwordtype",
        "bucket",
        "date",
        "sourceshort",
        "sourcelong",
        "systemid",
        "aggregated_account_count"
      ],
      "enrichment_fields": [
        "earliest_leak_date",
        "latest_leak_date",
        "sample_user"
      ],
      "summary_template": "Multiple leaked accounts for domain {entity} were found across IntelX leak datasets (e.g. {sample_user}, {sourceshort}).",
      "evidence_status": "documented_and_derived",
      "citation_refs": [
        "https://es.scribd.com/document/871852043/Leaks-API",
        "https://intelx.io/product"
      ],
      "notes": "Organization-level exposure signal aggregating individual leaked accounts."
    },
    {
      "module": "darkweb_identity_monitor",
      "source": "darkweb_identity_monitor",
      "provider": "intelx",
      "provider_method": "leaks_search_lines",
      "signal_type": "darkweb_identity_line_leak",
      "category": "dark_web",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Medium by default; high when linea clearly exposes sensitive PII or auth artifacts; low when bucket is benign context (e.g., whois or purely public web) or very old.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "For a monitored email, at least one /live/search/result record (format=1) from /live/search/internal where linea contains the normalized email and item.bucket starts with leaks., darknet., or pastes.",
      "evidence_fields": [
        "linea",
        "lineraw",
        "positionline",
        "positionsize",
        "item.systemid",
        "item.bucket",
        "item.name",
        "item.date",
        "item.type",
        "item.media"
      ],
      "enrichment_fields": [
        "item.tags",
        "optional file preview snippet if different from linea"
      ],
      "summary_template": "The email {entity} appears in leaked data indexed by IntelX (bucket {item.bucket}), including the line: {linea}.",
      "evidence_status": "documented",
      "citation_refs": [
        "https://es.scribd.com/document/871852043/Leaks-API"
      ],
      "notes": "Captures line-level identity exposure even when not normalized into an account record."
    },
    {
      "module": "darkweb_identity_monitor",
      "source": "darkweb_identity_monitor",
      "provider": "intelx",
      "provider_method": "phonebook_selectors",
      "signal_type": "darkweb_identity_enumerated_selector",
      "category": "identity_security",
      "severity": "low",
      "severity_is_conditional": "yes",
      "conditional_rule": "Low by default; can be raised to medium only when corroborated by independent breach evidence involving the same selectors.",
      "entity_type": "domain",
      "finding_kind": "contextual_enrichment",
      "trigger_condition": "For a monitored domain, /phonebook/search/result returns at least one selector where selectortype equals 1 or 2 and selectorvalue is related to the monitored domain (subdomain or email at the domain).",
      "evidence_fields": [
        "selectorvalue",
        "selectortype",
        "status"
      ],
      "enrichment_fields": [
        "request.term",
        "request.target"
      ],
      "summary_template": "Additional selectors related to {entity} were discovered via IntelX Phonebook (e.g., {selectorvalue}).",
      "evidence_status": "derived",
      "citation_refs": [
        "https://help.intelx.io/api/search/",
        "https://www.ginseg.com/wp-content/uploads/sites/2/2019/07/Manual-Intelligence-X-API.pdf",
        "https://sn0int.com/r/kpcyrd/intelx-domain"
      ],
      "notes": "Designed as a weak context signal to expand monitored identities; not a breach indicator on its own."
    }
  ],
  "confidence_guidance": [
    {
      "module": "darkweb_identity_monitor",
      "signal_type_or_use_case": "credential_breach_found (email)",
      "source_reliability": "IntelX maintains a large curated leak corpus and a Leaks API that explicitly extracts user/password/passwordtype and source metadata for leaked accounts.",
      "freshness_considerations": "date may reflect original publication date or index date; items can be backdated, so recency must be interpreted cautiously.",
      "corroboration_rules": "Cross-check leaked accounts against other breach providers and internal auth logs; use systemid with /file/preview for manual validation on high-impact cases.",
      "calibration_todo": "Measure overlap between IntelX leaks and other providers and how often IntelX-only leaks still correspond to valid credentials; use this to tune confidence thresholds per bucket and passwordtype."
    },
    {
      "module": "darkweb_identity_monitor",
      "signal_type_or_use_case": "domain_credential_breach_found (domain)",
      "source_reliability": "Domain-level counts are aggregated from the same Leaks API accounts data; reliability depends on accurate email parsing and domain matching.",
      "freshness_considerations": "Old leaks may still contribute to counts; weight older dates less heavily when assessing current risk.",
      "corroboration_rules": "Compare domain leak counts to internal incident history and password rotation practices; cross-check against other breach services.",
      "calibration_todo": "Build distributions of leak counts per domain versus observed incidents and use them to define severity thresholds and decay curves for old leaks."
    },
    {
      "module": "darkweb_identity_monitor",
      "signal_type_or_use_case": "darkweb_identity_line_leak (email)",
      "source_reliability": "Line-level records reuse the Search API item schema and give precise line and bucket; sensitivity depends on Zima’s parsing of linea content.",
      "freshness_considerations": "Lines can persist indefinitely; there is no separate last-seen field beyond item.date and bucket context.",
      "corroboration_rules": "Only escalate when lines parse into credential or PII patterns and, ideally, when corroborated by /accounts/csv or other providers.",
      "calibration_todo": "Implement and tune regex/ML patterns for credentials and PII on linea, then review a sample of alerts to estimate precision and adjust patterns and bucket filters."
    },
    {
      "module": "darkweb_identity_monitor",
      "signal_type_or_use_case": "darkweb_identity_enumerated_selector (domain)",
      "source_reliability": "Phonebook aggregates selectors from multiple sources (including WHOIS and leaks) but does not classify them as compromised vs. benign.",
      "freshness_considerations": "Selectors may be stale or long-lived; recency per selector is not explicitly exposed.",
      "corroboration_rules": "Treat phonebook hits as low-confidence until selectors are seen in Leaks API or other breach sources.",
      "calibration_todo": "Track how often phonebook-discovered selectors later appear in confirmed breaches and adjust how much weight to give this enrichment."
    },
    {
      "module": "stealer_log_exposure",
      "signal_type_or_use_case": "IntelX-based stealer log heuristics",
      "source_reliability": "Docs and blog posts mention stealer logs in Tree View and Identity Portal, but there is no structured stealer-log field in public APIs; any detection is heuristic.",
      "freshness_considerations": "Stealer logs are often recent but indexing time and export limits can affect completeness and timeliness.",
      "corroboration_rules": "Correlate any IntelX stealer-log candidates with local endpoint telemetry and other dark-web sources; avoid acting solely on IntelX heuristics.",
      "calibration_todo": "Run pilot correlations between IntelX stealer-log candidates (found via heuristics) and confirmed malware cases to estimate precision before defining hard signals."
    }
  ]
}
