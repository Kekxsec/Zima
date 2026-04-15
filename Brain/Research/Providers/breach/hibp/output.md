---
title: "output / breach / hibp"
aliases: ["hibp output", "hibp signal registry"]
tags: [zima, research, outputs, signal-registry, breach, hibp]
type: provider_research_output
provider: hibp
provider_category: breach
status: complete
prompt_note: prompt.md
provider_folder: hibp.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---
# Have I Been Pwned (HIBP) integration for `breach_monitor`

HIBP should be treated as a core signal-producing provider for `breach_monitor`, with three primary signal concepts: account-in-breach, stealer-log credential exposure, and paste-based exposure, plus several enrichment/utility endpoints for metadata, subscription state, and domain management. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

## A. API Surface Appendix

### 1. Breach search for an account — `/breachedaccount/{account}`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/breachedaccount/{account}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Return all breaches an account (email / username / phone) has appeared in; primary per-account breach signal input. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Supported `entity_type`(s)**
  - `email`, `username`, `phone` (HIBP docs say “accounts (email addresses, usernames and phone numbers)” — Zima should normalize primarily as `email` for this module, with possible extension to other identifiers later). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Auth / execution requirements**
  - Requires HIBP subscription key via `hibp-api-key` header (32-char hex); invalid or missing key returns 401. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Requires `user-agent` header; missing user agent returns 403. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - HTTPS only; TLS 1.2+. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Key query parameters (documented)** [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - `truncateResponse` (e.g. `?truncateResponse=false`):
    - `true` (default): returns only `{ "Name": "<breach>" }` per breach.
    - `false`: returns full breach model for each breach.
  - `domain` (e.g. `?domain=adobe.com`): filter breaches to those against a given domain.
  - `IncludeUnverified` (e.g. `?IncludeUnverified=false`): exclude unverified breaches; by default both verified and unverified are returned.
- **Top-level response shapes (documented)**
  - **Hit, truncated (default)** — array of objects with only `Name` (string): [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    ```json
    [
      { "Name": "Adobe" },
      { "Name": "Gawker" },
      { "Name": "Stratfor" }
    ]
    ```
  - **Hit, full breach models (`truncateResponse=false`)** — array of breach objects (see breach model below). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **No-hit / error variants (documented)**
  - 200: account found in ≥1 breach. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 404: account not found in any breach (or opted out) — generic “Not found — the account could not be found and has therefore not been pwned” response code definition; applied across search endpoints. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 400: bad request, e.g. empty account. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 401: invalid or missing API key. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 403: missing/blocked user-agent, or forbidden resource (e.g. sensitive breach). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 429: rate limit exceeded, with `retry-after` header and JSON error body. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Test API behaviour (documented)**
  - Test key: any 32-char hex, e.g. `0000...0000`. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Test accounts such as `account-exists@hibp-integration-tests.com`, `spam-list-only@...`, `stealer-log@...` return deterministic synthetic results without a paid subscription. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Breach model fields (documented)**
  - When `truncateResponse=false` or via `/breaches`/`/breach/{name}`, each breach object has: [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `Name` (string, PascalCase, stable ID)
    - `Title` (string, user-facing name, mutable)
    - `Domain` (string)
    - `BreachDate` (date string `YYYY-MM-DD`)
    - `AddedDate` (datetime, ISO 8601, minute precision)
    - `ModifiedDate` (datetime, >= AddedDate)
    - `PwnCount` (integer)
    - `Description` (HTML string)
    - `DataClasses` (string[]) — data categories like `"Email addresses"`, `"Passwords"`, `"Password hints"` etc. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `IsVerified` (bool)
    - `IsFabricated` (bool)
    - `IsSensitive` (bool) — public APIs do not return accounts from sensitive breaches. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `IsRetired` (bool) — data removed and not returned. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `IsSpamList` (bool) — spam/marketing list; not necessarily a security compromise. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `IsMalware` (bool) — sourced from malware campaigns. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `IsSubscriptionFree` (bool) — subscription-free breach for domain search. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `IsStealerLog` (bool) — sourced from stealer logs; domains also mapped and accessible via stealer log APIs. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `LogoPath` (string)
    - `Attribution` (string or null) [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Field presence (documented / inferred)**
  - All listed attributes are part of the breach model and present in examples; some may be null: `Attribution` is shown as null; presence but null allowed (documented via sample). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Semantics of null vs omission for breach fields are not explicitly documented; treat as **unclear**; handle missing keys defensively (inferred).
- **Citation refs**
  - HIBP API v3 “Breaches → Getting all breaches for an account” and “The breach model”, “Response codes”, “Test accounts”. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

### 2. Domain-level breach search — `/breacheddomain/{domain}`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/breacheddomain/{domain}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Return all breached email aliases on a verified domain and, for each alias, the names of breaches it appeared in. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Supported `entity_type`(s)**
  - Primary: `domain` (input); effective entities: `email` (aliases + domain). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Auth / execution requirements**
  - Requires verified control of the domain via HIBP domain search dashboard; unverified domains return 403. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Requires `hibp-api-key` and `user-agent` headers. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response shapes (documented)**
  - **Hit (200)** — object mapping alias to array of breach names: [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    ```json
    {
      "alias1": ["Adobe"],
      "alias2": ["Adobe", "Gawker", "Stratfor"],
      "alias3": ["AshleyMadison"]
    }
    ```
  - **No hit (404)** — domain has no breached email addresses. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - **403** — domain not yet verified. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Notes**
  - Returns sensitive breaches as well because domain ownership is verified (documented). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - No formal rate limit documented, but “regularly querying beyond what is practically necessary may result in 429” (documented, behaviour is policy-based). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Citation refs**
  - HIBP API v3 “Getting all breached email addresses for a domain”. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

### 3. Subscribed domains — `/subscribeddomains`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/subscribeddomains` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - List domains associated with the API key, with current and historical breach counts; used for domain-search management and subscription scoping. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Supported `entity_type`(s)**
  - `domain` (enrichment / inventory).
- **Auth / execution requirements**
  - Requires `hibp-api-key` and `user-agent`. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response schema (documented)**
  - Each entry: [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `DomainName` (string) — verified domain.
    - `PwnCount` (integer or null) — total breached email addresses on domain at last search.
    - `PwnCountExcludingSpamLists` (integer or null) — same but excluding spam-list breaches.
    - `PwnCountExcludingSpamListsAtLastSubscriptionRenewal` (integer or null) — locked reference count at current subscription start. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `NextSubscriptionRenewal` (datetime or null) — subscription end date. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Presence**
  - Null allowed for counts and renewal dates when no searches/subscriptions yet (documented). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Citation refs**
  - HIBP API v3 “Getting all subscribed domains”. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

### 4. Breach catalogue and metadata

These endpoints provide full breach metadata and data-class taxonomy; they are primarily enrichment/utility for Zima.

#### 4.1 `/breaches`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/breaches` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Return full list of all breaches (currently ~962) with full breach models. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Parameters (documented)** [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - `Domain=?Domain=adobe.com` — filter to breaches against given website domain.
  - `IsSpamList=?IsSpamList=true` — filter to only spam-list or only non-spam breaches.
- **Response**
  - 200: array of breach models; sorted alphabetically by `Title`. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

#### 4.2 `/breach/{name}`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/breach/{name}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Get a single breach by its stable `Name`. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response**
  - 200: single breach model.
  - 404: breach name not found (derived from generic response-codes section; endpoint-specific 404 not explicitly enumerated — **derived from documented behaviour**). [haveibeenpwned](https://haveibeenpwned.com/api/v3)

#### 4.3 `/latestbreach`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/latestbreach` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Get most recently **added** breach (by `AddedDate`, not necessarily most recent incident date). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response**
  - 200: single breach model. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

#### 4.4 `/dataclasses`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/dataclasses` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Return alphabetically ordered array of data-class strings (e.g. “Email addresses”, “Passwords”). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response**
  - 200: `string[]`.

---

### 5. Stealer Logs APIs

All stealer log endpoints require a subscription including stealer logs (“Pwned 5 or higher”), verified domains for domain-based queries, and have their own rate limits separate from breach search RPM. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)

#### Background semantics

- Stealer logs are created by malware on infected machines, capturing website URL, email address, and password as credentials are entered. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- HIBP processes these into pairs of email address and website domain (e.g. `jane@gmail.com` + `netflix.com`) and loads them as a special “stealer log” breach with `IsStealerLog=true` plus separate stealer-log domain APIs. [haveibeenpwned](https://haveibeenpwned.com/breach/StealerLogsJan2025)
- The `StealerLogsJan2025` breach explicitly consists of “email address, password and the website the credentials were entered against”, and added 106M passwords to Pwned Passwords. [haveibeenpwned](https://haveibeenpwned.com/breach/StealerLogsJan2025)

#### 5.1 `/stealerlogsbyemail/{email address}`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/stealerlogsbyemail/{email address}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - For a single email address, return the list of website domains whose credentials appeared in stealer logs. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Supported `entity_type`(s)**
  - Input entity: `email`; output entity dimension: `domain` (website domains).
- **Auth / gating (documented)**
  - Requires `hibp-api-key` on subscription with `IncludesStealerLogs=true`. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Email’s domain **must** be one of the domains added to the domain search dashboard (ownership verified) or 403. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Response shapes (documented)**
  - 200: JSON array of domains (strings), sorted alphabetically: [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    ```json
    [
      "netflix.com",
      "spotify.com"
    ]
    ```
  - 404: no stealer-log entries for this email address. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 403: email’s domain not verified. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

#### 5.2 `/stealerlogsbywebsitedomain/{domain}`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/stealerlogsbywebsitedomain/{domain}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - For a website domain (e.g. `netflix.com`), return email addresses whose credentials were captured while logging into that site. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Supported `entity_type`(s)**
  - Input entity: `domain` (website domain).
  - Output dimension: `email` addresses.
- **Auth / gating**
  - Domain must be in the domain search dashboard; otherwise 403. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Requires stealer-logs-capable subscription and `hibp-api-key`. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Response shapes**
  - 200: JSON array of email addresses (strings), sorted alphabetically: [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    ```json
    [
      "andy@gmail.com",
      "jane@gmail.com"
    ]
    ```
  - 403: unverified domain. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

#### 5.3 `/stealerlogsbyemaildomain/{domain}`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/stealerlogsbyemaildomain/{domain}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - For an **email domain** (e.g. `gmail.com` or a corporate domain), return aliases and website domains that those aliases have appeared against in stealer logs. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Supported `entity_type`(s)**
  - Input: `domain` (email domain).
  - Effective output: mapping of `email` aliases to website domains.
- **Auth / gating**
  - Email domain must be verified in domain search dashboard; unverified yields 403. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Response shapes (documented)**
  - 200: JSON object mapping alias → array of website domains: [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    ```json
    {
      "andy": ["netflix.com"],
      "jane": ["netflix.com", "spotify.com"]
    }
    ```
  - 403: unverified email domain. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

#### Additional stealer-log notes

- All stealer-log APIs have their **own** lower rate limit than breach search due to heavy data; separate throttling and 429s apply. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- No API returns passwords directly; passwords are instead added to Pwned Passwords. [haveibeenpwned](https://haveibeenpwned.com/breach/StealerLogsJan2025)
- HIBP emphasizes that stealer-log data is prepared by criminals with no guarantees of accuracy; presence of an email+domain pair indicates that is what was in the log, not that the user definitely used that service. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)

---

### 6. Pastes API — `/pasteaccount/{account}`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/pasteaccount/{account}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Return all pastes where the given email address appears; often leak indicators or sources of credential dumps. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Supported `entity_type`(s)**
  - `email`.
- **Auth / execution**
  - Requires `hibp-api-key` and `user-agent`. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response schema (documented paste model)** [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Each paste:
    - `Source` (string) — paste service; values include `Pastebin`, `Pastie`, `Slexy`, `Ghostbin`, `QuickLeak`, `JustPaste`, `AdHocUrl`, `PermanentOptOut`, `OptOut`.
    - `Id` (string) — source paste ID (combine with `Source` to construct URL).
    - `Title` (string, optional) — may be null and omitted when absent. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `Date` (datetime, optional) — may be null if source doesn’t publish a date. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `EmailCount` (integer) — count of email addresses detected via documented regex. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response variants**
  - 200: array of paste entities, newest first. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 404: no pastes for account — **derived** from generic response-code semantics; v3 paste docs don’t explicitly restate 404 but v2 behaviour and global table are consistent. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

### 7. Subscription status — `/subscription/status`

- **Endpoint**
  - `GET https://haveibeenpwned.com/api/v3/subscription/status` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - Report current subscription tier and limits, including RPM and stealer-logs capability; used for client-side gating and capacity planning. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response schema (documented)**
  - `SubscriptionName` (string) — “Pwned 1”, “Pwned 2”, “Pwned 3”, “Pwned 4” etc.
  - `Description` (string) — human-readable description.
  - `SubscribedUntil` (datetime).
  - `Rpm` (integer) — breach-search requests per minute. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - `DomainSearchMaxBreachedAccounts` (integer) — max domain size by breached accounts (excluding spam lists). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - `IncludesStealerLogs` (bool) — whether stealer log APIs are available. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

### 8. Pwned Passwords API — `/range/{first 5 hash chars}`

- **Endpoint**
  - `GET https://api.pwnedpasswords.com/range/{first 5 hash chars}` [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Purpose**
  - K-anonymity search of HIBP’s password corpus; used to test whether a password hash prefix appears in known breached passwords, without revealing the full hash or plaintext. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Supported `entity_type`(s)**
  - Conceptually `hash` or `password`; **no direct email/entity link**.
- **Auth / execution**
  - No API key required; free API, no rate limit documented. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Optional headers/params:
    - `Add-Padding: true` — ensures 800–1000 results (padded entries with count 0) for traffic analysis resistance. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
    - `mode=ntlm` — return NTLM suffixes (27 chars) vs SHA-1 (35 chars). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Response shape (documented)**
  - Always 200 (no 404 ever), for any of the 1,048,576 possible 5-char prefixes. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Body: text lines `HASH_SUFFIX:COUNT`, one per matching password. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Notes**
  - Used extensively for password hygiene; not directly linked to breach entities. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

### 9. Common response codes, rate limits, and CORS

- **Response codes (documented table)** [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 200: Ok.
  - 400: Bad request, invalid account format.
  - 401: Unauthorised (missing/invalid API key).
  - 403: Forbidden (missing user agent, unverified domain, or unauthorized resource).
  - 404: Not found (no breach/paste/stealer-log entries for account/domain; or breach name not found).
  - 429: Too many requests (rate limit exceeded; includes `retry-after` in seconds). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - 503: Service unavailable (often Cloudflare protection or backend issues). [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Rate limiting**
  - Breach, paste, and stealer APIs are rate-limited according to subscription `Rpm`; stealer log endpoints have their own lower limits; domain-search API has no formal limit but abuse can be throttled and return 429. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - Pwned Passwords has **no rate limit**. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **CORS**
  - Only non-authenticated APIs (e.g. Pwned Passwords) support CORS; authenticated APIs must be proxied to avoid exposing keys. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

## B. Module Mapping Table

### Module–endpoint mapping (`breach_monitor`)

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| breach_monitor | signal_producer | breachedaccount(account) | `GET /api/v3/breachedaccount/{account}` | direct_signal_input | email, username, phone | Require valid `hibp-api-key` and `user-agent`; only create signals on HTTP 200; treat 404 as “no known breach / possibly opted-out” (no signal); optionally expand each `Name` via `/breach/{name}` or `truncateResponse=false` for full evidence. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Core per-account breach feed. |
| breach_monitor | signal_producer | breacheddomain(domain) | `GET /api/v3/breacheddomain/{domain}` | direct_signal_input | domain → email | Domain must be verified; 403 means “no access” not “no breaches”; on 200, expand each alias+breach pair into per-email breach signals (`alias@domain`), same signal types as `breachedaccount`; on 404, no signals. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Bulk enumeration source; dedupe against `breachedaccount`. |
| breach_monitor | enrichment | breaches(filter) | `GET /api/v3/breaches` | enrichment_only | breach (metadata) | Queried periodically (e.g. daily) to hydrate local catalogue of breach metadata, data classes, and flags; not used alone to create per-account signals. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Used to enrich breach signals with `PwnCount`, `Description`, flags. |
| breach_monitor | enrichment | breach(name) | `GET /api/v3/breach/{name}` | enrichment_only | breach (metadata) | Called when only `Name` is available (truncated responses) or to refresh metadata; no standalone signal. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Avoid per-signal synchronous lookups; cache locally. |
| breach_monitor | enrichment | latestbreach() | `GET /api/v3/latestbreach` | enrichment_only | breach (metadata) | Used as a cheap poll to decide when to re-sync domain search / local catalogue; not directly signal-producing. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Optimization for polling cadence. |
| breach_monitor | enrichment | dataclasses() | `GET /api/v3/dataclasses` | enrichment_only | n/a | Used to validate mapping of `DataClasses` strings and potentially to maintain allowlist; not directly signal-producing. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Data-class vocabulary. |
| breach_monitor | utility | subscribeddomains() | `GET /api/v3/subscribeddomains` | utility_only | domain | Use to discover which domains can be safely queried via `breacheddomain` and stealer-log domain endpoints; also to understand breach volume per domain. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Helps preconfigure monitored domains and capacity planning. |
| breach_monitor | utility | subscription_status() | `GET /api/v3/subscription/status` | utility_only | n/a | Called at startup / periodically to determine `Rpm`, `DomainSearchMaxBreachedAccounts`, and `IncludesStealerLogs`; used to gate use of stealer-log endpoints and to tune rate limiting. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Do not emit signals from this; purely config. |
| breach_monitor | signal_producer | stealerlogsbyemail(email) | `GET /api/v3/stealerlogsbyemail/{email}` | direct_signal_input | email, domain | Only call for email domains you control (verified in dashboard) and if `IncludesStealerLogs=true`; on 200, produce one stealer-log credential exposure per `(email, websiteDomain)` pair; 404 is no data (no signal). | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Strong, near-real-time evidence of credential capture. |
| breach_monitor | signal_producer | stealerlogsbyemaildomain(domain) | `GET /api/v3/stealerlogsbyemaildomain/{domain}` | direct_signal_input | domain → email, domain | Same gating as above; on 200, flatten alias+domain array into per `(email, websiteDomain)` exposure signals; 403 unverified domain, 404 not documented (treat lack of body/empty as no signal if encountered). | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Bulk pivot for corporate domains; high leverage but potentially large volumes. |
| breach_monitor | signal_producer | stealerlogsbywebsitedomain(domain) | `GET /api/v3/stealerlogsbywebsitedomain/{domain}` | direct_signal_input | domain → email | Domain must be verified; on 200, produce per-email exposure for that website domain; primarily used when your own site is the website domain. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Lets you see which accounts on your own site are exposed. |
| breach_monitor | signal_producer | pasteaccount(account) | `GET /api/v3/pasteaccount/{account}` | direct_signal_input | email | Requires API key; on 200, each paste is a candidate “email found in paste” signal; likely lower severity; on 404 (derived) no signal. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Good early indicator, but contents of paste are not exposed via API. |
| breach_monitor | out_of_scope | pwned_passwords_range(prefix) | `GET https://api.pwnedpasswords.com/range/{prefix}` | out_of_scope | hash/password | Not directly tied to breach entities; more appropriate for a password hygiene / credential module; treat as out-of-scope for `breach_monitor` at this stage. | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Can be revisited for a `password_strength` or `secrets` module. |

---

## C. Signal Contract Table

### Standalone signal contracts for `breach_monitor`

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| breach_monitor | breach_monitor | hibp | `breachedaccount`, `breacheddomain` (flattened per account) | account_breached | identity_security | high | yes | Default high; downgrade to medium when breach `DataClasses` lacks any password-related classes and appears to be contact/PII only; downgrade to low when `IsSpamList=true`; optionally upgrade to critical when `IsStealerLog=true` or `IsMalware=true` *and* `DataClasses` includes password-related items. | email | true_finding | HTTP 200 from `/breachedaccount/{account}` or `/breacheddomain/{domain}`; for each breach object B associated with an account A where the breach is not retired (`IsRetired=false`), generate one signal per `(A,B)`; `IsSensitive` and opt-outs are already filtered by API (no additional filter needed). | From breach model for the matched breach: `Name`, `Title`, `Domain`, `BreachDate`, `AddedDate`, `ModifiedDate`, `PwnCount`, `DataClasses`, `IsVerified`, `IsFabricated`, `IsSensitive`, `IsRetired`, `IsSpamList`, `IsMalware`, `IsSubscriptionFree`, `IsStealerLog`, `LogoPath`, `Attribution`; plus the queried account/email. | `Description` HTML, any locally cached breach metadata from `/breach/{name}` or `/breaches`, and test-account flags when using test domain; subscription tier and domain verification state (for internal debugging, not user-facing). | `Account {entity} was exposed in the {breach_title} breach on {breach_date}, leaking: {data_classes}.` | documented | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Use `truncateResponse=false` or hydrate via `/breach/{name}` to get full evidence; ensure dedupe across `breachedaccount` and `breacheddomain` by using `(email, breach Name)` as key. Treat 404 as “no known breach / possibly opted out”. |
| breach_monitor | breach_monitor | hibp | `stealerlogsbyemail`, `stealerlogsbyemaildomain`, `stealerlogsbywebsitedomain` | stealer_log_credential_exposure | identity_security | critical | yes | Critical when any stealer-log entry exists (direct credential capture by malware); optionally downgrade to high if organisational policy wants to treat historical logs >X days old as reduced urgency once password resets are confirmed. | email | true_finding | HTTP 200 from any stealer-log endpoint; for each `(email, websiteDomain)` pair returned (directly from `stealerlogsbyemail` or via expanding alias/domain objects), emit one signal keyed on email with website domain in evidence; restrict queries to email domains and/or website domains you control (domain dashboard verified). | Email address, website domain(s) returned, the API path used (`stealerlogsbyemail` vs `stealerlogsbyemaildomain` vs `stealerlogsbywebsitedomain`), and any matching HIBP breach entries where `IsStealerLog=true` for that email (if cross-queried). | Subscription metadata including `IncludesStealerLogs`, last time domain search/stealer scan was run, and linked Pwned Passwords hit count for the associated password hash if looked up separately; domain verification status used to allow the query (for audit). | `Credentials for {entity} were captured in stealer logs while logging into {website_domain}.` | documented/derived | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Domain verification and Pwned 5+ subscription are hard preconditions; API never returns passwords, but the `StealerLogsJan2025` breach description confirms logs contain email+password+website, so treat as direct credential exposure. Handle large result sets carefully (batching, backoff). |
| breach_monitor | breach_monitor | hibp | `pasteaccount` | paste_account_exposed | identity_security | medium | yes | Default medium; downgrade to low for very old pastes (e.g. `Date` older than configurable threshold) or when pastes are clearly spam/low risk based on `Source`/`Title` heuristics (implementation-time decision); upgrade to high only when corroborated with a specific breach and recent activity. | email | true_finding | HTTP 200 from `/pasteaccount/{account}`; for each paste object where the queried email address is present, emit one signal per `(account, pasteId)` or aggregate by account if volume is high. | `Source`, `Id`, `Title` (if present), `Date` (if present), `EmailCount`, and the queried email; optionally derived URL for the paste if reconstructed client-side for investigation. | Linked HIBP breach results for the same account (if any), internal age buckets (e.g. “<6 months”, “6–24 months”, “>24 months”), and any internal classification you add later (e.g. “likely credential dump” vs “generic email list”) but these are *not* separate signals. | `Email {entity} was found in a public paste ({source} ID {paste_id}) on {paste_date}.` | documented/derived | [haveibeenpwned](https://haveibeenpwned.com/api/v3) | API surface doesn’t reveal paste contents; treat as strong indicator of data leakage but weaker than confirmed credential breaches; dedupe by `(email, Source, Id)`. 404 semantics for “no pastes” are inferred from global response-code docs. |

---

## D. Severity Rules

### 1. `account_breached`

- **Baseline severity**: **high**, because this is a confirmed account in a known breach dataset, often exposing at least email, usernames, and sometimes passwords or other PII. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Conditional rules (derived from documented fields)** [haveibeenpwned](https://haveibeenpwned.com/api/v3)
  - **Critical** when:
    - The matching breach has `IsStealerLog=true` **or** `IsMalware=true`, **and** `DataClasses` contains any password-related class (e.g. strings containing “Password”), reflecting direct credential capture or malware-sourced compromise.
  - **Medium** when:
    - `IsSpamList=true` is **false**, but `DataClasses` shows only contact/marketing data (e.g. “Email addresses” + non-credential items) and no password-related classes.
  - **Low** when:
    - `IsSpamList=true` (documented as not necessarily the result of a security compromise) and no additional corroborating breach with stronger indicators is present. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Alignment with your calibration guide**
  - Direct credential exposures or malware/stealer breaches → **critical**.
  - Confirmed breaches of PII and likely credentials → **high**.
  - PII-only or marketing-type exposures → **medium/low**.

### 2. `stealer_log_credential_exposure`

- **Severity**: **critical** by default.
  - HIBP’s stealer logs are created by malware that captures real-time credentials (email + password + website) as the user logs in. [haveibeenpwned](https://haveibeenpwned.com/breach/StealerLogsJan2025)
  - This matches your “critical” category: direct credential exposure and active stealer logs.
- **Conditional downgrades (optional)**
  - After Zima has confirmed password resets and 2FA rollout for affected accounts, you may choose to downgrade old, remediated findings to **high** for historical context; that conditional rule would be implemented in your correlation layer rather than mapper.

### 3. `paste_account_exposed`

- **Baseline severity**: **medium**.
  - Being present in a public paste is a strong indicator that the email address appears in leaked material, but the API does not guarantee password presence; risk is “suspicious / historical exposure” rather than confirmed credential breach. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Conditional rules**
  - **Low** when:
    - Paste is very old (e.g. several years) and there is no corroborating breach for the same account, or when internal heuristics classify it as low-risk spam/marketing based on `Title`/`Source` (implementation-time heuristic, **inferred**).
  - **High** when:
    - Paste is recent and correlated with known breach campaigns or credentials in other sources (e.g. same account appears in fresh breach plus paste references credential dumps; **to be implemented once more telemetry is available**).

### Assessment vs your first-pass notion of severity

- HIBP data supports a more nuanced severity model than a flat “varies”: breaches with passwords or malware/stealer flags are high-critical, pure PII/contact exposures are medium, and spam lists plus old pastes can be downgraded to low. [haveibeenpwned](https://haveibeenpwned.com/breach/StealerLogsJan2025)
- These rules are **derived** strictly from documented flags (`IsSpamList`, `IsMalware`, `IsStealerLog`, `DataClasses`) plus your own calibration definitions.

---

## E. Confidence Guidance

### Confidence and calibration table

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| breach_monitor | account_breached | HIBP breach datasets are curated and documented; `IsVerified` distinguishes confirmed vs unverified breaches; `IsFabricated` marks suspected fabrications; overall, reliability is high but not perfect. [haveibeenpwned](https://haveibeenpwned.com/api/v3) | `BreachDate` may be much earlier than `AddedDate`; new breaches are added over time; use `AddedDate` and `ModifiedDate` to track recency; periodically resync via `/latestbreach` and `/breaches`. [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Correlate with other providers (e.g. other breach feeds, dark web sources) and internal login telemetry; treat unverified or fabricated breaches as lower-confidence until corroborated; consider raising confidence when `DataClasses` includes passwords and you see matching credential-stuffing or suspicious logins. | Collect empirical stats on which breach types (by `DataClasses`, `IsSpamList`, `IsMalware`, `IsStealerLog`) precede actual account compromise in customer environments; tune severity and confidence thresholds accordingly. |
| breach_monitor | stealer_log_credential_exposure | HIBP stealer logs are derived from real malware telemetry; Troy Hunt notes that presence of an email+domain pair means exactly that is in the stealer log, but criminals provide no guarantees of correctness (e.g. some domains may be malformed or misleading). [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/) | Stealer logs can recirculate; the same logs may appear across multiple collections; no explicit timestamp per pair is exposed via API (timeliness mostly comes from which corpus was just loaded). [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/) | Correlate with: (1) internal login attempts to the indicated website domain, (2) password reuse detection via Pwned Passwords, (3) other threat intel sources showing credential stuffing from the same IP ranges; downgrade confidence if email+domain pair looks implausible or there is no supporting activity over time. | Track how often stealer-log signals precede actual account takeover or suspicious logins; derive empirical thresholds for automatic password resets / forced reauth; determine whether to weight `IsStealerLog` breaches differently from stand-alone stealer-log domain pairs. |
| breach_monitor | paste_account_exposed | HIBP paste ingestion uses regex-based email extraction across multiple services; pastes may be deleted or inaccurate; they are weaker evidence than structured breaches but still meaningful as exposure indicators. [haveibeenpwned](https://haveibeenpwned.com/api/v3) | `Date` may be null or missing; where present, use it as primary staleness indicator; treat very old pastes as lower risk but still informative; recent pastes may indicate active leakage or pre-breach staging. [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Correlate paste presence with breaches, stealer logs, and phishing/spam campaigns; for example, if the same email appears in a recent breach and a paste from the same timeframe, increase confidence; if paste is the only source and is very old, treat as low-confidence and mostly contextual. | Build a simple age-based weighting model for paste signals and calibrate default severities against internal incident response outcomes; optionally sample paste URLs (out-of-band) for a small cohort to understand typical content without automating retrieval. |
| breach_monitor | enrichment via `/breaches` and `/breach` | Breach metadata is directly maintained by HIBP; fields like `PwnCount`, `Description`, and `DataClasses` are authoritative for that dataset; minor inaccuracies possible in public descriptions or counts. [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Metadata can be updated over time (`ModifiedDate` > `AddedDate`); ensure caches are refreshed at reasonable intervals (e.g. daily/weekly); do not treat one-time snapshots as immutable. [haveibeenpwned](https://haveibeenpwned.com/api/v3) | Use metadata as context, not as standalone proof; for example, do not assert password exposure solely from natural-language `Description`; rely instead on `DataClasses` and other sources; when conflicting descriptions or counts arise across sources, prefer HIBP’s structured model but record discrepancies. | Instrument how often metadata (e.g. `IsSpamList`, `IsSensitive`, `IsMalware`) drives analyst decisions and whether misclassifications occur; adjust UI labelling rather than signal semantics to improve human understanding. |

---

## F. Provider Summary

### Strongest signal types

- **Per-account breach membership (`account_breached`)**: High-quality, curated breach data that directly states whether a specific account appears in one or more breaches, with structured metadata including data classes and verification flags. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Stealer-log credential exposures (`stealer_log_credential_exposure`)**: Near-real-time evidence that credentials for an account have been captured by malware, including which websites they were entered into; this is highly actionable and maps cleanly to critical severity. [haveibeenpwned](https://haveibeenpwned.com/breach/StealerLogsJan2025)
- **Paste-based email exposure (`paste_account_exposed`)**: Early-warning indicator that an email address appears in public pastes, often associated with dumps or staging of breach data; useful but lower confidence than structured breaches. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

### What HIBP should *not* be used for in `breach_monitor`

- **Password-strength or password-policy enforcement**: Pwned Passwords `/range` is perfect for this, but it is hash/password-centric and should belong in a dedicated password/secret hygiene module, not `breach_monitor`. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **General dark-web or threat-actor attribution**: HIBP does not provide actor attribution, infrastructure indicators, or broader dark-web context; it is focused on breach exposure, stealer logs, and pastes. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Real-time login telemetry or behaviour analytics**: HIBP is not a SIEM, does not see your login streams, and is not suited for session-based anomaly detection; use it as external evidence to augment internal telemetry.

### API/auth/rate-limit/licensing cautions

- **Keys and user agents are mandatory**: All email/domain and stealer-log endpoints require `hibp-api-key` and a descriptive `user-agent`; missing user-agent yields 403. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Subscription tier gating**: The `/subscription/status` endpoint must be consulted to respect `Rpm`, `DomainSearchMaxBreachedAccounts`, and `IncludesStealerLogs`; attempting stealer-log calls without the right tier will fail. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **Domain verification gating**: `/breacheddomain` and all stealer-log domain endpoints only work for domains added to the domain search dashboard and verified; 403 does not mean “no data”, only “no access”. [troyhunt](https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/)
- **Rate limits and backoff**: Exceeding limits returns 429 with `retry-after`; stealer logs additionally enforce lower, independent limits; repeated abuse may trigger Cloudflare-level blocks and 503s. [haveibeenpwned](https://haveibeenpwned.com/api/v3)
- **CORS and frontend usage**: Authenticated APIs must not be called directly from browsers; they are not CORS-enabled; always proxy through your backend. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

### Overall role for Zima (current stage)

- In the current Zima stage, HIBP should be treated as a **signal-producing provider** for `breach_monitor`, with:
  - `breachedaccount` / `breacheddomain` → primary breach membership signals.
  - stealer-log endpoints → critical stealer-log credential exposure signals.
  - `pasteaccount` → medium/low severity paste exposure signals.
- The rest of the API surface (`/breaches`, `/breach`, `/dataclasses`, `/subscribeddomains`, `/subscription/status`, Pwned Passwords) should be used as **enrichment** or **utility** only, not as standalone signal sources in this module. [haveibeenpwned](https://haveibeenpwned.com/api/v3)

---

## G. Structured JSON

```json
{
  "provider": "hibp",
  "provider_category": "breach",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "breachedaccount(account)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/breachedaccount/{account}",
      "classification": "direct_signal_input",
      "entity_types": ["email", "username", "phone"],
      "gating_logic": "Require valid hibp-api-key and user-agent. Only create signals on HTTP 200. Treat 404 as 'no known breach or opted-out' and do not emit signals. Optionally hydrate each breach Name via /breach/{name} or set truncateResponse=false to obtain full breach model.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Core per-account breach feed; use (account, breach Name) as dedupe key."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "breacheddomain(domain)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/breacheddomain/{domain}",
      "classification": "direct_signal_input",
      "entity_types": ["domain", "email"],
      "gating_logic": "Domain must be verified in HIBP domain search dashboard; 403 means unverified, not 'no breaches'. On 200, expand alias keys to full emails (alias@domain) and generate same breach signals as breachedaccount. On 404, emit no signals.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Bulk enumeration source; dedupe against breachedaccount results."
    },
    {
      "module": "breach_monitor",
      "provider_role": "enrichment",
      "provider_method": "breaches(filter)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/breaches",
      "classification": "enrichment_only",
      "entity_types": ["breach"],
      "gating_logic": "Periodic sync; no per-entity gating other than optional Domain and IsSpamList filters.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Hydrates breach metadata and data classes for use in signals and UI."
    },
    {
      "module": "breach_monitor",
      "provider_role": "enrichment",
      "provider_method": "breach(name)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/breach/{name}",
      "classification": "enrichment_only",
      "entity_types": ["breach"],
      "gating_logic": "Lookup by stable Name; 404 means no such breach defined.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Use to hydrate full breach model when only Name is known or to refresh stale metadata."
    },
    {
      "module": "breach_monitor",
      "provider_role": "enrichment",
      "provider_method": "latestbreach()",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/latestbreach",
      "classification": "enrichment_only",
      "entity_types": ["breach"],
      "gating_logic": "No parameters; returns most recently added breach.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Use to decide when to re-run domain or account scans after new breach ingestion."
    },
    {
      "module": "breach_monitor",
      "provider_role": "enrichment",
      "provider_method": "dataclasses()",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/dataclasses",
      "classification": "enrichment_only",
      "entity_types": [],
      "gating_logic": "No parameters; simple list of strings.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Maintains vocabulary of DataClasses for mapping and display."
    },
    {
      "module": "breach_monitor",
      "provider_role": "utility",
      "provider_method": "subscribeddomains()",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/subscribeddomains",
      "classification": "utility_only",
      "entity_types": ["domain"],
      "gating_logic": "Requires hibp-api-key; returns only domains tied to that key.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Used to seed list of domains eligible for breacheddomain and stealer-log domain queries."
    },
    {
      "module": "breach_monitor",
      "provider_role": "utility",
      "provider_method": "subscription_status()",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/subscription/status",
      "classification": "utility_only",
      "entity_types": [],
      "gating_logic": "Requires hibp-api-key; returns subscription limits including Rpm and IncludesStealerLogs.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Should be called at startup or periodically to tune rate limiting and feature usage."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "stealerlogsbyemail(email)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/stealerlogsbyemail/{email}",
      "classification": "direct_signal_input",
      "entity_types": ["email", "domain"],
      "gating_logic": "Email domain must be verified in domain search; subscription must have IncludesStealerLogs=true. On 200, produce one stealer-log credential exposure per (email, websiteDomain). On 404, no signal.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3", "https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/"],
      "notes": "Strongest per-account stealer-log signal; beware rate limits specific to stealer-log APIs."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "stealerlogsbyemaildomain(domain)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/stealerlogsbyemaildomain/{domain}",
      "classification": "direct_signal_input",
      "entity_types": ["domain", "email", "domain_website"],
      "gating_logic": "Email domain must be verified; stealer-log subscription required. On 200, flatten alias->domains map into per (alias@domain, websiteDomain) exposures.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3", "https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/"],
      "notes": "Bulk pivot for corporate domains; careful with paging/batching and dedupe with stealerlogsbyemail."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "stealerlogsbywebsitedomain(domain)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/stealerlogsbywebsitedomain/{domain}",
      "classification": "direct_signal_input",
      "entity_types": ["domain", "email"],
      "gating_logic": "Website domain must be verified; stealer-log subscription required. On 200, produce per-email exposures for that website domain.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3", "https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/"],
      "notes": "Best suited when your own site is the website domain; can be very high volume for popular services."
    },
    {
      "module": "breach_monitor",
      "provider_role": "signal_producer",
      "provider_method": "pasteaccount(account)",
      "endpoint_or_artifact": "GET https://haveibeenpwned.com/api/v3/pasteaccount/{account}",
      "classification": "direct_signal_input",
      "entity_types": ["email"],
      "gating_logic": "On 200, treat each paste model as a potential exposure signal for the queried email. On 404 (inferred), no signal.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Weaker than structured breach data; use primarily as an exposure indicator."
    },
    {
      "module": "breach_monitor",
      "provider_role": "out_of_scope",
      "provider_method": "pwned_passwords_range(prefix)",
      "endpoint_or_artifact": "GET https://api.pwnedpasswords.com/range/{first5}",
      "classification": "out_of_scope",
      "entity_types": ["hash", "password"],
      "gating_logic": "No key required; always returns 200 with suffix list. Not used by breach_monitor.",
      "citation_refs": ["https://haveibeenpwned.com/api/v3"],
      "notes": "Reserved for a separate password or secret-hygiene module."
    }
  ],
  "signal_contracts": [
    {
      "module": "breach_monitor",
      "source": "breach_monitor",
      "provider": "hibp",
      "provider_method": "breachedaccount, breacheddomain",
      "signal_type": "account_breached",
      "category": "identity_security",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "Default high. Downgrade to medium when DataClasses contains only contact/PII and no password-related classes. Downgrade to low when IsSpamList=true. Optionally upgrade to critical when (IsStealerLog=true OR IsMalware=true) AND DataClasses includes password-related classes.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "HTTP 200 from /breachedaccount/{account} or /breacheddomain/{domain}. For each breach object B linked to account A where IsRetired=false, emit one signal keyed by (A, B.Name). Sensitive and opted-out breaches are already suppressed by the API.",
      "evidence_fields": [
        "account",
        "Name",
        "Title",
        "Domain",
        "BreachDate",
        "AddedDate",
        "ModifiedDate",
        "PwnCount",
        "Description",
        "DataClasses",
        "IsVerified",
        "IsFabricated",
        "IsSensitive",
        "IsRetired",
        "IsSpamList",
        "IsMalware",
        "IsSubscriptionFree",
        "IsStealerLog",
        "LogoPath",
        "Attribution"
      ],
      "enrichment_fields": [
        "subscription tier (from /subscription/status)",
        "latestbreach metadata for correlation",
        "dataclasses vocabulary for display"
      ],
      "summary_template": "Account {entity} was exposed in the {breach_title} breach on {breach_date}, leaking: {data_classes}.",
      "evidence_status": "documented",
      "citation_refs": [
        "https://haveibeenpwned.com/api/v3"
      ],
      "notes": "Use (account, breach Name) as natural dedupe key across breachedaccount and breacheddomain. Treat 404 as 'no known breach or opted out' and avoid negative assertions."
    },
    {
      "module": "breach_monitor",
      "source": "breach_monitor",
      "provider": "hibp",
      "provider_method": "stealerlogsbyemail, stealerlogsbyemaildomain, stealerlogsbywebsitedomain",
      "signal_type": "stealer_log_credential_exposure",
      "category": "identity_security",
      "severity": "critical",
      "severity_is_conditional": "yes",
      "conditional_rule": "Critical whenever any stealer-log entry exists for an account, as this represents direct credential capture by malware. Optionally downgrade to high after credentials have been rotated and sufficient time has passed, as determined by internal policy.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "HTTP 200 from any stealer-log endpoint. For each (email, websiteDomain) pair returned—either from stealerlogsbyemail directly or by expanding objects from stealerlogsbyemaildomain or stealerlogsbywebsitedomain—emit one signal keyed by (email, websiteDomain). Only query domains and email domains verified in HIBP's domain dashboard and when IncludesStealerLogs=true in subscription status.",
      "evidence_fields": [
        "email",
        "website_domain",
        "source_endpoint (stealerlogsbyemail | stealerlogsbyemaildomain | stealerlogsbywebsitedomain)"
      ],
      "enrichment_fields": [
        "subscription.IncludesStealerLogs",
        "subscription.Rpm",
        "subscribeddomains.DomainName",
        "any linked breach entries where IsStealerLog=true",
        "optional Pwned Passwords hit count if looked up separately"
      ],
      "summary_template": "Credentials for {entity} were captured in stealer logs while logging into {website_domain}.",
      "evidence_status": "documented",
      "citation_refs": [
        "https://haveibeenpwned.com/api/v3",
        "https://www.troyhunt.com/experimenting-with-stealer-logs-in-have-i-been-pwned/",
        "https://haveibeenpwned.com/breach/StealerLogsJan2025"
      ],
      "notes": "Passwords are not returned via API, but StealerLogsJan2025 breach documentation confirms logs contain email, password and website. Treat as direct credential exposure; handle separate, lower rate limit for stealer-log APIs."
    },
    {
      "module": "breach_monitor",
      "source": "breach_monitor",
      "provider": "hibp",
      "provider_method": "pasteaccount",
      "signal_type": "paste_account_exposed",
      "category": "identity_security",
      "severity": "medium",
      "severity_is_conditional": "yes",
      "conditional_rule": "Default medium. Downgrade to low when paste Date is older than a configurable threshold and not corroborated by other breaches. Optionally upgrade to high when paste is recent and aligned with known breach or credential-dump campaigns, as determined by additional telemetry.",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "HTTP 200 from /pasteaccount/{account}. For each paste object associated with the queried account, emit one signal keyed by (account, Source, Id) or aggregate multiple pastes into a single signal if necessary for noise reduction.",
      "evidence_fields": [
        "account",
        "Source",
        "Id",
        "Title",
        "Date",
        "EmailCount"
      ],
      "enrichment_fields": [
        "reconstructed paste URL (Source + Id) for analyst investigation",
        "age_bucket derived from Date",
        "linked breaches for the same account"
      ],
      "summary_template": "Email {entity} was found in a public paste ({source}, ID {paste_id}) on {paste_date}.",
      "evidence_status": "documented",
      "citation_refs": [
        "https://haveibeenpwned.com/api/v3"
      ],
      "notes": "Paste contents are not exposed via API; use presence of the account in a paste as an exposure indicator. Treat 404 as 'no pastes known' (derived from global response-code semantics)."
    }
  ],
  "confidence_guidance": [
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "account_breached",
      "source_reliability": "HIBP curates breach data with verification and fabrication flags; overall reliability is high but some breaches are unverified or marked fabricated.",
      "freshness_considerations": "Use AddedDate and ModifiedDate to understand when a breach was loaded or updated. BreachDate may significantly predate detection. Periodically refresh metadata via /breaches and /latestbreach.",
      "corroboration_rules": "Cross-check with other breach feeds and internal login telemetry. Treat unverified or fabricated breaches as lower-confidence, and raise confidence when DataClasses includes passwords and you observe credential-stuffing or suspicious logins for the same account.",
      "calibration_todo": "Gather statistics on how often different breach types lead to real incidents; tune severity mapping for IsSpamList, IsMalware, IsStealerLog and different DataClasses based on those outcomes."
    },
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "stealer_log_credential_exposure",
      "source_reliability": "Stealer log data is sourced from malware; HIBP emphasises that criminals provide no accuracy guarantees, but presence of an email+domain pair reflects exactly what appears in the logs.",
      "freshness_considerations": "Stealer logs can be recirculated; API does not surface timestamps per pair. Treat most recently loaded corpora as higher priority, but recognise some entries may be older.",
      "corroboration_rules": "Correlate with internal login logs to the indicated website domains, password reuse indicators, and other threat intel. Downgrade confidence where domains are malformed or inconsistent with known user behaviour.",
      "calibration_todo": "Track how often stealer-log exposures precede account takeover or suspicious activity. Use this to refine when to automatically force password resets or trigger higher-severity workflows."
    },
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "paste_account_exposed",
      "source_reliability": "Paste detection relies on regex-based email extraction across multiple services; some pastes may be spam or low quality, but overall presence is a meaningful exposure indicator.",
      "freshness_considerations": "Use Date when present; treat very old pastes as lower risk while still informative. For null Date values, be conservative and rely on corroboration instead of assuming freshness.",
      "corroboration_rules": "Look for overlap with breach and stealer-log signals, and with internal phishing/spam campaigns. Use multiple paste hits in a short window as stronger evidence than a single, old paste.",
      "calibration_todo": "Build an age-based weighting model and evaluate how paste findings correlate with downstream incidents; adjust default severities to minimise noise while preserving early warnings."
    },
    {
      "module": "breach_monitor",
      "signal_type_or_use_case": "breach metadata enrichment via /breaches and /breach",
      "source_reliability": "Structured breach model fields from HIBP are authoritative for that dataset; textual descriptions may contain minor inaccuracies but are generally reliable.",
      "freshness_considerations": "Because breaches can be modified (ModifiedDate), periodically refresh local metadata; do not assume initial snapshots are permanent.",
      "corroboration_rules": "Use DataClasses and flags (IsSpamList, IsSensitive, IsMalware, IsStealerLog) in combination with other sources to drive severity and tagging; do not rely solely on free-text Description for critical decisions.",
      "calibration_todo": "Monitor how analysts use metadata in triage and whether misunderstandings arise; refine internal documentation and UI labelling rather than changing signal semantics."
    }
  ]
}
```
