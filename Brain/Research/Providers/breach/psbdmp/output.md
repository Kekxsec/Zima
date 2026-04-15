---
title: "output / breach / psbdmp"
aliases: ["psbdmp output", "psbdmp signal registry"]
tags: [zima, research, outputs, signal-registry, breach, psbdmp, graph_exclude]
type: provider_research_output
provider: psbdmp
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: psbdmp.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
psbdmp is a Pastebin-dump index with a small REST API (v3) that lets you search dumps and fetch full paste content; for Zima it should primarily be used as an OSINT signal producer for credential exposure (via `search` + `dump`), with everything else treated as enrichment/utility and carefully gated because a “paste hit” is not the same as a confirmed breach.

Below is the requested implementation-grade breakdown.

---

## A. API Surface Appendix

### General provider notes

- psbdmp is described on its own API page as “the largest-scale collection of publicly available Pastebin dumps,” currently advertising a dataset of over 28 million entries, some dating back to 2015 or earlier.[psbdmp](https://psbdmp.ws/api)

- The API page explicitly states the project will be shut down permanently “at some point during the year,” with the dataset offered for exclusive acquisition first, so long‑term availability is uncertain.[psbdmp](https://psbdmp.ws/api)

- The v3 API is unauthenticated in the public docs; third‑party tooling treats it as a free, public service, though at least one tool (MOSINT) models psbdmp as an API-keyed service for its own


Treat this as a non-SLA OSINT source: no uptime guarantees, schema may change without notice, and rate limits are undocumented.

---

### 1) GET `/api/v3/dump/{DUMP_ID}`

**Purpose**

Fetch full metadata and content of a single indexed Pastebin dump by its internal ID.[psbdmp](https://psbdmp.ws/api)

**Supported entity_type(s)**

- Not entity-driven; takes a dump ID, which you typically get from `search`, `today`, `date`, etc.[psbdmp](https://psbdmp.ws/api)

- In Zima, this is a _second hop_ after entity-based search.


**Auth / execution**

- HTTP GET to `https://psbdmp.ws/api/v3/dump/{DUMP_ID}`.[psbdmp](https://psbdmp.ws/api)

- No auth mechanism documented; third‑party tools call it anonymously.[cocalc](https://cocalc.com/github/alpkeskin/mosint/blob/master/v3/pkg/services/psbdmp/psbdmp.go)


**Top-level response (successful hit)**

Example from docs:[psbdmp](https://psbdmp.ws/api)

json

`{   "id": "KF7hDTp1",  "tags": "",  "date": "2018-11-29 14:18",  "content": "inurl:pastebin | siph0n | psbdmp | ddos.cf intext:(\"professor.sp.gov.br\")" }`

- `id` (string) – internal dump id; always present in example.[psbdmp](https://psbdmp.ws/api)

- `tags` (string) – arbitrary tag string, e.g. `"none"` or `""`; appears optional/empty but always present as a field.[psbdmp](https://psbdmp.ws/api)

- `date` (string) – human‑readable timestamp “YYYY-MM-DD HH:MM”.[psbdmp](https://psbdmp.ws/api)

- `content` (string) – full text of the paste as captured by psbdmp.[psbdmp](https://psbdmp.ws/api)


No explicit indication of partial content vs full; examples suggest full paste content.

**No‑hit / error behavior**

- Not documented; likely HTTP 404 or 4xx JSON error, but schema is unknown (must be probed in implementation and treated as _unknown_).[psbdmp](https://psbdmp.ws/api)


**Classification (per Zima)**

- For `breach_monitor`: `direct_signal_input` (needed to inspect contents for credentials/PII).

- For `alias_correlation`: `enrichment_only` (used to mine aliases inside content).


---

### 2) GET `/api/v3/today`

**Purpose**

List dumps created “today” (server‑side local date), with lightweight metadata and short text preview.[psbdmp](https://psbdmp.ws/api)

**Supported entity_type(s)**

- None directly; this is a global feed not scoped to a specific entity.

- Zima would only use this in a future “global threat intel” module, not for per‑entity alias/breach queries.


**Auth / execution**

- HTTP GET `https://psbdmp.ws/api/v3/today`.[psbdmp](https://psbdmp.ws/api)

- No auth documented.


**Top-level response (successful)**

Example:[psbdmp](https://psbdmp.ws/api)

json

`{   "date": "2024-01-21",  "count": 131,  "data": [    {      "id": "UViAHFXZ",      "tags": "none",      "length": 44,      "time": "2024-01-21 00:05",      "text": "Fitky_austin\r\nEmblazes\r\nLizard\r\nTheBeastMare"    },    ...  ] }`

- `date` (string, `YYYY-MM-DD`) – the date this listing covers.[psbdmp](https://psbdmp.ws/api)

- `count` (integer) – number of dumps for that date.[psbdmp](https://psbdmp.ws/api)

- `data` (array of objects) – per-dump metadata and preview.[psbdmp](https://psbdmp.ws/api)

    - `id` (string) – dump id.

    - `tags` (string) – tag label such as `"none"`.

    - `length` (integer) – likely character count of the paste.[psbdmp](https://psbdmp.ws/api)

    - `time` (string timestamp `YYYY-MM-DD HH:MM`).[psbdmp](https://psbdmp.ws/api)

    - `text` (string) – snippet or possibly truncated content.[psbdmp](https://psbdmp.ws/api)


Fields appear always present in the example; no documentation of optionality.

**No‑hit / partial / error**

- `count` would reasonably be `0` and `data` `[]` if there are no dumps, but this is not explicitly documented (treat as _inferred_).[psbdmp](https://psbdmp.ws/api)

- Errors / pagination behavior not described; assume whole-day coverage in a single page.


**Classification (per Zima)**

- For both target modules: `utility_only` / `out_of_scope` (not entity-driven).


---

### 3) GET `/api/v3/yesterday`

**Purpose**

Same as `/today`, but for the previous calendar day.[psbdmp](https://psbdmp.ws/api)

**Shape**

- No separate JSON example; the API page lists it directly after `/today`, strongly implying identical schema (date, count, data[id,tags,length,time,text]).[psbdmp](https://psbdmp.ws/api)


**Classification**

- For both modules: `utility_only` / `out_of_scope` (global feed).


---

### 4) GET `/api/v3/date/:date`

**Purpose**

List dumps for an arbitrary date, with pagination.[psbdmp](https://psbdmp.ws/api)

**Execution**

- HTTP GET `https://psbdmp.ws/api/v3/date/2018-01-21?page=2`.[psbdmp](https://psbdmp.ws/api)

- `:date` must be `YYYY-MM-DD`; `page` is a query parameter.


**Response**

Example (truncated in docs):[psbdmp](https://psbdmp.ws/api)

json

`{   "current_page": 2,  "data": [    { "id": "V7GZmNj5", "tags": "none", "date": 1516494843 },    { "id": "CAdA7A2e", "tags": "none", "date": 1516494843 },    ...  ] }`

From the more complete `getbydate` example (same paginator), we can _derive_ these additional fields:[psbdmp](https://psbdmp.ws/api)

- `first_page_url`, `last_page_url`, `next_page_url`, `prev_page_url` (string URLs).

- `from`, `to`, `last_page`, `per_page`, `total` (integers).[psbdmp](https://psbdmp.ws/api)


Per‑dump `data` fields:

- `id` (string) – dump ID.

- `tags` (string) – tag.

- `date` (integer, Unix timestamp) – creation time.[psbdmp](https://psbdmp.ws/api)


**No‑hit / partial**

- For dates with few dumps, `total` and `last_page` will be small; paginate as usual.[psbdmp](https://psbdmp.ws/api)

- No explicit “no results” schema documented; likely `data: []` and `total: 0` (inferred).


**Classification**

- For both target modules: `utility_only` (historical backfill or bulk crawling only).


---

### 5) GET `/api/v3/latest/:num`

**Purpose**

Return the most recent dumps, up to a specified count.[psbdmp](https://psbdmp.ws/api)

**Execution**

- HTTP GET `https://psbdmp.ws/api/v3/latest` or `/api/v3/latest/{NUM}`.[psbdmp](https://psbdmp.ws/api)

- Docs: by default, 100 dumps are returned if `:num` is omitted; valid `:num` is from 1 to 1000.[psbdmp](https://psbdmp.ws/api)


**Response**

Example (truncated):[psbdmp](https://psbdmp.ws/api)

json

`[   {    "id": "neNU65Pk",    "tags": "none",    "length": 1345,    "time": "2024-01-21 20:35",    "text": "..."  },  ... ]`

Per‑dump fields:

- `id` (string) – dump id.

- `tags` (string).

- `length` (integer).

- `time` (string timestamp).

- `text` (string snippet).[psbdmp](https://psbdmp.ws/api)


The response is a bare array, similar to `search`.[psbdmp](https://psbdmp.ws/api)

**Classification**

- For both modules: `utility_only` (bulk monitoring / research, not entity‑scoped).


---

### 6) GET `/api/v3/search/:word`

**Purpose**

Search all indexed dumps for occurrences of an arbitrary keyword/term.[psbdmp](https://psbdmp.ws/api)

**Execution**

- HTTP GET `https://psbdmp.ws/api/v3/search/{word}`.[psbdmp](https://psbdmp.ws/api)

- Official docs show example `search/psbdmp` and return an array of objects.[psbdmp](https://psbdmp.ws/api)

- Third‑party tools pass an email or domain string directly as `{word}` (e.g. `search/user@example.com`), with no query parameters or


**Response (successful hit)**

Official example:[psbdmp](https://psbdmp.ws/api)

json

`[   {    "id": "BMghzZ4b",    "tags": "none",    "length": 393077,    "time": "2018-07-14 02:12",    "text": "###.adsbygoogle\r\nflickr.com##.facade-of-protection-neue\r\nhttps://st.prntscr.com/2018/03/20/0706/img/"  },  ... ]`

Third‑party Go client (MOSINT) confirms the same shape:[cocalc](https://cocalc.com/github/alpkeskin/mosint/blob/master/v3/pkg/services/psbdmp/psbdmp.go)

go

``type emailData struct {     ID     string `json:"id"`    Tags   string `json:"tags"`    Length int    `json:"length"`    Time   string `json:"time"`    Text   string `json:"text"` }``

Per‑entry fields:

- `id` (string) – dump id, later usable with `/dump/{id}`

- `tags` (string) – tag.

- `length` (integer) – size metric.

- `time` (string timestamp).

- `text` (string snippet; short preview of content including the search term)


On no hits, tools typically receive `[]` (empty array), inferred from third‑party wrappers’ assumptions.[cocalc](https://cocalc.com/github/alpkeskin/mosint/blob/master/v3/pkg/services/psbdmp/psbdmp.go)

**Supported entity_type(s)**

- Any string term; common use from OSINT tooling is:

    - `email` (e.g. `victim@example.com`).[cocalc](https://cocalc.com/github/alpkeskin/mosint/blob/master/v3/pkg/services/psbdmp/psbdmp.go)

    - `domain` (e.g. `example.com`)


**Classification**

- For `breach_monitor`: `direct_signal_input` (first step to find candidate dumps for an entity).

- For `alias_correlation`: `enrichment_only` (index of places where aliases can be mined).


---

### 7) POST/GET `/api/v3/getbydate` (docs also say `/api/v3/dump/getbydate`)

**Purpose**

Fetch dumps in a given date range, with pagination and error fields.[psbdmp](https://psbdmp.ws/api)

**Execution**

- Docs heading: `POST /api/v3/dump/getbydate`; example actually uses `https://psbdmp.ws/api/v3/getbydate` (inconsistency in path; treat as `unclear`, to be probed in implementation).[psbdmp](https://psbdmp.ws/api)

- Example cURL:[psbdmp](https://psbdmp.ws/api)

    bash

    `curl -X POST -d "from=12.01.2018&to=13.01.2018" https://psbdmp.ws/api/v3/getbydate`

- Method supports both GET and POST according to docs.[psbdmp](https://psbdmp.ws/api)

- `from`, `to` appear to be in `DD.MM.YYYY` format (note difference from `/date/:date`).[psbdmp](https://psbdmp.ws/api)


**Response (example)**

json

`{   "current_page": 1,  "data": [    { "id": "XV6bMGMK", "tags": "none", "date": 1515715202 },    { "id": "1vyiqCVd", "tags": "none", "date": 1515715203 },    { "id": "8vgSi4iF", "tags": "none", "date": 1515715203 }  ],  "first_page_url": "https://psbdmp.ws/api/v3/getbydate?from=12.01.2018&to=13.01.2018&page=1",  "from": 1,  "last_page": 639,  "last_page_url": "https://psbdmp.ws/api/v3/getbydate?from=12.01.2018&to=13.01.2018&page=639",  "links": [],  "next_page_url": "https://psbdmp.ws/api/v3/getbydate?from=12.01.2018&to=13.01.2018&page=2",  "path": "https://psbdmp.ws/api/v3/getbydate",  "per_page": 100,  "prev_page_url": null,  "to": 100,  "total": 63880 }`

Docs also state: “If all ok `error` field will be 0 (and no `error_info`).” but the example body shown omits these fields, so presence of `error`/`error_info` is _documented but not exemplified_.[psbdmp](https://psbdmp.ws/api)

**Classification**

- For both modules: `utility_only` (bulk backfill; not needed for real‑time entity‑centric monitoring).


---

### 8) Legacy `psbdmp.cc` API (for context only)

SpiderFoot’s `sfp_psbdmp` module uses `https://psbdmp.cc/api/search/email/{email}` and `/search/domain/{domain}` to retrieve Pastebin IDs for hacked emails/domains, then fetches the actual paste from `pastebin.com`.[github](https://github.com/smicallef/spiderfoot/blob/master/modules/sfp_psbdmp.py)

- This shows historical existence of email/domain‑specific search endpoints on the `.cc` domain, but current official docs for `.ws` only document the generic `/search/:word`

- For Zima, treat the `.cc` API as **legacy and third‑party-described**; do not rely on email/domain subpaths unless validated at runtime.


---

## B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|alias_correlation|signal_producer|search|GET `/api/v3/search/:word`|enrichment_only|email, domain|Only call with normalized seed email or domain; treat returned dump IDs as locations where the seed string appears, not as proof of compromise; do not emit standalone signals from this module.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api); MOSINT psbdmp.go [cocalc](https://cocalc.com/github/alpkeskin/mosint/blob/master/v3/pkg/services/psbdmp/psbdmp.go); ernest PsbdmpAPI const [pkg.go](https://pkg.go.dev/github.com/b0gdan-iacob/ernest/cmd/utils)|Use results to drive secondary fetches for alias mining; empty array (`[]`) means “no hit”; handle gracefully.|
|alias_correlation|signal_producer|dump|GET `/api/v3/dump/{id}`|enrichment_only|email, domain|Only fetch dumps referenced by `search` for the module’s seed; parse `content` to extract additional emails, domains, usernames; never on its own create a breach/credential signal here.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|Preserve full `content` for offline alias extraction and correlation; note that dump content may include many unrelated entities.|
|alias_correlation|signal_producer|today / yesterday|GET `/api/v3/today`,`/yesterday`|out_of_scope|none|Do not use in this module; these are global feeds, not keyed to a specific identity or domain.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|Could be revisited for a future “global alias discovery” feature, but noisy and hard to tie back to a seed entity.|
|alias_correlation|signal_producer|date|GET `/api/v3/date/:date`|utility_only|none|Optional backfill to pre‑warm alias graphs when onboarding a customer, but not needed in main correlation pipeline.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|Use only in offline jobs; do not run continuously due to unknown rate limits and eventual project shutdown notice.|
|alias_correlation|signal_producer|getbydate|POST/GET `/api/v3/getbydate`|utility_only|none|Same as `/date`; only for bulk historical crawling; ignore `error`/`error_info` until actual responses are observed and parsed.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|Path inconsistency (`/dump/getbydate` vs `/getbydate`) must be probed; treat as brittle.|
|breach_monitor|signal_producer|search|GET `/api/v3/search/:word`|direct_signal_input|email, domain|Only seed with validated customer identifiers; if `search` returns no results, do not emit any signal; if it returns IDs, move to `dump` inspection before deciding on signal creation.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api); MOSINT psbdmp.go [cocalc](https://cocalc.com/github/alpkeskin/mosint/blob/master/v3/pkg/services/psbdmp/psbdmp.go); SpiderFoot sfp_psbdmp using search-by-email/domain [github](https://github.com/smicallef/spiderfoot/blob/master/modules/sfp_psbdmp.py)|Treat search hits as _candidate_ evidence; a hit alone is not a breach and must not be turned into a “breach” signal without inspecting dump content.|
|breach_monitor|signal_producer|dump|GET `/api/v3/dump/{id}`|direct_signal_input|email (primary)|After `search`, fetch each dump; only create a credential‑exposure signal if `content` both contains the seed email and matches Zima’s credential/PII patterns; otherwise, treat as enrichment only.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|`content` is free text; you must implement your own parsing for `email:password` combos, hashes, etc.; psbdmp does not classify dumps by type or breach severity.|
|breach_monitor|signal_producer|today / yesterday|GET `/api/v3/today`,`/yesterday`|out_of_scope|none|Do not use in current design; no direct mapping to a specific monitored identity, and too noisy as alert source.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|Could serve a future “global dark‑paste monitoring” module but not appropriate for customer‑scoped breach alerts.|
|breach_monitor|signal_producer|date / latest|GET `/api/v3/date/:date`,`/latest/:num`|utility_only|none|Optional bulk backfill for building a historical model of psbdmp‑visible breaches; not used for per‑customer, per‑entity alerts in real time.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|Use sparingly due to unknown rate limits and project sunset; prioritize on‑demand `search` queries instead.|
|breach_monitor|signal_producer|getbydate|POST/GET `/api/v3/getbydate`|utility_only|none|Same as above; used only if you implement large‑scale crawling of psbdmp; not necessary for first‑pass breach monitoring based on per‑entity search.|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api)|Given the shutdown notice, building long‑running crawlers around this endpoint is risky; prefer minimal, opportunistic use or skip.|

---

## C. Signal Contract Table

Only one psbdmp‑backed signal is recommended as a standalone alert in this phase; all other uses (including “paste mention without clear credentials”) should remain enrichment‑only for Zima.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|breach_monitor|breach_monitor|psbdmp|`GET /api/v3/search/:word` + `GET /api/v3/dump/{id}`|credential_exposed_in_paste_dump|identity_security|critical|yes|If Zima’s content parser classifies at least one extracted credential for the target email as plaintext, set severity to critical; if only hashed/obfuscated secrets are detected, treat as high; if only a mention with no credential pattern is present, do not emit this signal (keep as enrichment only).|email|true_finding|For a monitored email address `E`: (1) `GET /api/v3/search/E` returns at least one entry; (2) for at least one returned `id`, `GET /api/v3/dump/{id}` returns a JSON object where `content` contains `E`; and (3) Zima’s parser finds one or more password or credential artifacts associated with `E` in `content` (e.g., `E:password`, `E;password`, or equivalent combos as defined by internal patterns).|From `search`: each hit’s `id`, `tags`, `length`, `time`, `text`; from `dump`: `id`, `tags`, `date`, `content` for the dump(s) that satisfied the parser; optionally the list of parsed credential lines/snippets and internal parser classification (plaintext vs hashed) as separate internal fields.|From `dump`/`search`: dump timestamps (`date` or `time`), `length`, and `tags`; optionally an internally constructed `psbdmp_dump_url` (e.g., `https://psbdmp.ws/dump/{id}`) for analyst triage, clearly marked as derived, not provider-native.|"Credential(s) for {{email}} appear exposed in a Pastebin dump indexed by psbdmp (dump ID {{dump_id}})."|derived|[https://psbdmp.ws/api](https://psbdmp.ws/api) [psbdmp](https://psbdmp.ws/api); MOSINT psbdmp.go (search response fields) [cocalc](https://cocalc.com/github/alpkeskin/mosint/blob/master/v3/pkg/services/psbdmp/psbdmp.go); SpiderFoot sfp_psbdmp (using psbdmp for hacked emails) [github](https://github.com/smicallef/spiderfoot/blob/master/modules/sfp_psbdmp.py)|psbdmp does not label dumps as “credential dumps”; this signal relies entirely on Zima’s own parsing of `content` to determine whether a dump actually exposes credentials versus merely mentioning the email.[psbdmp](https://psbdmp.ws/api) The API returns full content for a dump via `/dump/{id}` but only a short `text` preview in `search` responses.[psbdmp](https://psbdmp.ws/api) False positives are likely if parsing is naive; you must maintain strict patterns and consider decaying severity over time (e.g., older than 12–24 months). The API’s long‑term availability is uncertain due to the shutdown notice, so this signal should be designed to fail closed (no signals) if psbdmp becomes unavailable.[psbdmp](https://psbdmp.ws/api)|

**Evidence status**

- `search`/`dump` fields and shapes are **documented** in psbdmp’s public API page and confirmed by MOSINT’s client

- The trigger condition and severity logic are **derived** from these fields and Zima’s own credential‑pattern heuristics (psbdmp does not provide any “breach” flag).


**Why no separate “paste_mention_without_credentials” signal**

- A mere mention of an email or domain in a paste is ambiguous (could be spam lists, logs, or benign references), so it should be treated as enrichment for correlation rather than a standalone breach signal to avoid alert fatigue.


---

## D. Severity Rules (per signal)

For `credential_exposed_in_paste_dump`:

- **Base severity:**

    - **critical** when the parser confirms plaintext credentials (matches your “direct credential exposure, plaintext passwords” definition).[psbdmp](https://psbdmp.ws/api)

- **Conditional downgrade:**

    - **high** if only strong evidence of hashed passwords/secrets is present (e.g., consistent hash-length strings mapped to the email), still indicating direct credential exposure but without guaranteed immediate reuse.

    - **no signal** (enrichment only) if only an email/domain mention is detected with no adjacent credential or sensitive data pattern.

- **Temporal considerations (recommended):**

    - You may want to decay severity for very old dumps (e.g., downgrade to medium for dumps older than N months), but psbdmp does not prescribe this; it’s a Zima policy decision based on `date`/`time` fields.[psbdmp](https://psbdmp.ws/api)


Your initial “0.65–0.75” confidence note is broadly consistent with this: treat psbdmp as moderately reliable for _finding_ potential leaks, but highly dependent on your own parsing and corroboration for _confirming_ them.

---

## E. Confidence Guidance Table

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|alias_correlation|Using `search` + `dump` to mine aliases|Single‑maintainer OSINT project; dataset is large (28M+ dumps) but coverage is limited to Pastebin content that psbdmp collected, and there is an explicit notice that the project will be shut  Treat as opportunistic, not canonical.|`time` and `date` fields give when psbdmp saw the dump, not necessarily when the underlying breach occurred; dumps can be reposts or compilations.[psbdmp](https://psbdmp.ws/api) For alias graphs, recency matters less, but you should still tag aliases with discovery date and optionally age‑weight them in correlation scoring.|Only use aliases discovered in psbdmp as weak links until corroborated by additional sources (e.g., same alias appears in structured breach DBs or customer telemetry). Use frequency across multiple dumps and sources as a signal of stronger correlation.|Track how often psbdmp‑derived aliases later appear in confirmed breach data or internal logs; adjust how much weight alias_correlation gives to psbdmp‑only links (likely low/medium). Consider A/Bing correlation scoring with and without psbdmp aliases on real investigations.|
|breach_monitor|`credential_exposed_in_paste_dump`|psbdmp indexes real Pastebin content and provides full dump text, but does not verify or annotate leaks.[psbdmp](https://psbdmp.ws/api) Some third‑party tools rely on it for hacked‑email discovery, indicating practical but imperfect |Dumps may be years old; psbdmp’s dataset includes entries from 2015 onwards, and recency is only visible via `date`/`time` in each record.[psbdmp](https://psbdmp.ws/api) Older dumps should likely have reduced severity/priority; also, the shutdown notice suggests that the dataset may become static or disappear.|Require both psbdmp evidence _and_ at least one corroborating signal where possible: another breach provider confirming the same email/domain, repeated psbdmp occurrences across independent dumps, or customer telemetry showing credential misuse (login anomalies) after the paste’s date.|Run the parser on a large sample of psbdmp dumps containing known test accounts and measure precision/recall for credential detection. Use labelled internal test accounts intentionally leaked in controlled dumps to tune patterns. Record false positive/negative rates per pattern family and adjust severity thresholds accordingly.|
|breach_monitor|psbdmp hits as enrichment-only (paste mention)|Same as above; however, using mere mentions as signals is especially risky due to unclear context; treat single-source, single‑dump mentions with low base trust.|Mentions without credentials can still be long‑lived or reflect reputational issues (e.g., doxing), but they’re weak indicators of account takeover risk; consider age‑based decay even more aggressively here.|Only surface paste mentions as explicit alerts if: (a) the customer opts in, and (b) there is corroborating context such as targeted language, PII patterns, or other OSINT sources mentioning the same entity. Default posture: keep as context attached to other, stronger alerts.|Instrument an opt‑in rule for paste mentions and log analyst feedback (dismiss vs escalate). Use this to decide whether to ever promote a separate “paste_mention” signal type or leave it permanently as enrichment only.|

---

## F. Tags per Signal Type

For `credential_exposed_in_paste_dump`:

- `["breach", "plaintext_password", "credential_stuffing", "pii_exposure"]`

    - Use `plaintext_password` only when your parser believes the passwords are in cleartext; otherwise you may drop that tag at runtime and keep `breach` + `credential_stuffing`.


No other standalone signals are defined, so no additional tag sets are required at this stage.

---

## G. Provider Summary for Zima

### Strongest signal types

- **Direct credential exposures in Pastebin dumps:**

    - When `search` finds dumps for a monitored email and `/dump/{id}` content clearly exposes `email:password`‑style combos, psbdmp can provide high‑value evidence of credential compromise, often earlier than mainstream breach

- **Alias discovery from dump content:**

    - Parsing `content` for additional emails, usernames, or domains provides useful OSINT for alias_correlation, helping link identities across leak ecosystems.[psbdmp](https://psbdmp.ws/api)


### What psbdmp should **not** be used for

- As a canonical breach catalog or ground truth for “has this account ever been breached?” – its coverage is limited to Pastebin and whatever the maintainer scraped, not to all public

- For structured PII classification or breach taxonomy – there are no type fields or labels in the API; everything is raw text.[psbdmp](https://psbdmp.ws/api)

- For long‑term, mission‑critical workflows – the API announces an impending permanent shutdown and offers the dataset for sale, so API availability and update cadence are not guaranteed.[psbdmp](https://psbdmp.ws/api)


### API/auth/rate‑limit/licensing cautions

- **Auth & rate limits:**

    - No authentication or rate‑limit headers are documented on the public API page; third‑party tools call it anonymously and treat the model as “FREE_NOAUTH_UNLIMITED” in SpiderFoot metadata, but this is not a formal SLA. Build clients with backoff, concurrency limits, and failure‑tolerant

- **Licensing / dataset sale:**

    - The API page explicitly offers the full dataset for exclusive acquisition and states that it will not be made public after sale, with no redistribution rights; this implies that API access may cease once a buyer is found. Ensure Zima’s legal/licensing stance is clear before relying heavily on psbdmp data.[psbdmp](https://psbdmp.ws/api)


### Overall role in Zima

- In the current stage, psbdmp should be treated as a **signal-producing OSINT source** for _credential_exposed_in_paste_dump_ in the `breach_monitor` module, with strong gating and corroboration.

- For `alias_correlation`, psbdmp is **enrichment-only**: it provides additional identifiers and context but should not by itself generate alerts.

- Most other endpoints (`today`, `yesterday`, `date`, `latest`, `getbydate`) are **utility-only** for optional bulk crawling/backfill and are not required for the core per‑entity workflow.


---

## H. Structured JSON

json

`{   "provider": "psbdmp",  "provider_category": "breach",  "provider_role": "signal_producer",  "module_mappings": [    {      "module": "alias_correlation",      "provider_role": "signal_producer",      "provider_method": "search",      "endpoint_or_artifact": "GET /api/v3/search/:word",      "classification": "enrichment_only",      "entity_types": ["email", "domain"],      "gating_logic": "Only call with normalized seed email or domain; treat returned dump IDs as locations where the seed string appears, not as proof of compromise; do not emit standalone signals from this module.",      "citation_refs": ["https://psbdmp.ws/api ", "MOSINT psbdmp.go ", "ernest PsbdmpAPI const "],      "notes": "Use results to drive secondary fetches for alias mining; empty array ([]) means no hit. Handle safely if the service becomes unavailable due to the announced shutdown."    },    {      "module": "alias_correlation",      "provider_role": "signal_producer",      "provider_method": "dump",      "endpoint_or_artifact": "GET /api/v3/dump/{id}",      "classification": "enrichment_only",      "entity_types": ["email", "domain"],      "gating_logic": "Only fetch dumps referenced by search for the module’s seed; parse content to extract additional emails, domains, usernames; never on its own create a breach/credential signal here.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Preserve full content for offline alias extraction and correlation; dump content may include many unrelated entities."    },    {      "module": "alias_correlation",      "provider_role": "signal_producer",      "provider_method": "today_yesterday",      "endpoint_or_artifact": "GET /api/v3/today, GET /api/v3/yesterday",      "classification": "out_of_scope",      "entity_types": [],      "gating_logic": "Do not use in this module; these are global feeds not keyed to a specific identity or domain.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Could be revisited for a future global alias discovery feature but likely too noisy."    },    {      "module": "alias_correlation",      "provider_role": "signal_producer",      "provider_method": "date",      "endpoint_or_artifact": "GET /api/v3/date/:date",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Optional backfill to pre-warm alias graphs when onboarding a customer; not needed in main correlation pipeline.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Use only in offline jobs; beware unknown rate limits and long-term availability."    },    {      "module": "alias_correlation",      "provider_role": "signal_producer",      "provider_method": "getbydate",      "endpoint_or_artifact": "POST/GET /api/v3/getbydate (docs also mention /api/v3/dump/getbydate)",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Only for bulk historical crawling; ignore error/error_info until actual responses are observed.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Path inconsistency must be probed at runtime; treat as brittle and avoid in critical paths."    },    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "search",      "endpoint_or_artifact": "GET /api/v3/search/:word",      "classification": "direct_signal_input",      "entity_types": ["email", "domain"],      "gating_logic": "Only seed with validated customer identifiers. If search returns no results, do not emit any signal; if it returns IDs, move to dump inspection before deciding on signal creation.",      "citation_refs": ["https://psbdmp.ws/api ", "MOSINT psbdmp.go ", "SpiderFoot sfp_psbdmp "],      "notes": "Treat search hits as candidate evidence only; a hit alone is not a breach. Use as the first hop in the psbdmp workflow."    },    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "dump",      "endpoint_or_artifact": "GET /api/v3/dump/{id}",      "classification": "direct_signal_input",      "entity_types": ["email"],      "gating_logic": "After search, fetch each dump; only create a credential-exposure signal if content both contains the seed email and matches Zima’s credential/PII patterns; otherwise, record as enrichment only.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Requires robust internal parsing logic. psbdmp does not categorize dumps by leak type."    },    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "today_yesterday",      "endpoint_or_artifact": "GET /api/v3/today, GET /api/v3/yesterday",      "classification": "out_of_scope",      "entity_types": [],      "gating_logic": "Do not use in current design; no direct mapping to a monitored identity and too noisy as an alert source.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Consider only for future global dark-paste monitoring features."    },    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "date_latest",      "endpoint_or_artifact": "GET /api/v3/date/:date, GET /api/v3/latest/:num",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Optional bulk backfill for building a historical view of psbdmp-visible breaches; not needed for real-time per-entity alerts.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Use sparingly due to unknown rate limits and the provider’s planned shutdown."    },    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "getbydate",      "endpoint_or_artifact": "POST/GET /api/v3/getbydate",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Only if you implement large-scale crawling; not necessary for per-entity breach monitoring.",      "citation_refs": ["https://psbdmp.ws/api "],      "notes": "Given the shutdown notice and path inconsistency, using this heavily is risky."    }  ],  "signal_contracts": [    {      "module": "breach_monitor",      "source": "breach_monitor",      "provider": "psbdmp",      "provider_method": "GET /api/v3/search/:word + GET /api/v3/dump/{id}",      "signal_type": "credential_exposed_in_paste_dump",      "category": "identity_security",      "severity": "critical",      "severity_is_conditional": "yes",      "conditional_rule": "If the internal parser classifies at least one extracted credential for the target email as plaintext, keep severity critical; if only hashed or obfuscated secrets are detected, downgrade to high; if only a mention with no credential pattern is present, do not emit this signal (keep as enrichment only).",      "entity_type": "email",      "finding_kind": "true_finding",      "trigger_condition": "For a monitored email address E: (1) GET /api/v3/search/E returns at least one entry; (2) for at least one returned id, GET /api/v3/dump/{id} returns JSON where content contains E; and (3) the parser finds one or more password or credential artifacts associated with E in content (for example E:password or equivalent combos as defined by Zima patterns).",      "evidence_fields": [        "search[].id",        "search[].tags",        "search[].length",        "search[].time",        "search[].text",        "dump.id",        "dump.tags",        "dump.date",        "dump.content",        "parsed_credentials[] (internal)"      ],      "enrichment_fields": [        "dump.date",        "search[].time",        "search[].length",        "search[].tags",        "derived.psbdmp_dump_url"      ],      "summary_template": "Credential(s) for {{email}} appear exposed in a Pastebin dump indexed by psbdmp (dump ID {{dump_id}}).",      "evidence_status": "derived",      "citation_refs": [        "https://psbdmp.ws/api ",        "MOSINT psbdmp.go ",        "SpiderFoot sfp_psbdmp "      ],      "notes": "psbdmp provides raw dump content but no breach classification; all leak detection is done by Zima’s parser. Old dumps may still indicate compromised credentials but severity should likely decay with age. The provider has announced a future shutdown and dataset sale, so the client must handle permanent unavailability without breaking the module."    }  ],  "confidence_guidance": [    {      "module": "alias_correlation",      "signal_type_or_use_case": "psbdmp search+dump for alias mining",      "source_reliability": "Large but single-maintainer OSINT index of Pastebin dumps; coverage limited to what has been scraped, with an explicit shutdown notice. Treat as opportunistic rather than authoritative.",      "freshness_considerations": "time/date show when psbdmp saw the dump, not breach date. Age is less critical for alias graphs but should still be recorded.",      "corroboration_rules": "Treat psbdmp-only aliases as weak links until seen in other breach or telemetry sources. Use occurrence frequency across multiple dumps/sources to strengthen confidence.",      "calibration_todo": "Measure how often psbdmp-derived aliases later appear in confirmed breach data or internal logs; down-weight if correlation is weak."    },    {      "module": "breach_monitor",      "signal_type_or_use_case": "credential_exposed_in_paste_dump",      "source_reliability": "psbdmp returns real Pastebin content but does not validate leaks. Third-party tools use it for hacked-email discovery, indicating practical but imperfect reliability.",      "freshness_considerations": "Dumps can be many years old; severity should likely decay for very old dumps. The dataset may become static or go offline after sale.",      "corroboration_rules": "Prefer raising strongest confidence when psbdmp evidence is corroborated by another breach source or by customer telemetry showing post-dump credential abuse.",      "calibration_todo": "Run the parser on large psbdmp samples with test accounts; track precision/recall and adjust patterns and severity thresholds accordingly."    },    {      "module": "breach_monitor",      "signal_type_or_use_case": "psbdmp paste mention as enrichment",      "source_reliability": "Mentions without credentials are particularly ambiguous and should be considered low-trust indicators.",      "freshness_considerations": "Old mentions still have reputational implications but weak security impact; decay their weight quickly.",      "corroboration_rules": "Only promote mentions toward alerts when combined with targeted language, PII patterns, or confirmations from other OSINT sources; otherwise keep as enrichment context.",      "calibration_todo": "If you add an opt-in mention rule, capture analyst disposition to decide whether to keep or drop it as an alert type."    }  ] }`
