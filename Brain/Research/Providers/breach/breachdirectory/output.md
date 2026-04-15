---
title: "output / breach / breachdirectory"
aliases: ["breachdirectory output", "breachdirectory signal registry"]
tags: [zima, research, outputs, signal-registry, breach, breachdirectory]
type: provider_research_output
provider: breachdirectory
provider_category: breach
status: complete
prompt_note: prompt.md
provider_folder: breachdirectory.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---
# BreachDirectory Provider Research Notes

## A. API Surface Appendix

### 1. `GET https://breachdirectory.com/api_usage`

#### Purpose

Primary query endpoint controlled by query parameters:

- `method=$Method` — selects which backend dataset/search mode to use. [breachdirectory](https://breachdirectory.com/documentation)
- `key=$Key` — API key, required. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)
- `query=$Query` — search term (email, username, IP, etc., depending on method). [breachdirectory](https://breachdirectory.com/documentation)

Example pattern: [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

```text
https://breachdirectory.com/api_usage?method=$Method&key=$Key&query=$Query
```

If parameters are missing or invalid, the endpoint returns human-readable text errors rather than JSON, including: [breachdirectory](https://breachdirectory.com/documentation)

- `A search method is required.`

- `An API key is required.`

- `You have exceeded the limit of queries allowed for your API key.`

- `Invalid or expired API key.`

- `A search query is required.`


These should be treated as hard errors rather than no-hit responses. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

---

### 1.1 Core breach search (data breaches)

Docs state: “BreachDirectory allows anyone to search for an email address, IP address, or a username through its extensive list of data breaches.” [breachdirectory](https://breachdirectory.com/documentation)

When searching breach data, a successful hit returns a JSON array of breach objects. Example: [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

```json
[
  {
    "title": "Data Breach #1",
    "domain": "a.com",
    "email": "[email protected]",
    "username": "Username",
    "ip": "127.0.0.1"
  },
  {
    "title": "Data Breach #2",
    "domain": "b.com",
    "email": "[email protected]",
    "username": "Demouser",
    "ip": "127.0.0.1"
  }
]
```

Response characteristics:

- Top-level: JSON array

- Fields per entry (all strings):

    - `title` — breach name or label. [breachdirectory](https://breachdirectory.com/documentation)

    - `domain` — affected site domain. [breachdirectory](https://breachdirectory.com/documentation)

    - `email` — breached email, if present. [breachdirectory](https://breachdirectory.com/documentation)

    - `username` — breached username, if present. [breachdirectory](https://breachdirectory.com/documentation)

    - `ip` — associated IP, if present. [breachdirectory](https://breachdirectory.com/documentation)


The docs do **not** state which `method` value triggers this core data-breach behavior. They only document the generic `method=$Method` parameter and state that breach searching is supported. Treat the method value as **undocumented/unknown** and determine it empirically per account. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

#### Response variants

- Hit: HTTP 200 with non-empty JSON array as above. [breachdirectory](https://breachdirectory.com/documentation)

- No-hit: HTTP 200 with `[]` or `false`. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

- Error: HTTP 200 or other status with one of the text error messages above. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)


No official example includes password or hash fields in this core breach response. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

---

### 1.2 `method=expanded` (expanded breach DB)

Docs state: “If you're searching through the expanded breach database, specify `expanded` as the search method… If results do exist, the API will return results from data breach data from sources other than BreachDirectory.” [breachdirectory](https://breachdirectory.com/documentation)

Example output is shown in mixed PHP-style notation: [breachdirectory](https://breachdirectory.com/documentation)

```text
[
  { Source: "breach title"
    Array (
      [email]    => [email protected]
      [username] => demo
      [ip]       => 127.0.0.1
      [created]  => 2026-01-01 00:00:00.00
    )
  },
  ...
]
```

This implies, based on the docs example only:

- Hit: non-empty collection of entries, each with:

    - `Source` — breach title or external source label. [breachdirectory](https://breachdirectory.com/documentation)

    - `email`, `username`, `ip` — identifiers for the record. [breachdirectory](https://breachdirectory.com/documentation)

    - `created` — timestamp string. [breachdirectory](https://breachdirectory.com/documentation)

- No-hit: possibly `No results found.` or `[]`; exact behavior is not explicitly specified for `expanded`. [breachdirectory](https://breachdirectory.com/documentation)


Exact JSON key casing and structure should be confirmed from real responses.

---

### 1.3 `method=general` (Pastebin / paste search)

Docs state: “If you're searching through the Pastebin database, specify `general` as the search method.” [breachdirectory](https://breachdirectory.com/documentation)

Hit example: [breachdirectory](https://breachdirectory.com/documentation)

```json
[
  {
    "id": "id-from-pastebin",
    "tags": "none",
    "length": 4,
    "time": "2019-04-30 09:30",
    "text": "demo"
  }
]
```

Response characteristics:

- Top-level: JSON array

- Fields:

    - `id` (string) — Pastebin ID

    - `tags` (string)

    - `length` (integer)

    - `time` (string timestamp)

    - `text` (string; full paste content) [breachdirectory](https://breachdirectory.com/documentation)


No-hit response: `No results found.` (string). [breachdirectory](https://breachdirectory.com/documentation)

This method returns free text. Whether it contains credentials depends on downstream parsing.

---

### 1.4 `method=blockchain`

Docs state that `blockchain` searches blockchain addresses such as BTC and ETH. [breachdirectory](https://breachdirectory.com/documentation)

Hit example: [breachdirectory](https://breachdirectory.com/documentation)

```json
{
  "id": "1",
  "address": "112AmFATxzhuSpvtz1hfpa3Zrw3BG276pc",
  "balance": "0.0",
  "total_sent_btc": "50000000.0",
  "total_received_btc": "50000000.0",
  "total_sent_eth": null,
  "total_received_eth": null,
  "total_sent_usd": "210.05",
  "total_received_usd": "211.05",
  "transaction_fees": "4080.128571",
  "transactions_payment": "1",
  "transactions_receipt": "1",
  "sent_counter": "1",
  "received_counter": "2",
  "first_seen": "2016/04/05 17:35",
  "last_seen": "2016/04/07 11:18",
  "about": "Ransomware"
}
```

No-hit response: `No results found.` (string). [breachdirectory](https://breachdirectory.com/documentation)

This is threat-intel or crypto due-diligence data, not directly a credential-breach signal.

---

### 1.5 `method=kev_cve`

Docs state that `kev_cve` searches a KEV/CVE database. A hit returns a JSON object with CVE metadata such as ID, vendor, product, description, required action, due date, CWEs, and related fields. [breachdirectory](https://breachdirectory.com/documentation)

Example fields include:

- `cve_id`

- `vendor_project`

- `product`

- `vulnerability_name`

- `cve_description`

- `cve_requiredaction`

- `cve_duedate`

- `cve_cwes`


No-hit response: `No results found.` (string). [breachdirectory](https://breachdirectory.com/documentation)

This is vulnerability intelligence, not account or credential data.

---

### 1.6 `method=email_disposable`

Docs state that to check whether an email address is disposable, you specify `email_disposable` as the search method. [breachdirectory](https://breachdirectory.com/documentation)

Output values:

- `disposable` — if the domain is disposable

- `not disposable` — otherwise [breachdirectory](https://breachdirectory.com/documentation)


This method does not return JSON. It returns a simple classification string.

---

### 1.7 Other methods (threat actors, darker OSINT)

Docs mention that bulk-plan users gain access to a variety of search methods, including Threat Actors, KEV/CVE lookups, blockchain investigations, and additional dark-web style searches. [breachdirectory](https://breachdirectory.com/documentation)

However, the concrete `method` names and response shapes for Threat Actors and dark-web URL lookups are **not documented** and should be treated as outside the current contract. [breachdirectory](https://breachdirectory.com/documentation)

---

## 2. `GET https://breachdirectory.com/api_file` (Bulk API)

### Purpose

Bulk scanning endpoint. Docs state that if you have access to the bulk API plan, an additional `bulk_url` parameter is required. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

```text
https://breachdirectory.com/api_file?api_method=$Method&api_key=$Key&bulk_url=$URL
```

Parameters:

- `api_method` — search method, similar to `method` in `api_usage`. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

- `api_key` — bulk API key. [breachdirectory](https://breachdirectory.com/)

- `bulk_url` — URL to a `.txt` or `.csv` file containing accounts to search. No `query` parameter is needed when bulk is used. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)


Blog and bulk UI notes clarify:

- Up to approximately 100 accounts per bulk run. Larger files trigger: `File size too big! Consider removing some accounts from the file. We suggest searching for up to 100 accounts at once.` [breachdirectory](https://breachdirectory.com/blog/breachdirectory-enterprise-api/)

- Supported file contents include email addresses, usernames, IP addresses, and domains. [breachdirectory](https://breachdirectory.com/)


The response shape is not fully specified. It likely reuses the same per-account semantics as `api_usage`, grouped per input account. This is **inferred** from docs wording rather than explicitly documented. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

---

## 3. Bulk API Web UI (`/api_bulk`)

The “BreachDirectory – Bulk API Scanner” web UI lets a human operator:

- enter an API key

- upload a CSV with up to 100 accounts

- choose data type such as emails, usernames, IPs, or domains

- view formatted results for copy or export [breachdirectory](https://breachdirectory.com/blog/breachdirectory-enterprise-api/)


This is an operator-facing UI rather than a stable programmatic endpoint. Scraping it is not recommended. [breachdirectory](https://breachdirectory.com/blog/breachdirectory-enterprise-api/)

---

## 4. RapidAPI Host — `https://breachdirectory.p.rapidapi.com/` (Unofficial but widely used)

Several community tools integrate with BreachDirectory through RapidAPI using parameters `func` and `term`, together with RapidAPI headers. [breachdirectory](https://breachdirectory.com/api_bulk)

Example usage: [osintteam](https://osintteam.blog/ebreached-a-simple-osint-tool-to-detect-breached-email-accounts-and-related-passwords-85d755aac828)

```python
url = "https://breachdirectory.p.rapidapi.com/"
params = {"func": "auto", "term": email}
headers = {
  "X-RapidAPI-Key": api_key,
  "X-RapidAPI-Host": "breachdirectory.p.rapidapi.com",
}
```

A RapidAPI support thread documents these functions: [stackoverflow](https://stackoverflow.com/questions/71118739/how-would-i-log-the-hash-values-in-this-api-response)

- `auto` — returns passwords, SHA-1 hashes, and sources given a username or email

- `sources` — returns sources only

- `password` — returns how many times a password was leaked

- `domain` — returns passwords, SHA-1 hashes, and sources for a domain, limited to 1000 results

- `dehash` — attempts to decrypt a given hash


A Go client for this API defines the following response struct: [rapidapi](https://rapidapi.com/rohan-patra/api/breachdirectory/discussions/28352)

```go
type BreachDirectoryResponse struct {
  Success bool `json:"success"`
  Found   int  `json:"found"`
  Result  []struct {
    HasPassword bool     `json:"has_password"`
    Sources     []string `json:"sources"`
    Password    string   `json:"password,omitempty"`
    Sha1        string   `json:"sha1,omitempty"`
    Hash        string   `json:"hash,omitempty"`
  } `json:"result"`
}
```

A StackOverflow-linked example for `func=auto` shows entries such as: [osintteam](https://osintteam.blog/ebreached-a-simple-osint-tool-to-detect-breached-email-accounts-and-related-passwords-85d755aac828)

```json
{
  "result": [
    { "has_password": false, "sources": ["Pluto.tv"] },
    {
      "has_password": true,
      "password": "bleh",
      "hash": "kMUX9351bsMjbgXH9rpKKf+GIYJrJy4=",
      "sources": ["Aptoide.com"]
    },
    {
      "has_password": true,
      "password": "blah",
      "hash": "lEiyXSecP9cIGJfyYhs8yteVEplUIRjAvaI7Jc76upI=",
      "sources": ["Collection 1"]
    }
  ]
}
```

Community tools such as `passfind` and `eBreached` explicitly describe this API as returning cleartext passwords, hashes, and leak sources. [pkg.go](https://pkg.go.dev/github.com/DannyLuu/mosint/v3/pkg/services/breachdirectory)

Because this interface is mediated through RapidAPI and not documented on `breachdirectory.com`, its schema should be treated as **inferred from examples and non-authoritative**.

### Inferred response variants

- Hit: `success=true`, `found > 0`, non-empty `result` array with `has_password`, `sources`, and optional `password`, `sha1`, or `hash`. [rapidapi](https://rapidapi.com/rohan-patra/api/breachdirectory/discussions/28352)

- No-hit: likely `success=true`, `found=0`, `result=[]`; some tools also mention HTTP 500 being used for no-records or internal errors, so semantics are unclear. [breachdirectory](https://breachdirectory.com/api_bulk)

- Error: HTTP 4xx or 5xx with RapidAPI error payload when key is invalid or quota is exceeded. [breachdirectory](https://breachdirectory.com/api_bulk)


---

## B. Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|breach_monitor|signal_producer|Core breach search (undocumented `method` for data breach DB)|`GET /api_usage`|direct_signal_input|email (docs also support username, IP)|Treat as hit only when HTTP 200 body is a non-empty JSON array of objects containing at least `title` and `domain` for the queried identifier; ignore `false`, `[]`, and text error messages as non-hits/errors.|[breachdirectory](https://breachdirectory.com/documentation)|Main per-account breach surface. Passwords and hashes are not documented here; use for “email present in breach” signals.|
|breach_monitor|signal_producer|`method=expanded`|`GET /api_usage`|direct_signal_input|email (also username, IP)|Treat as hit when response contains at least one entry with a `Source` label and one of `email`, `username`, or `ip` matching the monitored account; ignore `No results found.` as no-hit.|[breachdirectory](https://breachdirectory.com/documentation)|Extends coverage with third-party breach data; schema is loosely shown and should be validated from live responses.|
|breach_monitor|signal_producer|`method=general` (Pastebin)|`GET /api_usage`|enrichment_only|email, username, strings in pastes|Use only as enrichment when paste content clearly includes the monitored email; do not emit standalone breach signals from paste presence alone.|[breachdirectory](https://breachdirectory.com/documentation)|High-noise free text; better for analyst context than automated high-severity alerts.|
|breach_monitor|signal_producer|`method=kev_cve`|`GET /api_usage`|out_of_scope|CVE ID, vendor, product|Exclude from `breach_monitor`; no direct account or credential semantics.|[breachdirectory](https://breachdirectory.com/documentation)|Candidate for a future vulnerability or threat-intel module.|
|breach_monitor|signal_producer|`method=blockchain`|`GET /api_usage`|out_of_scope|blockchain address|Exclude from `breach_monitor`; results describe blockchain activity rather than user credentials.|[breachdirectory](https://breachdirectory.com/documentation)|Candidate for ransomware or crypto-intel module.|
|breach_monitor|signal_producer|`method=email_disposable`|`GET /api_usage`|utility_only|email|Use only to derive an `is_disposable_domain` enrichment flag; return string `disposable` or `not disposable` must not generate standalone breach signals.|[breachdirectory](https://breachdirectory.com/documentation)|Feed into risk scoring and correlation, not alerts.|
|breach_monitor|signal_producer|Bulk API|`GET /api_file`|utility_only|email (also username, IP, domain)|Use to batch up to approximately 100 identifiers per run; map each per-identifier result back into the same signal logic as single `api_usage` calls and deduplicate on `(email, breach title/domain)`.|[breachdirectory](https://breachdirectory.com/api_documentation?lang=en)|Ingestion mechanism only; semantics are intended to mirror single search with file-size guardrails.|
|breach_monitor|signal_producer|RapidAPI `func=auto` (if chosen)|`GET https://breachdirectory.p.rapidapi.com/`|direct_signal_input|email, username, domain|Treat as hit only if `success=true`, `found>0`, and `result` array is non-empty; derive password exposure from `has_password` and `password` fields per entry.|[stackoverflow](https://stackoverflow.com/questions/71118739/how-would-i-log-the-hash-values-in-this-api-response)|Rich credential data but on a non-first-party host; treat schema as inferred and watch for instability.|
|breach_monitor|signal_producer|Bulk UI|`/api_bulk` web UI|out_of_scope|email, username, IP, domain|Do not automate the UI; rely on `api_file` instead.|[breachdirectory](https://breachdirectory.com/blog/breachdirectory-enterprise-api/)|Human-oriented interface only.|

---

## C. Signal Contract Table

Only one standalone signal should be emitted by `breach_monitor` from this provider.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|breach_monitor|breach_monitor|breachdirectory|`api_usage` (core breach search + `expanded`); optionally RapidAPI `func=auto`|`credential_breach_found`|identity_security|high|yes|Base severity is high whenever any breach record exists for the monitored email. Escalate to critical if any record includes direct password material, for example RapidAPI `result[].has_password == true` with non-empty `password`. Optionally downgrade to medium for very old breaches once reliable `created` or breach-date metadata is available.|email|true_finding|Official API: HTTP 200 and body is a non-empty array for breach or `expanded` search, with at least one object whose `email` or `username` matches the monitored identifier and has non-empty `title`, `domain`, or `Source`. RapidAPI: `success == true`, `found > 0`, and at least one `result[]` entry exists for the monitored email, username, or domain.|Core and expanded: `title`, `domain`, `email`, `username`, `ip`, and any `Source` or `created` fields present. RapidAPI: `success`, `found`, and full `result[]` entries including `has_password`, `sources`, `password`, `sha1`, and `hash` where present.|Normalized breach list, `is_disposable_domain` from `email_disposable`, and IDs of any clearly linked pastes from `method=general`.|`Credential for {{email}} appears in {{breach_count}} known data breaches indexed by BreachDirectory (password exposure: {{password_exposure_status}}).`|mixed|[breachdirectory](https://breachdirectory.com/documentation)|Use a single internal signal type for all breach surfaces from this provider. Passwords and hashes should be encrypted or otherwise strongly protected in storage.|

Additional notes:

- **Severity rationale:** presence of an email in any breach is a confirmed exposure event, so baseline severity is high; accessible password material justifies critical. [pkg.go](https://pkg.go.dev/github.com/DannyLuu/mosint/v3/pkg/services/breachdirectory)

- Do **not** create separate vendor-specific signal types for `expanded` versus core; they represent the same conceptual finding.


---

## D. Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|breach_monitor|`credential_breach_found` from core or expanded `api_usage`|BreachDirectory presents itself as a large breach search engine indexing many billions of records and is widely used by OSINT tools, implying good coverage but unclear completeness and curation standards. Metadata fields are simple and low-ambiguity. [breachdirectory](https://breachdirectory.com/documentation)|Core breach examples do not expose explicit date fields. Only the `expanded` example shows a `created` timestamp, and its exact JSON structure is unclear, so the API often cannot distinguish old from recent breaches. [breachdirectory](https://breachdirectory.com/documentation)|For early rollout, treat a single BreachDirectory hit as enough to flag an account, but seek corroboration from other breach sources or internal telemetry before triggering user-facing resets or broad notifications. Give more weight when the same breach or password appears across multiple providers.|Instrument overlap with other providers, breach-count distributions, and downstream incident outcomes. Use that data to tune alerting thresholds and severity decisions.|
|breach_monitor|`credential_breach_found` with RapidAPI password/hash enrichment|Community tools consistently use the `success`, `found`, and `result[].has_password/password/sources` schema and describe retrieval of cleartext passwords, hashes, and sources, suggesting high semantic reliability but lower infrastructure reliability because the RapidAPI surface is poorly documented and reportedly unstable. [stackoverflow](https://stackoverflow.com/questions/71118739/how-would-i-log-the-hash-values-in-this-api-response)|Password exposure is mostly time-agnostic because password reuse is the main risk. However, the API does not provide structured breach recency, so these results should indicate reuse risk rather than precise compromise timing.|Treat presence of a cleartext password as strong evidence, but still try to confirm through another password corpus, internal auth telemetry, or stealer-log providers before taking aggressive action. Treat RapidAPI-only hits more cautiously.|Track RapidAPI schema stability and error rates. If instability is high, prefer first-party API as canonical and treat RapidAPI-derived password details as best-effort enrichment only.|
|breach_monitor|Disposable-domain enrichment from `method=email_disposable`|Output is deterministic for a given domain, but the underlying disposable-domain list is opaque and may lag newly created services or misclassify edge cases.|The classification itself is stable, but the underlying domain list may drift over time.|Treat this as weak enrichment only and never as a standalone alert trigger. Combine it with breach presence, login behavior, and other intelligence.|Periodically compare outputs against independent disposable-domain lists and adjust weighting if needed.|
|breach_monitor|Paste-based enrichment from `method=general`|Paste integration is real, but mapping any paste result to a specific monitored user can be noisy because pastes often contain many unrelated credentials or arbitrary text.|Pastes may be deleted or may mirror old datasets. Presence in the index does not guarantee active exploitation or accessibility.|Only use as corroboration if the monitored email appears in the paste near credentials or other sensitive data. Otherwise, keep it as analyst context only.|Track whether paste-based enrichment actually correlates with confirmed incidents. Disable or reduce weighting if it proves too noisy.|

---

## E. Provider Summary

### 1. Strongest signal types

- **Primary:** email present in one or more breaches, with per-breach metadata such as `title`, `domain`, and optional `username` or `ip`, from core and expanded `api_usage` searches. [breachdirectory](https://breachdirectory.com/api_documentation?lang=en)

- **High-value enrichment:** direct credential material such as cleartext passwords, hashes, and sources when using RapidAPI `auto` or `domain`, which supports escalation to critical severity for live credential exposure. [rapidapi](https://rapidapi.com/rohan-patra/api/breachdirectory/discussions/28352)


### 2. What BreachDirectory should not be used for in `breach_monitor`

- **Not for vulnerability intelligence:** `method=kev_cve` belongs in a vulnerability or threat-intel module. [breachdirectory](https://breachdirectory.com/documentation)

- **Not for crypto tracking:** `method=blockchain` concerns blockchain addresses and ransomware-style flows rather than user accounts. [breachdirectory](https://breachdirectory.com/documentation)

- **Not as standalone signals:** `method=email_disposable` should remain a risk-scoring enrichment, and `method=general` is too noisy for standalone alerts without further parsing. [breachdirectory](https://breachdirectory.com/documentation)

- **Not via UI scraping:** `/api_bulk` is a human-oriented UI; programmatic integrations should use `api_file` instead. [breachdirectory](https://breachdirectory.com/blog/breachdirectory-enterprise-api/)


### 3. API, auth, rate-limit, and licensing cautions

- API key is mandatory via `key` or `api_key`; errors such as “Invalid or expired API key” and “You have exceeded the limit of queries allowed for your API key” indicate auth or quota issues. [howtechismade](https://www.howtechismade.com/guide/come-scoprire-le-password-di-milioni-di-account-facilmente-funziona/)

- Public docs do not define numeric rate limits. Third-party tools mention varying free-tier limits, so Zima should treat rate limits as configurable rather than hard-coded. [pkg.go](https://pkg.go.dev/github.com/DannyLuu/mosint/v3/pkg/services/breachdirectory)

- Bulk APIs are explicitly constrained to around 100 accounts per file. Larger payloads trigger the documented file-size error, so batching logic should respect that ceiling. [breachdirectory](https://breachdirectory.com/)

- The RapidAPI path has reports of weak documentation and instability. It should not be the sole path for critical production flows where first-party API access is available. [stackoverflow](https://stackoverflow.com/questions/71118739/how-would-i-log-the-hash-values-in-this-api-response)


### 4. Provider role for Zima now

- **Signal-producing:** core and expanded breach searches should directly drive `credential_breach_found` in `breach_monitor`.

- **Enrichment or utility:** disposable classification, paste search, KEV/CVE, blockchain, and bulk ingestion should be treated as enrichment or utility rather than direct alert sources.

- **Optional enrichment:** RapidAPI password and hash fields can materially improve signal quality and trigger critical severity, but should be explicitly marked as schema-inferred and monitored for breakage.


---

## F. Structured JSON

```json
{
  "provider": "breachdirectory",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "core breach search (undocumented method for data breach DB)",
      "endpoint_or_artifact": "GET https://breachdirectory.com/api_usage",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username", "ip"],
      "gating_logic": "Treat as hit only when HTTP 200 body is a non-empty JSON array of objects containing at least `title` and `domain` for the queried identifier. Treat `false`, `[]`, and any plain-text error messages as no-hit/error.",
      "citation_refs": ["web:11", "web:19"],
      "notes": "Primary per-account breach surface; passwords/hashes not documented here."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "method=expanded",
      "endpoint_or_artifact": "GET https://breachdirectory.com/api_usage",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username", "ip"],
      "gating_logic": "Treat as hit when response contains at least one entry with a `Source` label and one of `email`/`username`/`ip` matching the monitored account. Treat `No results found.` as no-hit.",
      "citation_refs": ["web:11"],
      "notes": "Extends coverage with external breach data; exact JSON structure inferred from example."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "method=general (Pastebin)",
      "endpoint_or_artifact": "GET https://breachdirectory.com/api_usage",
      "classification": "enrichment_only",
      "entity_types": ["email", "username"],
      "gating_logic": "Use only when paste content clearly includes the monitored email; do not emit standalone breach signals from presence of pastes alone.",
      "citation_refs": ["web:11"],
      "notes": "High-noise free text; analyst-context only by default."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "method=kev_cve",
      "endpoint_or_artifact": "GET https://breachdirectory.com/api_usage",
      "classification": "out_of_scope",
      "entity_types": ["cve_id"],
      "gating_logic": "Exclude from breach_monitor; maps to vulnerability/threat-intel domain, not credential breaches.",
      "citation_refs": ["web:11"],
      "notes": "Consider for a future vulnerability_intel module."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "method=blockchain",
      "endpoint_or_artifact": "GET https://breachdirectory.com/api_usage",
      "classification": "out_of_scope",
      "entity_types": ["blockchain_address"],
      "gating_logic": "Exclude from breach_monitor; results describe blockchain activity, not account credentials.",
      "citation_refs": ["web:11"],
      "notes": "Candidate for crypto/ransomware tracking module."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "method=email_disposable",
      "endpoint_or_artifact": "GET https://breachdirectory.com/api_usage",
      "classification": "utility_only",
      "entity_types": ["email"],
      "gating_logic": "Map `disposable` / `not disposable` to an enrichment flag; never emit standalone signals from this output.",
      "citation_refs": ["web:11"],
      "notes": "Used only for risk-scoring enrichment."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "bulk API (api_file)",
      "endpoint_or_artifact": "GET https://breachdirectory.com/api_file",
      "classification": "utility_only",
      "entity_types": ["email", "username", "ip", "domain"],
      "gating_logic": "Batch up to ~100 identifiers per `bulk_url` file; map each per-identifier result through the same rules as single `api_usage` and deduplicate.",
      "citation_refs": ["web:19", "web:17", "web:25"],
      "notes": "Ingestion helper; semantics mirror single searches."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "RapidAPI func=auto",
      "endpoint_or_artifact": "GET https://breachdirectory.p.rapidapi.com/",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username", "domain"],
      "gating_logic": "Treat as hit when `success==true`, `found>0`, and `result` array is non-empty; derive password exposure from `has_password` and `password` fields.",
      "citation_refs": ["web:40", "web:34", "web:42", "web:12"],
      "notes": "Schema inferred from third-party code and examples; monitor for changes."
    }
  ],
  "signal_contracts": [
    {
      "module": "breach_monitor",
      "source": "breach_monitor",
      "provider": "breachdirectory",
      "provider_method": "api_usage (core + expanded); optional RapidAPI func=auto",
      "signal_type": "credential_breach_found",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Set severity=high whenever any breach record exists for the monitored email from core or expanded breach searches. Escalate to critical when any record exposes direct password material (e.g. RapidAPI result entry with has_password==true and non-empty password field, or any future documented plaintext password field in first-party API). Optionally downgrade to medium for very old breaches once reliable created/breach-date metadata is available.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "Official API: HTTP 200 with a non-empty array body for the breach or expanded search, containing at least one object whose email/username matches the queried identifier and has non-empty title/domain or Source. RapidAPI (if used): success==true, found>0, and at least one result[] entry exists for the monitored identifier.",
      "evidence_fields": [
        "title",
        "domain",
        "email",
        "username",
        "ip",
        "Source",
        "created",
        "success",
        "found",
        "result[].has_password",
        "result[].sources",
        "result[].password",
        "result[].sha1",
        "result[].hash"
      ],
      "enrichment_fields": [
        "is_disposable_domain (from email_disposable)",
        "paste_ids (from method=general) linked to same email"
      ],
      "summary_template": "Credential for {{email}} appears in {{breach_count}} known data breaches indexed by BreachDirectory (password exposure: {{password_exposure_status}}).",
      "evidence_status": "mixed_documented_and_inferred",
      "citation_refs": ["web:11", "web:19", "web:34", "web:42", "web:35", "web:39"],
      "notes": "Single normalized signal type for all breach-related outputs. Password/hash exposure should be stored with strong protections and used to drive critical severity where appropriate."
    }
  ],
  "confidence_guidance": [
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "credential_breach_found (core/expanded)",
      "source_reliability": "Large, long-running breach search engine with extensive coverage; metadata fields are straightforward but completeness and curation are not externally audited.",
      "freshness_considerations": "Core breach responses have no explicit age metadata; only expanded examples show a created timestamp and its JSON structure is not guaranteed.",
      "corroboration_rules": "For early rollout, corroborate key hits with at least one other breach source or internal telemetry before triggering heavy-weight user actions.",
      "calibration_todo": "Collect distributions of breach counts, overlap with other providers, and real incident correlations; then tune severity thresholds and auto-remediation policies accordingly."
    },
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "credential_breach_found with password/hash (RapidAPI)",
      "source_reliability": "Password/hash fields appear consistently in multiple third-party tools, but RapidAPI surface has limited documentation and some reported instability.",
      "freshness_considerations": "Password exposure may be old or new; API does not expose recency, so treat as persistent reuse risk, not precise compromise time.",
      "corroboration_rules": "Treat cleartext password as strong but still seek corroboration in other password corpora and internal auth telemetry before acting aggressively.",
      "calibration_todo": "Track schema stability and error rate on RapidAPI; if unreliable, bias toward first-party API for core decisions and treat password/hash data as enrichment."
    }
  ]
}
```
