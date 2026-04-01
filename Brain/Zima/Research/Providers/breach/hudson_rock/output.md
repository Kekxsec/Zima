---
title: "output / breach / hudson_rock"
aliases: ["hudson_rock output", "hudson_rock signal registry"]
tags: [zima, research, outputs, signal-registry, breach, hudson_rock, graph_exclude]
type: provider_research_output
provider: hudson_rock
provider_category: breach
status: complete
prompt_note: prompt.md
provider_folder: hudson_rock.md
obsidianUIMode: preview
---
# Hudson Rock integration for Zima stealer_log_exposure module

## Overview

Hudson Rock’s Cavalier Infostealers API exposes several endpoints that search a large database of compromised machines infected by infostealer malware, returning structured “stealer records” containing compromise timestamps, stealer family, machine metadata, captured credentials, and optional directory trees. These records are well aligned with Zima’s `stealer_log_exposure` module and can act as direct signal inputs when searches by domain or email return hits, with OSINT endpoints providing a lightweight but less controllable alternative. [docs.hudsonrock](https://docs.hudsonrock.com/)

---

## A. API Surface Appendix

### A.1 Core Cavalier v3 – Search by Domain (Domain Intelligence)

**Docs / role.** Hudson Rock’s Cavalier Infostealers API lists a “Domain Intelligence” section with a **Search by Domains** endpoint under both Overview and reference navigation, indicating this as the primary domain-centric search for compromised credentials and related intelligence. A changelog entry for a new `dir_tree` field shows a concrete example of the v3 `search-by-domain` request/response. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

**Endpoint (documented).**

- Base: `https://api.hudsonrock.com`

- Path: `/json/v3/search-by-domain` (shown in the changelog request example). [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

- Method: `POST`. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)


**Purpose (documented/derived).**

- Search for compromised credentials and associated stealer logs linked to one or more domains, with filters for employee vs general-user credentials, keyword-based narrowing (for specific apps/URLs), and optional inclusion of directory tree structures from the infected machine. [docs.hudsonrock](https://docs.hudsonrock.com/reference/domains-overview)


**Supported entity types (derived).**

- Primary: `domain` (e.g. `tesla.com`, `teslamotors.com`). The request body shows a `domains` array of strings. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

- Implicitly, each returned record is also associated with machine-level entities (IP, hostname) and accounts (credentials entries), but those are not the primary query key. [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)


**Authentication (documented).**

- Header: `api-key: <API_KEY>`. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

- Standard JSON API headers (`accept: application/json`, `content-type: application/json`) are used in examples. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)


**Request body (documented).**

Example from `New directory tree field` changelog: [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

```json
{
  "domains": [
    "tesla.com",
    "teslamotors.com"
  ],
  "types": ["employees"],
  "keywords": ["sso"],
  "keywords_match": "any",
  "filter_credentials": true,
  "additional_fields": ["dir_tree"]
}
```

Key fields:

- `domains` (array[string], required): Domains to search. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

- `types` (array[string], optional): Shown with `"employees"`; other values are not documented on this page but similar enums appear in Password Search docs with `"employees"` and `"users"`. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

- `keywords` (array[string], optional): Application/URL-related search terms (example uses `"sso"`). [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

- `keywords_match` (string, optional): Example value `"any"`; likely controls whether any/all keywords must match (inferred). [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

- `filter_credentials` (boolean, optional): Example `true`; docs state similar field in Password Search to “return only matched credentials,” so here likely restricts credentials to those matching supplied filters. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

- `additional_fields` (array[string], optional): Example `"dir_tree"` requests inclusion of a directory-tree representation. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)


Presence and semantics of `types`, `keywords_match`, `filter_credentials`, and `additional_fields` are documented via example but not exhaustively specified; treat allowable values and defaults as **unclear** and confirm in live docs. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

**Response structure (documented/derived).**

The changelog shows a response example representing a single stealer record as returned when `dir_tree` is requested: [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

```json
{
  "_id": "67a08ccd465561f4625e840f",
  "stealer": "...",
  "stealer_family": "Lumma",
  "date_uploaded": "2025-02-03T09:30:52.468Z",
  "employeeAt": [ { "..." } ],
  "clientAt":   [ { "..." } ],
  "date_compromised": "2025-01-25T12:03:26.000Z",
  "ip": "...",
  "computer_name": "...",
  "operating_system": "...",
  "malware_path": "...",
  "antiviruses": [ { "..." } ],
  "credentials": [
    {
      "url": "https://sso.tesla.com/adfs/ls",
      "domain": "tesla.com",
      "username": "••••••••••,@tesla.com",
      "password": "••••••••••",
      "type": "employee",
      "password_strength": {
        "contains": ["lowercase", "symbol"],
        "length": 10,
        "id": 1,
        "value": "Weak"
      }
    }
  ],
  "dir_tree": {
    "name": "<REDACTED>",
    "type": "directory",
    "children": [
      {
        "name": "Applications",
        "type": "directory",
        "children": [
          {"name": "Steam",   "type": "directory", "children": [ {"name": "Tokens.txt", "type": "file"}, ... ]},
          {"name": "Discord", "type": "directory", "children": [ {"name": "DiscordTokens.txt", "type": "file"}, {"name": "All Passwords.txt", "type": "file"}, ... ]},
          {"name": "Important Files", "type": "directory", ...}
        ]
      }
    ]
  }
}
```

From this and the “Data Enrichment” / stealer schema material: [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)

- Top-level required (or highly likely) fields:

    - `_id`: string, unique stealer record identifier.

    - `stealer`: string, raw stealer log identifier.

    - `stealer_family`: string, malware family name (e.g., Lumma). [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)

    - `date_uploaded`: ISO datetime when Hudson Rock ingested the data. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

    - `date_compromised`: ISO datetime when the infection occurred / credentials were stolen. [docs.hudsonrock](https://docs.hudsonrock.com/reference/search-by-login-emails)

    - `ip`: string, IP address of the compromised machine. [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)

    - `computer_name`: string.

    - `operating_system`: string.

- Common optional/conditional fields:

    - `employeeAt`: array[object], employment metadata for corporate employees (structure unclear). [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

    - `clientAt`: array[object], likely representing client/customer relationships (structure unclear). [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

    - `malware_path`: string, file path where the stealer binary resided. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

    - `antiviruses`: array[object], installed AV products (structure unclear). [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)

    - `credentials`: array[object], each with URL/domain/login/password and password-strength metadata. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

    - `dir_tree`: object representing a directory tree with `name`, `type` (`"directory"` or `"file"`), and recursive `children`. [docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)


The `stealer_family` and `ip` fields and their text descriptions are also documented in Hudson Rock’s stealer schema / data enrichment material: `stealer_family` is a string indicating which stealer type was used, and `ip` is the machine’s IP address. [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)

**Response cardinality and wrapper (unclear/inferred).**

- The changelog shows a single JSON object with no explicit `data` or pagination wrapper; however, other snippets (e.g., a “Stealer Search” doc) show a `data` array wrapper around stealer records. [docs.hudsonrock](https://docs.hudsonrock.com/docs/stealer-search)

- Treat the exact top-level shape (array vs `{ data: [...] }` plus pagination fields) as **unclear** and confirm in live reference docs and API responses.


**Response variants (inferred/unclear).**

- **Successful hit:** HTTP 200 with one or more stealer records matching the requested domains and filters.

- **Successful no-hit:** HTTP 200 with an empty array or `data: []` (exact behavior not documented; inferred from general API practices and other Hudson Rock integrations). [github](https://github.com/yasinyilmaz/rockNroll)

- **Partial / limited result:** Pagination is documented for OSINT v2 endpoints at 50 stealers per page, suggesting that v3 may also paginate; however, v3 pagination fields are not shown and should be treated as **unknown**. [turkhackteam](https://www.turkhackteam.org/konular/hudsonrock-cavalier-cybercrime-intelligence-solution.2064800/)

- **Common errors:** No explicit list is visible via the public docs scraper; assume standard 4xx/5xx JSON error payloads and confirm during implementation (status codes and error-body schema are **unknown**).


---

### A.2 Core Cavalier v3 – Search by Emails (End User Protection)

**Docs / role.** The API navigation shows an **End User Protection** section with “Email Search” under both the docs tree and reference area (Search by Emails). A specific reference entry “Search by Emails” notes that sorting can be done by `date_compromised` or `date_uploaded`, which are the same fields present on stealer records. [docs.hudsonrock](https://docs.hudsonrock.com/)

**Endpoint (partially documented).**

- Display name: “Search by Emails”. [docs.hudsonrock](https://docs.hudsonrock.com/reference/search-by-login-emails)

- Reference path: `/reference/search-by-login-emails` in docs navigation. [docs.hudsonrock](https://docs.hudsonrock.com/reference/search-by-login-emails)

- Actual REST path (e.g., `/json/v3/search-by-emails` vs `/json/v3/search-by-login-emails`) and method are not visible to the scraper and must be taken from authenticated docs; treat as **unknown** here.


**Purpose (derived).**

- Search stealer records where credentials or other selectors are associated with specific email addresses/logins, typically to protect employees or users by detecting if their accounts were present in infostealer logs. [infostealers](https://www.infostealers.com/article/email-leaked-credentials-search/)


**Supported entity types (derived).**

- Primary: `email` (end-user or employee email address). Hudson Rock’s free tools and marketing material emphasise email and username checks for infostealer compromise. [hudsonrock](https://www.hudsonrock.com/threat-intelligence-cybercrime-tools)


**Authentication (inferred).**

- Likely the same API-key header mechanism as other v3 endpoints (`api-key`), but not explicitly visible in the snippet; treat as **inferred** from v3 patterns and confirm against the reference page. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)


**Request body (partially documented / inferred).**

- The `Search by Emails` reference snippet states that `date_compromised` vs `date_uploaded` are valid sort keys. [docs.hudsonrock](https://docs.hudsonrock.com/reference/search-by-login-emails)

- By analogy with Password Search, v3 search endpoints typically accept arrays of selectors (e.g., `passwords`, `domains`) plus filters like `types`, `filter_credentials`, optional date ranges, and sort parameters. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

- For implementation, expect a JSON body containing one or more email addresses plus optional filters, but treat exact field names (e.g., `emails`, `logins`, `identifiers`) and constraints as **unknown** until verified in the authenticated docs.


**Response structure (derived).**

- Returns the same underlying stealer records described in A.1, filtered by matches against email/login fields. [infostealers](https://www.infostealers.com/article/email-leaked-credentials-search/)

- Fields such as `stealer_family`, `date_compromised`, `date_uploaded`, `ip`, `computer_name`, `operating_system`, `credentials`, and possibly `employeeAt`/`clientAt` are expected to appear, but the exact wrapper and any additional metadata (hit counts, pagination) are **unclear** from public snippets. [docs.hudsonrock](https://docs.hudsonrock.com/docs/stealer-search)


**Response variants (inferred).**

- **Hit:** 200 with at least one stealer record whose captured credentials include the queried email as a login or which otherwise maps to the user via Hudson Rock’s enrichment logic.

- **No-hit:** 200 with no stealer records; free email-check tools built on this API explicitly report whether an email has been compromised or not. [infostealers](https://www.infostealers.com/article/email-leaked-credentials-search/)

- Errors & pagination semantics remain **unknown** in public docs and must be confirmed interactively.


---

### A.3 Complimentary OSINT v2 – Search by Login (email / username)

**Docs / role.** Multiple open-source tools (e.g., Rock ‘N’ Roll, several OSINT projects) integrate Hudson Rock’s **Cavalier** v2 “Search by Login” endpoint to check whether an email address (or login string) appears in infostealer logs. These are described by Hudson Rock representatives as “complimentary data” intended for OSINT-style integrations. [github](https://github.com/InQuest/ThreatIngestor/issues/161)

**Endpoint (documented via examples).**

- Base: `https://cavalier.hudsonrock.com`.

- Path: `/api/json/v2/search-by-login`. [arxiv](https://arxiv.org/pdf/2111.07238.pdf)

- Method: `POST`. [turkhackteam](https://www.turkhackteam.org/konular/hudsonrock-cavalier-cybercrime-intelligence-solution.2064800/)

- Query parameters: examples show `sample=true` and `sortby=date_uploaded` as optional query-string parameters used by Rock ‘N’ Roll. [arxiv](https://arxiv.org/pdf/2111.07238.pdf)


**Purpose (documented/derived).**

- Given a single login (commonly an email address), return a list of stealer records where that login appears in captured credentials. [arxiv](https://arxiv.org/pdf/2111.07238.pdf)


**Supported entity types (derived).**

- `email` (primary in most examples). [github](https://github.com/graniet/operative-framework/issues/52)

- `username` or other identifiers may also be allowed as login strings, but not formally documented in public examples.


**Authentication (documented via examples / third-party).**

- Example headers from Rock ‘N’ Roll include `api-key: ROCKHUDSONROCK`, indicating a special complimentary key; other OSINT integrations suggest that some complimentary endpoints may work without an API key, but `search-by-login` is usually called with a key. [github](https://github.com/projectdiscovery/subfinder/issues/1260)

- For production Zima usage, treat authentication and key provisioning as a licensing concern to be clarified with Hudson Rock; the exact free/paid split is **not fully documented**.


**Request body (documented via examples).**

Rock ‘N’ Roll sends the following JSON body: [arxiv](https://arxiv.org/pdf/2111.07238.pdf)

```json
{
  "login": "user@example.com"
}
```

- `login` (string): email address or login identifier.


**Response structure (documented via third-party code/description).**

- Rock ‘N’ Roll and similar tools iterate over `response.json()` as a list, implying the endpoint returns a JSON array of stealer records. [arxiv](https://arxiv.org/pdf/2111.07238.pdf)

- For each `entry`, Rock ‘N’ Roll accesses fields:

    - `stealer_family`

    - `date_uploaded`

    - `date_compromised`

    - `computer_name`

    - `operating_system`

    - `antiviruses`

    - `credentials` (array; at least `url` and `domain` are used)

- These names align with the v3 stealer schema, suggesting v2 and v3 share the same core record fields.

- Employee-session cookies (`employee_session_cookies`) are also processed in Rock ‘N’ Roll, but this field is not mentioned in official snippets and should be treated as **optional / undocumented**. [arxiv](https://arxiv.org/pdf/2111.07238.pdf)


**Field presence (inferred).**

- In Rock ‘N’ Roll, every field is accessed via `.get(..., default)`, which implies all of them are optional from the client’s perspective (may be missing/null). [arxiv](https://arxiv.org/pdf/2111.07238.pdf)

- In practice, for Zima’s purposes, treat `date_compromised`, `stealer_family`, and at least one of `computer_name`, `operating_system`, `ip` (in v3), or `credentials` as expected for a “useful hit,” and defensively handle missing values.


**Response variants (inferred).**

- **Hit:** HTTP 200 with a non-empty JSON array of stealer records.

- **No-hit:** HTTP 200 with `[]` (Rock ‘N’ Roll explicitly checks for an empty result and prints “User not found.”). [arxiv](https://arxiv.org/pdf/2111.07238.pdf)

- **Errors:** Standard HTTP errors when the request or key is invalid; exact schema and codes are not documented publicly.


---

### A.4 Complimentary OSINT v2 – Search by Domain & URLs by Domain

**Docs / role.** Hudson Rock exposes complimentary OSINT endpoints under `/api/json/v2/osint-tools/` on `cavalier.hudsonrock.com`, including `search-by-domain` and `urls-by-domain`. These are positioned as lightweight tools for discovering compromised assets and URLs associated with a domain and are widely referenced in OSINT tooling and community posts. [github](https://github.com/Security-Onion-Solutions/securityonion/discussions/14079)

**Endpoints (documented via examples / third-party).**

- `https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-domain?domain=tesla.com`. [github](https://github.com/projectdiscovery/subfinder/issues/1260)

- `https://cavalier.hudsonrock.com/api/json/v2/osint-tools/urls-by-domain?domain=tesla.com`. [github](https://github.com/Security-Onion-Solutions/securityonion/discussions/14079)

- Method: `GET` in most examples.


**Purpose (derived).**

- `search-by-domain`: Return information about infostealer compromises associated with a given domain (likely summarised rather than full raw records). [github](https://github.com/InQuest/ThreatIngestor/issues/161)

- `urls-by-domain`: Return related URLs discovered for a domain, which OSINT tools use for subdomain/URL enumeration. [github](https://github.com/projectdiscovery/subfinder/issues/1260)


**Supported entity types (derived).**

- `domain` (for both endpoints). [github](https://github.com/InQuest/ThreatIngestor/issues/161)

- `urls-by-domain` effectively returns `url` entities as enrichment. [github](https://github.com/projectdiscovery/subfinder/issues/1260)


**Authentication & rate limits (documented via third-party).**

- Subfinder issue and other community notes state that `urls-by-domain` “doesn’t require any dedicated API key” and that the rate limit is **50 requests per 10 seconds**, with **50 stealers per page**. [turkhackteam](https://www.turkhackteam.org/konular/hudsonrock-cavalier-cybercrime-intelligence-solution.2064800/)

- It is unclear whether `search-by-domain` has identical auth/limits; many examples omit an API key, but this should be validated directly with Hudson Rock.


**Response structure (unknown/inferred).**

- The exact JSON schema of `osint-tools/search-by-domain` and `urls-by-domain` is not shown in official or community snippets accessible via the scraper.

- Community tooling treats them as simple JSON APIs returning structured data about compromises and URLs, but field names and invariants are **unknown**.


Given this uncertainty, these OSINT endpoints are best treated as **utility/enrichment** for Zima rather than primary signal sources, unless direct schema access is obtained.

---

### A.5 Cross-cutting stealer schema and Password Search

**Stealer schema.** Hudson Rock provides a formal “Stealer Schema” / “Data Enrichment” description that documents core stealer-record fields such as `stealer_family` (string; which stealer type) and `ip` (string; IP of the compromised machine), confirming the general structure seen in the v3 example and v2 integrations. [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)

**Password Search endpoint.** The **Search by Password** docs offer a detailed view into common query and filtering patterns used across advanced search endpoints: [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

- Endpoint: `/search-by-password` with required permission `search-by-password` (exact REST path prefix not visible, but aligned with v3).

- Request body fields:

    - `passwords` (array[string], required): up to 50 passwords. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

    - `sort_by` (string, default `"date_compromised"`): allowed values `"date_compromised"` or `"date_uploaded"`. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

    - `sort_direction` (string, default `"desc"`): `"asc"` or `"desc"`. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

    - `types` (array[string], optional): filters `"employees"` vs `"users"`. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

    - `domains` (array[string], optional): restrict to specific domains. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

    - `filter_credentials` (boolean, default `true`). [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

    - `start_date`, `end_date` (datetime, optional): time bounding. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)


These fields and enums (`sort_by`, `sort_direction`, `types`, `filter_credentials`, date filters) are strong indicators of the same patterns being used in domain/email searches, though this is extrapolation and should be validated in those specific references. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

This shared schema and parameter vocabulary significantly simplifies mapping to a single internal `stealer_log_exposure` abstraction in Zima.

---

## B. Module Mapping Appendix

### B.1 Target module

The provider map specifies a single target Zima module:

- `stealer_log_exposure`


This module is intended to surface signals when infostealer logs show evidence of credential compromise for Zima-tracked entities (initially emails and domains).

### B.2 Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|
|---|---|---|---|---|---|---|---|
|stealer_log_exposure|signal_producer|`search_by_domain` (v3 client wrapper)|Core Cavalier Domain Intelligence: `POST /json/v3/search-by-domain` on `api.hudsonrock.com`|direct_signal_input|domain|Only create signals when at least one stealer record is returned and `credentials` contains entries with `domain` matching the queried domain; always set `filter_credentials=true` and prefer `types=["employees"]` for corporate-focused monitoring.|[docs.hudsonrock](https://docs.hudsonrock.com/)|
|stealer_log_exposure|signal_producer|`search_by_email` (v3 client wrapper)|Core Cavalier End User Protection: Search by Emails (reference: Search by Emails docs)|direct_signal_input|email|Only create signals when the Search by Emails endpoint returns one or more stealer records for the queried email/login; treat the presence of a record with non-null `date_compromised` as a confirmed compromise event.|[docs.hudsonrock](https://docs.hudsonrock.com/)|
|stealer_log_exposure|signal_producer|`osint_search_by_login` (v2 fallback)|Complimentary Cavalier v2: `POST /api/json/v2/search-by-login` on `cavalier.hudsonrock.com`|direct_signal_input (optional/fallback)|email, username|Use only as a fallback or low-fidelity path when v3 is unavailable; create signals only on non-empty result arrays, and mark evidence provenance as OSINT/v2; rate-limit strongly at or below community limits (≈1 request per 10 seconds per Rock ‘N’ Roll).|[arxiv](https://arxiv.org/pdf/2111.07238.pdf)|
|stealer_log_exposure|enrichment|`osint_search_by_domain` (v2 enrichment)|Complimentary OSINT `GET /api/json/v2/osint-tools/search-by-domain?domain=…`|enrichment_only|domain|Use solely to enrich existing Hudson Rock domain hits or other breach signals with additional summary/context about domain-level exposure; do not emit standalone signals from this endpoint because its schema and guarantees are undocumented.|[github](https://github.com/projectdiscovery/subfinder/issues/1260)|
|stealer_log_exposure|enrichment|`osint_urls_by_domain` (v2 enrichment)|Complimentary OSINT `GET /api/json/v2/osint-tools/urls-by-domain?domain=…`|enrichment_only|domain, url|Use only to add potentially interesting URLs/subdomains to existing domain-exposure signals; never emit a signal based solely on URL enumeration from this endpoint.|[github](https://github.com/projectdiscovery/subfinder/issues/1260)|
|stealer_log_exposure|out_of_scope|`search_by_password`|Password Search advanced endpoint|out_of_scope (for this module)|password (secret)|Exposes powerful password-based search that could underpin a dedicated `password_reuse_exposure` module but does not map cleanly to the current email/domain-focused `stealer_log_exposure` module; explicitly exclude until a password-centric module exists.|[docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)|
|stealer_log_exposure|out_of_scope|`search_by_username_v3`, `search_by_ipcidr_v3`, `search_by_company`|Other End User Protection and Domain Intelligence selectors|out_of_scope (for now)|username, ip, company|These are highly relevant for future modules (identity, network, third-party risk) but exceed the current provider map constraint of `email` and `domain` only; do not integrate yet for `stealer_log_exposure`.|[docs.hudsonrock](https://docs.hudsonrock.com/)|

---

## C. Signal Contract Table

Only two stable, provider-agnostic signal types are recommended: a generic `stealer_log_compromise` signal emitted for both email and domain entities, differentiated by `entity_type`, and with an optional lower-fidelity variant when sourced from v2 OSINT endpoints.

### C.1 Signal contracts

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|stealer_log_exposure|stealer_log_exposure|hudson_rock|`search_by_domain` (v3)|`stealer_log_compromise`|identity_security|high|yes|Escalate to `critical` when `date_compromised` is recent (e.g., ≤90 days) and at least one credential entry for the domain includes a non-empty `password` or clearly sensitive SSO/privileged URL; otherwise keep at `high`.|domain|true_finding|HTTP 200 from v3 Search by Domain; response contains at least one stealer record where `date_compromised` is non-null and `credentials` includes at least one object with `domain` equal (case-insensitive) to the queried domain and, if `types` is used, type indicates employees/users relevant to the organisation.|`_id`, `stealer`, `stealer_family`, `date_compromised`, `date_uploaded`, `ip`, `computer_name`, `operating_system`, `malware_path`, full `credentials` array (or at least entries matching the domain), and any `employeeAt` / `clientAt` objects associated with the hit.|`dir_tree` (if requested via `additional_fields`), `antiviruses`, non-domain credentials on the same machine, and any keyword filters used (`keywords`, `keywords_match`, `types`, `filter_credentials`) for later correlation and tuning but not as separate signals.|"Infostealer logs show compromised credentials for domain {{entity}} (stealer family {{stealer_family}}, first seen {{date_compromised}})."|documented / derived|[docs.hudsonrock](https://docs.hudsonrock.com/changelog/new-directory-tree-field)|Severity: direct credential theft on employee machines qualifies as at least high risk; recency and SSO/privileged URLs justify conditional critical. Shape of the top-level response (array vs wrapper) is unclear and must be handled defensively.|
|stealer_log_exposure|stealer_log_exposure|hudson_rock|`search_by_email` (v3)|`stealer_log_compromise`|identity_security|high|yes|Escalate to `critical` when `date_compromised` is recent and the stealer record clearly ties corporate or high-value access (e.g., employee domain, AD/SSO URLs in `credentials`) to the queried email; otherwise default to high.|email|true_finding|Search by Emails returns one or more stealer records for the queried email/login (exact request field name unknown); treat any record with non-null `date_compromised` as confirmation that credentials tied to that email were present in infostealer logs.|`_id`, `stealer_family`, `date_compromised`, `date_uploaded`, `ip` (if present), `computer_name`, `operating_system`, any `credentials` entries where the username/login or email mapping is known to relate to the queried address, and any employment metadata indicating employee vs external user.|Any available `antiviruses`, additional machine metadata, and optional `dir_tree`/other advanced fields if supported for email searches; sort and filter parameters (`sort_by`, `sort_direction`, `types`, `filter_credentials`, date range) for audit and tuning but not standalone findings.|"Infostealer logs show that credentials associated with {{entity}} were stolen (stealer family {{stealer_family}}, first seen {{date_compromised}})."|derived / inferred|[docs.hudsonrock](https://docs.hudsonrock.com/)|Endpoint path and request schema are partially opaque in public docs; integration must confirm actual field names. Severity logic mirrors domain case, but at user-level.|
|stealer_log_exposure|stealer_log_exposure|hudson_rock|`osint_search_by_login` (v2)|`stealer_log_compromise`|identity_security|medium|yes|Escalate to `high` only when corroborated by v3 results or independent breach evidence; otherwise keep OSINT-only hits at medium due to reduced control over filters and less clearly documented schema and SLAs.|email|true_finding|Complimentary v2 Search by Login returns a non-empty JSON array; for at least one entry, `date_compromised` is non-null and basic metadata fields (`stealer_family`, `computer_name` or `operating_system`) are present, indicating a resolved stealer record for the queried login.|`stealer_family`, `date_compromised`, `date_uploaded`, `computer_name`, `operating_system`, and `antiviruses` from each entry used to form the signal, plus the raw login string submitted; include any domain/URL from the first `credentials` entry as part of evidence.|Additional credentials beyond the first, any available IP or extended metadata if present in v2 responses, and any OSINT-provided message or summary fields; these enrich understanding but should not generate separate signals.|"Complimentary Hudson Rock OSINT data indicates infostealer compromise for {{entity}} (family {{stealer_family}}, first seen {{date_compromised}})."|derived / inferred|[arxiv](https://arxiv.org/pdf/2111.07238.pdf)|V2 OSINT endpoints use complimentary keys and community-documented limits; they are powerful but less governed than v3. Treat as lower-fidelity and prefer v3 where licensing allows.|

---

## D. Severity Rules

### D.1 Domain-based stealer_log_compromise (v3 Search by Domain)

- **Base severity:** `high`.

    - Justification: A returned stealer record with `credentials` for a monitored domain implies confirmed credential theft from an infected machine, matching the “confirmed breach, exposed credentials” band in Zima’s calibration guide. [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)

- **Conditional escalation to critical:**

    - If `date_compromised` is within a configurable “recent” window (e.g., 90 days, subject to tuning) **and** any of the following holds:

        - `credentials.url` indicates SSO, VPN, RDP, or other privileged access (e.g., contains `sso.`, `vpn.`, `rdp`, `citrix`, or equivalent high-value endpoints). [infostealers](https://www.infostealers.com/article/prominent-threat-actor-accidentally-infects-own-computer-with-info-stealer/)

        - `type` is explicitly `"employee"` and the associated asset is critical (per Zima’s asset inventory / mapping).

        - Optional: `dir_tree` reveals highly sensitive artifacts (“All Passwords.txt”, tokens files for remote-access tools, etc.), indicating broader credential exfiltration beyond a single site. [infostealers](https://www.infostealers.com/article/botnets-and-infostealers-2/)

    - This aligns with “active stealer logs / credential theft” being critical when clearly exploitable for high-privilege access, while older or less-privileged records remain high.


### D.2 Email-based stealer_log_compromise (v3 Search by Emails)

- **Base severity:** `high`.

    - Justification: Search by Emails is designed to signal that a given account’s credentials appear in stealer logs; Hudson Rock’s own guidance treats such findings as serious incidents for affected organisations and users. [hudsonrock](https://www.hudsonrock.com/blog/6190)

- **Conditional escalation to critical:**

    - If `date_compromised` is recent and the credentials clearly map to corporate or otherwise high-value services (e.g., AD, intranet, admin panels, cloud SSO) for the monitored organisation’s domain.

    - If multiple recent stealer records exist for the same email, implying repeated or persistent compromise.

- **Downgrade conditions (optional):**

    - For very old `date_compromised` values and where strong remediation evidence exists in Zima (e.g., password resets after the compromise date), teams may consider downgrading to medium; however, this should be handled in correlation or response layers rather than the mapper.


### D.3 OSINT v2-based stealer_log_compromise (Search by Login)

- **Base severity:** `medium`.

    - Justification: Still a true indication of compromise, but the OSINT path has less documented freshness guarantees, less granular filtering, and a free/complementary positioning, fitting Zima’s “suspicious activity / passive threat indicators” band. [github](https://github.com/yasinyilmaz/rockNroll)

- **Conditional escalation to high:**

    - When a v2 hit is corroborated by a v3 hit for the same selector and similar `date_compromised` range, or by other independent breach data.

    - When the organisation designates the account as highly sensitive (e.g., admin accounts) and has no alternative telemetry.


### D.4 First-pass provider-specific severity assessment

- The initial project note had no specific Hudson Rock severity override. Based on the documented fields and dataset nature (infostealer-derived, credential-centric), treating v3 hits as **high with conditional critical**, and v2 hits as **medium with conditional high**, is consistent with Zima’s calibration guide and Hudson Rock’s positioning as early-warning for credential theft. [hudsonrock](https://www.hudsonrock.com/)


---

## E. Confidence Guidance

### E.1 Source reliability

- Hudson Rock specialises in infostealer intelligence, sourcing compromised credentials directly from threat actors’ logs, and states that data is integrated into its cybercrime database within days of compromise once logs are sold. [infostealers](https://www.infostealers.com/article/prominent-threat-actor-accidentally-infects-own-computer-with-info-stealer/)

- Articles and OSINT community discussions note that data originates from credentials stored on infected devices; false positives can occur mainly for very generic usernames or secondary associations (e.g., someone else storing a victim’s email), but overall specificity is high when selectors are precise (full corporate emails, exact domains). [reddit](https://www.reddit.com/r/OSINT/comments/1igrg18/integration_of_hudson_rocks_api_foss/)


### E.2 Freshness / staleness

- Hudson Rock indicates that typically **2–3 days** elapse between infection and data being indexed, due to the time threat actors take to sell logs; after ingestion, stealer records retain `date_compromised` and `date_uploaded` timestamps. [infostealers](https://www.infostealers.com/article/botnets-and-infostealers-2/)

- For Zima, `date_compromised` should be interpreted as the primary measure of compromise recency, while `date_uploaded` is a lower bound for when defenders could have known of the issue.


### E.3 Corroboration opportunities

- Cross-check Hudson Rock hits against:

    - Internal identity logs (suspicious logins, password resets) around `date_compromised`.

    - Other breach intelligence (e.g., Have I Been Pwned stealer sources, dark web monitoring) for the same accounts. [haveibeenpwned.uservoice](https://haveibeenpwned.uservoice.com/forums/275398-general/suggestions/49608539-pay-as-you-go-for-stealer-lists-queries)

    - Endpoint telemetry indicating infostealer infection on the same machines.

- For OSINT v2 hits, prefer to also query v3 (where licensed) to confirm and enrich the record.


### E.4 Calibration TODOs

- Empirically tune the “recent” threshold for critical vs high severities based on observed exploit rate and organisational appetite; 90 days is a starting heuristic but not a fixed rule.

- Measure false-positive and duplicate rates when using v2 OSINT endpoints vs v3 to refine when OSINT-based results should be surfaced at all.

- Decide, per tenant, whether consumer/retail user credentials (not just employees) should trigger the same severities, especially for B2C use cases.


---

## F. Confidence Guidance Table

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|stealer_log_exposure|v3 `search_by_domain` → `stealer_log_compromise`|High: data comes from infostealer logs acquired directly from threat actors and parsed into a structured cybercrime database; schema is well-defined. [infostealers](https://www.infostealers.com/article/prominent-threat-actor-accidentally-infects-own-computer-with-info-stealer/)|Use `date_compromised` as primary signal of risk recency; `date_uploaded` shows when defenders could first have known; typical ingestion delay is 2–3 days post-infection. [infostealers](https://www.infostealers.com/article/botnets-and-infostealers-2/)|Corroborate with internal auth logs, password reset events and other threat intel sources (e.g., stealer sources in Have I Been Pwned) around the same compromise window. [haveibeenpwned.uservoice](https://haveibeenpwned.uservoice.com/forums/275398-general/suggestions/49608539-pay-as-you-go-for-stealer-lists-queries)|Empirically tune the recency threshold for critical vs high; validate how often domain-based stealer hits correlate with actual incidents within each tenant.|
|stealer_log_exposure|v3 `search_by_email` → `stealer_log_compromise`|High: same underlying dataset and schema as domain search, but selector is a specific email/login, which reduces ambiguity for corporate addresses. [infostealers](https://www.infostealers.com/article/email-leaked-credentials-search/)|Treat recent `date_compromised` as strong evidence of active account risk; consider age and known remediation (password resets) before auto-escalating older events.|Cross-check with identity telemetry (MFA challenges, impossible travel, account lockouts) and confirm that the email is indeed controlled by the monitored organisation.|Measure how many email-based stealer hits represent already-remediated events vs live exposures to calibrate downgrade rules or suppression for fully-remediated, very old entries.|
|stealer_log_exposure|v2 `search-by-login` OSINT → `stealer_log_compromise`|Medium: same core dataset but accessed via complimentary OSINT tooling with less documentation on SLAs, filters and error guarantees. [arxiv](https://arxiv.org/pdf/2111.07238.pdf)|No explicit freshness SLA; rely on `date_compromised` and treat OSINT-only hits as lower priority unless very recent or for highly privileged accounts.|Whenever possible, re-query v3 for the same selector and compare; also correlate with other OSINT/breach sources before escalating to high severity.|Track empirical false-positive and duplication rates for OSINT-only hits; decide thresholds where Zima should suppress or only use them as enrichment rather than standalone signals.|

---

## G. Provider Summary and Implementation Notes

### G.1 Strongest signal types

- **Stealer log–derived credential compromise for specific domains and emails** is the core value of Hudson Rock for Zima: v3 Search by Domain and Search by Emails provide confirmed evidence that credentials were harvested from infected machines, with rich metadata (`stealer_family`, `date_compromised`, machine details, credentials, optional directory trees). [hudsonrock](https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20\(1\)-97e834f4.pdf)

- These map cleanly onto a single internal `stealer_log_compromise` signal type across entity types (`domain`, `email`).


### G.2 What Hudson Rock should not be used for (in this stage)

- Not a generic IP/URL reputation feed or DDoS/malware C2 tracker – focus is on **infostealer compromise and stolen credentials**, not broad threat infrastructure classification. [hudsonrock](https://www.hudsonrock.com/press)

- Not a generic dark web or data-broker breach monitor; it specifically covers infostealer logs aggregated from cybercrime markets. [infostealers](https://www.infostealers.com/article/prominent-threat-actor-accidentally-infects-own-computer-with-info-stealer/)

- Password-centric analytics (weak-password discovery, reuse) via Search by Password are powerful but belong in a separate Zima module, not in `stealer_log_exposure`. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)


### G.3 API/auth/rate-limit/licensing cautions

- v3 endpoints use API-key authentication and are part of Hudson Rock’s commercial Cavalier offering; permissions for advanced endpoints (e.g., Password Search) are explicitly gated. [docs.hudsonrock](https://docs.hudsonrock.com/docs/password-search)

- Complimentary v2 OSINT endpoints (including `search-by-login` and `/osint-tools/search-by-domain`/`urls-by-domain`) have community-documented limits of about **50 requests per 10 seconds** and 50 stealers per page; they may not require a dedicated API key for some endpoints, but licensing and acceptable-use should be confirmed directly with Hudson Rock before relying on them in a commercial product. [github](https://github.com/graniet/operative-framework/issues/52)

- Documentation for some references (Search by Emails, Domains Overview) is partially hidden behind the interactive docs or authentication; implementers should validate path names, wrappers, error schemas, and any pagination / quota headers in a staging environment. [docs.hudsonrock](https://docs.hudsonrock.com/reference/domains-overview)


### G.4 Provider role classification for Zima

- In the current Zima stage and for the `stealer_log_exposure` module, Hudson Rock should be treated as a **signal-producing provider**, with:

    - **Direct signal inputs** from v3 Search by Domain and Search by Emails, plus an optional lower-fidelity variant from v2 Search by Login.

    - **Enrichment-only** usage of OSINT `search-by-domain` and `urls-by-domain` endpoints to add context and discovery value but not to create independent signals.

    - **Deferred / out-of-scope** usage of password-based and non-email/domain selector endpoints until additional modules (password hygiene, IP/network exposure, third-party risk) are defined.


These choices keep the Zima integration focused, robust against undocumented behavior in OSINT endpoints, and aligned with Zima’s signal-severity calibration around confirmed credential theft.

---

## H. Structured JSON

```json
{
  "provider": "hudson_rock",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "search_by_domain",
      "endpoint_or_artifact": "POST https://api.hudsonrock.com/json/v3/search-by-domain",
      "classification": "direct_signal_input",
      "entity_types": ["domain"],
      "gating_logic": "Only create signals when at least one stealer record is returned and credentials contains entries with domain matching the queried domain; always set filter_credentials=true and prefer types=[\"employees\"] for corporate-focused monitoring.",
      "citation_refs": ["https://docs.hudsonrock.com", "https://docs.hudsonrock.com/changelog/new-directory-tree-field", "https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20(1)-97e834f4.pdf"]
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "search_by_email",
      "endpoint_or_artifact": "Search by Emails (v3 End User Protection)",
      "classification": "direct_signal_input",
      "entity_types": ["email"],
      "gating_logic": "Only create signals when the Search by Emails endpoint returns one or more stealer records for the queried email/login; treat the presence of a record with non-null date_compromised as a confirmed compromise event.",
      "citation_refs": ["https://docs.hudsonrock.com", "https://www.infostealers.com/article/email-leaked-credentials-search/", "https://docs.hudsonrock.com/reference/search-by-login-emails"]
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "osint_search_by_login",
      "endpoint_or_artifact": "POST https://cavalier.hudsonrock.com/api/json/v2/search-by-login",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username"],
      "gating_logic": "Use only as a fallback or low-fidelity path when v3 is unavailable; create signals only on non-empty result arrays, and mark evidence provenance as OSINT/v2; rate-limit strongly in line with community guidance.",
      "citation_refs": ["https://github.com/yasinyilmaz/rockNroll", "https://github.com/projectdiscovery/subfinder/issues/1260", "https://github.com/graniet/operative-framework/issues/52"]
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "osint_search_by_domain",
      "endpoint_or_artifact": "GET https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-domain?domain=...",
      "classification": "enrichment_only",
      "entity_types": ["domain"],
      "gating_logic": "Use solely to enrich existing Hudson Rock domain hits or other breach signals with additional summary/context about domain-level exposure; do not emit standalone signals.",
      "citation_refs": ["https://github.com/projectdiscovery/subfinder/issues/1260", "https://www.reddit.com/r/OSINT/comments/1igrg18/integration_of_hudson_rocks_api_foss/", "https://github.com/Security-Onion-Solutions/securityonion/discussions/14079"]
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "osint_urls_by_domain",
      "endpoint_or_artifact": "GET https://cavalier.hudsonrock.com/api/json/v2/osint-tools/urls-by-domain?domain=...",
      "classification": "enrichment_only",
      "entity_types": ["domain", "url"],
      "gating_logic": "Use only to add potentially interesting URLs/subdomains to existing domain-exposure signals; never emit a signal based solely on URL enumeration.",
      "citation_refs": ["https://github.com/projectdiscovery/subfinder/issues/1260", "https://github.com/Security-Onion-Solutions/securityonion/discussions/14079"]
    },
    {
      "module": "stealer_log_exposure",
      "provider_role": "signal_producer",
      "provider_method": "search_by_password",
      "endpoint_or_artifact": "Search by Password (v3 advanced)",
      "classification": "out_of_scope",
      "entity_types": ["password"],
      "gating_logic": "Exclude from stealer_log_exposure; candidate for a future password_reuse_exposure or password_hygiene module.",
      "citation_refs": ["https://docs.hudsonrock.com/docs/password-search"]
    }
  ],
  "signal_contracts": [
    {
      "module": "stealer_log_exposure",
      "source": "stealer_log_exposure",
      "provider": "hudson_rock",
      "provider_method": "search_by_domain",
      "signal_type": "stealer_log_compromise",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Escalate to critical when date_compromised is within a recent window (for example <= 90 days) and at least one credential entry for the domain has a non-empty password or clearly sensitive SSO/privileged URL; otherwise remain high.",
      "entity_type": "domain",
      "finding_kind": "true_finding",
      "trigger_condition": "HTTP 200 from v3 Search by Domain; response contains at least one stealer record where date_compromised is non-null and credentials includes at least one object with domain equal (case-insensitive) to the queried domain.",
      "evidence_fields": [
        "_id",
        "stealer",
        "stealer_family",
        "date_compromised",
        "date_uploaded",
        "ip",
        "computer_name",
        "operating_system",
        "malware_path",
        "credentials",
        "employeeAt",
        "clientAt"
      ],
      "enrichment_fields": [
        "dir_tree",
        "antiviruses",
        "keywords",
        "keywords_match",
        "types",
        "filter_credentials"
      ],
      "summary_template": "Infostealer logs show compromised credentials for domain {{entity}} (stealer family {{stealer_family}}, first seen {{date_compromised}}).",
      "evidence_status": "documented / derived",
      "citation_refs": [
        "https://docs.hudsonrock.com/changelog/new-directory-tree-field",
        "https://docs.hudsonrock.com/reference/domains-overview",
        "https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20(1)-97e834f4.pdf"
      ],
      "tags": ["breach", "stealer_log", "credential_stuffing"]
    },
    {
      "module": "stealer_log_exposure",
      "source": "stealer_log_exposure",
      "provider": "hudson_rock",
      "provider_method": "search_by_email",
      "signal_type": "stealer_log_compromise",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Escalate to critical when date_compromised is recent and the stealer record clearly ties corporate or high-value access (for example AD/SSO URLs, corporate domain) to the queried email; otherwise remain high.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "Search by Emails returns one or more stealer records for the queried email/login; any record with non-null date_compromised is treated as confirmation that credentials tied to that email were present in infostealer logs.",
      "evidence_fields": [
        "_id",
        "stealer_family",
        "date_compromised",
        "date_uploaded",
        "ip",
        "computer_name",
        "operating_system",
        "credentials",
        "employeeAt",
        "clientAt"
      ],
      "enrichment_fields": [
        "antiviruses",
        "dir_tree",
        "sort_by",
        "sort_direction",
        "types",
        "filter_credentials",
        "start_date",
        "end_date"
      ],
      "summary_template": "Infostealer logs show that credentials associated with {{entity}} were stolen (stealer family {{stealer_family}}, first seen {{date_compromised}}).",
      "evidence_status": "derived / inferred",
      "citation_refs": [
        "https://docs.hudsonrock.com",
        "https://www.infostealers.com/article/email-leaked-credentials-search/",
        "https://docs.hudsonrock.com/reference/search-by-login-emails",
        "https://www.hudsonrock.com/assets/Hudson%20Rock%20-%20Data%20Enrichment%20(1)-97e834f4.pdf"
      ],
      "tags": ["breach", "stealer_log", "credential_stuffing"]
    },
    {
      "module": "stealer_log_exposure",
      "source": "stealer_log_exposure",
      "provider": "hudson_rock",
      "provider_method": "osint_search_by_login",
      "signal_type": "stealer_log_compromise",
      "category": "identity_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Escalate to high when corroborated by v3 results or independent breach evidence; otherwise keep OSINT-only hits at medium.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "V2 Search by Login returns a non-empty JSON array; for at least one entry, date_compromised is non-null and basic metadata (stealer_family, computer_name or operating_system) is present.",
      "evidence_fields": [
        "stealer_family",
        "date_compromised",
        "date_uploaded",
        "computer_name",
        "operating_system",
        "antiviruses",
        "credentials",
        "login"
      ],
      "enrichment_fields": [
        "ip",
        "employee_session_cookies"
      ],
      "summary_template": "Complimentary Hudson Rock OSINT data indicates infostealer compromise for {{entity}} (family {{stealer_family}}, first seen {{date_compromised}}).",
      "evidence_status": "derived / inferred",
      "citation_refs": [
        "https://github.com/yasinyilmaz/rockNroll",
        "https://www.reddit.com/r/OSINT/comments/1igrg18/integration_of_hudson_rocks_api_foss/",
        "https://github.com/Security-Onion-Solutions/securityonion/discussions/14079"
      ],
      "tags": ["breach", "stealer_log", "credential_stuffing"]
    }
  ],
  "confidence_guidance": [
    {
      "module": "stealer_log_exposure",
      "signal_type_or_use_case": "v3 search_by_domain → stealer_log_compromise",
      "source_reliability": "High: data comes from infostealer logs acquired directly from threat actors and parsed into a structured cybercrime database; schema is well-defined.",
      "freshness_considerations": "Use date_compromised as primary indicator; date_uploaded indicates when the data became available to defenders; typical ingestion delay is a few days after infection.",
      "corroboration_rules": "Correlate with identity/auth logs, password reset activity, and other breach intelligence such as Have I Been Pwned stealer sources.",
      "calibration_todo": "Tune recency threshold for critical vs high severities per tenant and measure correlation with real incidents."
    },
    {
      "module": "stealer_log_exposure",
      "signal_type_or_use_case": "v3 search_by_email → stealer_log_compromise",
      "source_reliability": "High: same dataset as domain search but with specific email selectors, which improves specificity for corporate addresses.",
      "freshness_considerations": "Treat recent date_compromised as strong evidence of active account risk; consider remediation status before downgrading older events.",
      "corroboration_rules": "Cross-check with MFA, impossible-travel signals, and account-lockout events for the same email in identity systems.",
      "calibration_todo": "Measure what proportion of email hits are already remediated vs live to inform downgrade/suppression rules for very old, fully remediated exposures."
    },
    {
      "module": "stealer_log_exposure",
      "signal_type_or_use_case": "v2 search-by-login OSINT → stealer_log_compromise",
      "source_reliability": "Medium: same underlying logs but accessed via complimentary OSINT APIs with less formal documentation on SLAs and filters.",
      "freshness_considerations": "No explicit freshness guarantee; rely on date_compromised, treat OSINT-only hits as lower priority unless very recent or involving privileged accounts.",
      "corroboration_rules": "Where possible, re-check with v3 and/or other OSINT/breach sources before escalating to high severity.",
      "calibration_todo": "Track false-positive and duplication rate of OSINT-only hits to decide when to surface as standalone signals vs enrichment."
    }
  ]
}
```
