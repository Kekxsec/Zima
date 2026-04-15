---
title: "output / reputation / emailrep"
aliases: ["emailrep output", "emailrep signal registry"]
tags: [zima, research, outputs, signal-registry, reputation, emailrep, graph_exclude]
type: provider_research_output
provider: emailrep
provider_category: reputation
status: not_started
prompt_note: prompt.md
provider_folder: emailrep.md
obsidianUIMode: preview
kind: artifact
llm_include: false
code_scope: backend
---
# EmailRep integration research for Zima

## API Surface Appendix

### HTTP API: query email reputation

**Endpoint / method**
`GET https://emailrep.io/{email}` 

**Purpose**
Returns a reputation/risk assessment and supporting “details” for a single email address, including indicators for malicious activity, leaked credentials, historical data breach presence, and deliverability / domain posture signals. 

**Supported entity_type(s)**
`email` (email address in the path). 

**Auth / execution requirements**
An API key programme exists (Community / Commercial / Enterprise), with published quotas (e.g., Community: 250 queries/month and up to 10 queries/day; Commercial: 1000 queries/month and no daily limit). 
Official examples show unauthenticated `curl emailrep.io/<email>` usage, but the docs-visible “minimum request header” details were not retrievable from the vendor reference site via this research tool, so the precise authentication header for `GET` should be treated as **unclear** from primary docs here. 
Third‑party client examples commonly send an API key header (case-insensitive variants like `Key:`), suggesting authenticated requests are supported; treat as **inferred** until you confirm against current vendor docs. 

**Query parameters**
`summary=true` (boolean flag) — documented by the provider as an option to return a human-readable explanation of why an email is suspicious. 
The _response field name_ for this human summary is **not explicitly shown** in vendor primary docs excerpts available here; third-party clients expect a top-level `summary` string, so treat `summary` as **inferred from examples** until confirmed in current vendor docs. 

**Top-level response fields and types**
From vendor examples and vendor-maintained repo documentation: 

- `email`: string (the queried email) 
- `reputation`: string enum: `high | medium | low | none` 
- `suspicious`: boolean 
- `references`: number (count of positive + negative sources; may include domain/related info not directly referencing the email) 
- `details`: object 
- `summary`: string (only when `?summary=true`) — **inferred** from third‑party clients; vendor describes its presence conceptually but not the field name in the excerpted primary materials here. 

**Nested object: `details` fields**
Vendor-maintained documentation describes the following `details.*` keys (all are implementation-relevant for Zima mapping). 

- `details.blacklisted`: boolean — believed malicious/spammy 
- `details.malicious_activity`: boolean — exhibited malicious behaviour (e.g., phishing/fraud) 
- `details.malicious_activity_recent`: boolean — malicious behaviour in the last 90 days 
- `details.credentials_leaked`: boolean — credentials leaked at some point (e.g., data breach, pastebin, dark web) 
- `details.credentials_leaked_recent`: boolean — credentials leaked in the last 90 days 
- `details.data_breach`: boolean — email was in a data breach at some point 
- `details.first_seen`: date-like string OR the literal string `'never'` (described as the first date observed in breach/leak/malicious/spam; `'never'` if never seen) 
- `details.last_seen`: date-like string OR `'never'` (last date observed in breach/leak/malicious/spam; `'never'` if never seen) 
- `details.domain_exists`: boolean 
- `details.domain_reputation`: string enum: `high | medium | low | n/a` (with `n/a` conditions described by vendor: when free_provider/disposable/nonexistent) 
- `details.new_domain`: boolean — created within last year 
- `details.days_since_domain_creation`: number 
- `details.suspicious_tld`: boolean 
- `details.spam`: boolean — spammy behaviour (e.g., spam traps, login form abuse) 
- `details.free_provider`: boolean 
- `details.disposable`: boolean 
- `details.deliverable`: boolean 
- `details.accept_all`: boolean — catch‑all mailbox behaviour caveat noted by vendor 
- `details.valid_mx`: boolean — has MX record 
- `details.spoofable`: boolean — spoofable (e.g., SPF not strict or DMARC not enforced) 
- `details.spf_strict`: boolean 
- `details.dmarc_enforced`: boolean 
- `details.profiles`: array of strings (online profile site identifiers) 

**Always present vs optional vs conditional**

- The vendor examples consistently show the top-level keys `email`, `reputation`, `suspicious`, `references`, and `details`. 
- `details.first_seen` appears in vendor-maintained repo docs and the service homepage example, but is not present in the older blog example response, so treat `details.first_seen` as **possibly optional/conditional** (or the blog example may be truncated). 
- `summary` is conditional on `?summary=true` (vendor-documented behaviour), but the exact returned field name is **inferred** as `summary` based on third-party clients. 
- No vendor documentation excerpt available here indicates “premium-only fields” in the response; the pricing page labels both Community and Commercial as “Full API response”, so treat response shape as plan-invariant and quotas as plan-dependent. 

**Response variants**

- **Successful hit (general)**: returns JSON with populated booleans and a non-zero `references`, plus `profiles` array possibly non-empty. 
- **Successful no-hit / low-evidence case**: can still return `suspicious: true`, `reputation: none`, `references: 0`, and many `details.*` booleans false, with `last_seen: "never"` (and a likely empty `profiles` array). 
- **Partial/limited**: not clearly described in vendor primary material available here; treat as **unclear**. 
- **Common error cases**: Vendor primary docs excerpts accessible here do not publish an error schema. Third-party clients commonly handle HTTP `400` (invalid email), `401` (invalid API key for authenticated requests), and `429` (rate limiting). Treat these as **inferred** and confirm against current vendor docs during implementation. 

**Example response excerpt (vendor)**
The provider homepage includes a representative response showing the keys required for Zima mapping (`reputation`, `suspicious`, `references`, and `details.*` including leak/breach and deliverability signals). 

---

### HTTP API: report a malicious email address

**Endpoint / method**
`POST https://emailrep.io/report` 

**Purpose**
Allows reporting an email address as malicious, with tags and optional context; vendor notes this is intended for verified individuals/organisations and can optionally expire a report if believed to be account compromise. 

**Supported entity_type(s)**
`email` (reported email address). 

**Auth / execution requirements**
Vendor example uses an API key header (shown as `key: [api_key]`). 
Key plans/quotas are published on the API key page. 

**Request body fields (what is knowable from accessible sources)**
Vendor blog shows JSON body keys: 

- `email`: string
- `tags`: array of strings
- `description`: string (optional in example usage; described as additional context)
- `timestamp`: number (epoch-like integer in example)

Third-party operator docs additionally describe:

- `expires`: number of hours the email should be considered risky (affecting `suspicious=true`/`blacklisted=true` in query response), with special default behaviour when `account_takeover` tag is used. Treat this as **inferred** until vendor-confirmed. 

**Enums / tag values**
Vendor blog lists “available tags” (2019 snapshot), but tag set may have evolved; confirm against current vendor docs if you implement `POST /report`. 

**Response variants**
Not documented in vendor materials available here; third-party tooling shows a `{status: "success"}`-style response, but treat response schema as **inferred/unclear** for production until verified. 

**Relevance to the two target Zima modules**
For `username_exposure` and `account_enumeration_risk`, `POST /report` is out-of-scope (it is an upstream feedback/curation action, not a “consume provider data and emit signals” input for these modules). 

---

### Provider-level operational artefacts (non-endpoint)

**API key plans / quotas**
Community and Commercial plans are described with explicit monthly quotas (and a daily cap for Community). 

**Provider operation / ownership**
The EmailRep site indicates it is operated by Sublime Security, Inc. 

**Privacy / data handling pointers**
Sublime publishes a privacy policy governing its websites/services, including how it processes personal data and that its services are intended for business customers. 
Sublime’s Terms of Service include restrictions such as not interfering with service availability and not sharing access keys beyond authorised users. 

## Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|username_exposure|signal_producer|get_reputation(email)|GET `https://emailrep.io/{email}`|direct_signal_input|email|Only query if input passes basic email validation; only emit module signals when `details.credentials_leaked == true` OR (fallback) `details.data_breach == true` (see Signal Contract Table).||Provider explicitly tracks `credentials_leaked`, `credentials_leaked_recent`, and `data_breach`. Treat these as the only “exposure” primitives; do **not** escalate based on `reputation` alone.|
|account_enumeration_risk|signal_producer|get_reputation(email)|GET `https://emailrep.io/{email}`|direct_signal_input|email|Only emit risk signal when EmailRep indicates real/public presence via `references > 0` OR `len(details.profiles) > 0` OR `details.data_breach == true` OR `details.credentials_leaked == true`; otherwise treat response as enrichment/no-op.||`references` may include domain-related sources not directly tied to the email, so use it as a weak-but-useful “public presence” indicator, not proof of compromise.|

## Signal Contract Table

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|username_exposure|username_exposure|emailrep|get_reputation(email)|credential_breach_found|identity_security|high|yes|If `details.credentials_leaked_recent == true` then keep **high** (recent leak); else downgrade to **medium** (historical/unknown recency).|email|true_finding|`details.credentials_leaked == true`|`email`, `reputation`, `suspicious`, `references`, `details.credentials_leaked`, `details.credentials_leaked_recent`, `details.data_breach`, `details.first_seen`, `details.last_seen`|`details.profiles`, `details.domain_exists`, `details.domain_reputation`, `details.free_provider`, `details.disposable`, `details.deliverable`, `details.valid_mx`, `details.accept_all`|`Credentials for {entity} were found in credential leaks (EmailRep).`|documented (trigger fields) / derived (severity mapping)||EmailRep specifies `credentials_leaked` and separately `credentials_leaked_recent` (last 90 days).  `first_seen/last_seen` are date-like strings or `'never'`; treat as string evidence unless robustly parsed.|
|username_exposure|username_exposure|emailrep|get_reputation(email)|data_breach_found|identity_security|medium|no|N/A|email|true_finding|`details.data_breach == true AND details.credentials_leaked == false`|`email`, `reputation`, `suspicious`, `references`, `details.data_breach`, `details.first_seen`, `details.last_seen`|`details.profiles`, `details.domain_reputation`, `details.domain_exists`, `details.free_provider`, `details.disposable`|`{entity} appears in historical data breach sources (EmailRep).`|documented (trigger fields) / derived (dedupe gating)||This row exists to avoid double-emitting when `credentials_leaked` is already true (EmailRep notes credential leaks may include breaches).|
|account_enumeration_risk|account_enumeration_risk|emailrep|get_reputation(email)|account_enumeration_risk_elevated|account_security|low|yes|If `len(details.profiles) > 0 OR details.data_breach == true OR details.credentials_leaked == true` then **medium** (stronger evidence of public exposure); else keep **low** (references-only).|email|contextual_enrichment|`(references > 0) OR (len(details.profiles) > 0) OR (details.data_breach == true) OR (details.credentials_leaked == true)`|`email`, `reputation`, `suspicious`, `references`, `details.profiles`, `details.data_breach`, `details.credentials_leaked`|`details.deliverable`, `details.domain_exists`, `details.domain_reputation`, `details.new_domain`, `details.days_since_domain_creation`, `details.free_provider`, `details.disposable`|`{entity} shows public presence signals that can increase account enumeration and targeting risk (EmailRep).`|documented (trigger fields) / derived (severity mapping)||Vendor warns `references` may include domain/related information not directly referencing the email; treat this as risk context, not proof of compromise.|

## Severity Rules and Confidence Guidance

### Severity rules aligned to Zima’s calibration guide

**`credential_breach_found` (username_exposure)**
EmailRep explicitly models `details.credentials_leaked` and recency via `details.credentials_leaked_recent` (last 90 days). 
Mapping to Zima severity: treat this as a **confirmed breach/leak indicator** (high) when recent; otherwise treat as **historical exposure** (medium) because EmailRep does not provide the breach name, data classes, or proof of plaintext passwords in the response fields shown. 
This matches your first-pass caution (“do not treat a low reputation score as equivalent to confirmed compromise”) because the trigger does not rely on `reputation` at all. 

**`data_breach_found` (username_exposure)**
EmailRep provides a distinct `details.data_breach` boolean described as “email was in a data breach at some point in time.” 
Without a “recent” flag for breaches specifically (and with `first_seen/last_seen` mixing multiple observation types), treat this as **medium** by default, reflecting “historical data with low recency confidence” when you cannot prove current credential risk. 

**`account_enumeration_risk_elevated` (account_enumeration_risk)**
This signal deliberately represents **risk context**, not a compromise claim; it is driven by public presence indicators like `references` and `details.profiles`. 
Use **low** severity when only `references > 0` is present because EmailRep notes references may include non-email direct sources. 
Escalate to **medium** in the module only when stronger exposure proofs exist (`profiles` non-empty or breach/leak flags true), because these increase the plausibility of targeted phishing / credential stuffing pressure without asserting active compromise. 

### Confidence guidance table

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|username_exposure|credential_breach_found|EmailRep states it uses many OSINT and leak sources and directly exposes boolean leak/breach flags; treat the _flag_ as a strong indicator but note lack of source-breaking attribution in the response fields shown.|Use `details.credentials_leaked_recent` (90-day window) as the only explicit freshness control in the schema; `first_seen/last_seen` are mixed-observation timestamps.|Corroborate with a second breach provider (e.g., a breach corpus with breach names) before driving automated remediation beyond user notification; if `credentials_leaked_recent == true`, prioritise password rotation/MFA.|Collect production stats: false positive rate of `credentials_leaked` vs known breach-ground-truth; decide whether historical leaks remain high or should auto-downgrade after a time window.|
|username_exposure|data_breach_found|The vendor exposes `details.data_breach` but does not include breach metadata in the documented response shape; treat as “presence in breach sources” rather than a complete breach record.|No explicit “breach_recent” flag; `first_seen/last_seen` combine breach/leak/malicious/spam observation.|If you have separate breach-name providers, only use EmailRep as a starter signal and enrich with named breach(s) from elsewhere for remediation guidance.|Decide whether this signal should be merged into `credential_breach_found` in later schema revisions; measure duplication value vs noise.|
|account_enumeration_risk|account_enumeration_risk_elevated|`references` is explicitly described by EmailRep as including domain/related reputation sources; treat it as weaker evidence than explicit breach/leak booleans or non-empty `profiles`.|Profile presence and reference counts have no stated recency semantics; risk can be fairly time-stable.|Corroborate with internal telemetry (login attempts, password reset spikes) before escalating response; treat this signal primarily as “risk scoring input” for correlation.|Calibrate thresholds: explore whether `references` should have a minimum (e.g., > N) in production to avoid noisy low-count domain-derived references.|

## Provider Summary and Implementation Notes

### Strongest signal types for Zima’s current scope

The most implementation-worthy EmailRep outputs for your two target modules are the explicit exposure booleans: `details.credentials_leaked`, `details.credentials_leaked_recent`, and `details.data_breach`, because they are direct “finding primitives” rather than reputational synthesis. 
A secondary-but-useful risk-context signal is public presence via `references` and `details.profiles`, which can support account enumeration risk scoring when handled conservatively. 

### What EmailRep should not be used for in these modules

Do not treat `reputation` (high/medium/low/none) or `suspicious` alone as evidence of credential compromise or confirmed breach: these fields are described as reputational synthesis across many factors, and the vendor itself cautions that a high reputation sender is not inherently safe and that deeper analysis is required. 
Do not emit standalone “domain security” signals from `spf_strict`, `dmarc_enforced`, or `spoofable` inside the two target modules; those fields are better modelled in a dedicated domain/email-auth module (your current targets are `username_exposure` and `account_enumeration_risk`). 
Do not use `POST /report` as an input to generate Zima findings for these modules; it is an outbound feedback action. 

### API, rate-limit, licensing, and privacy cautions

EmailRep plan quotas can be very small on the Community tier (10/day cap), so the integration should include aggressive caching and deduplication and avoid re-querying unchanged emails during batch runs. 
The `/report` endpoint vendor example uses an API key header, and third-party usage suggests the header name is case-insensitive; for safety standardise on a single header key in your client and confirm against current vendor docs in implementation. 
Sublime’s Terms include restrictions relevant to platform integrations (e.g., do not interfere with availability; do not share keys across unauthorised users). 
Because the queried entity is an email address, you should treat EmailRep queries as transmitting personal data to a third party and ensure your privacy/legal posture matches your deployment context; Sublime publishes a privacy policy describing its personal data practices and the business-customer orientation of its services. 

### Mapper and rules implementation notes for `modules/*/mapper.py` and `modules/*/rules.py`

`details.last_seen` (and `details.first_seen`) should be stored as raw strings in `evidence` unless you implement a parser that handles both date-like strings and the literal `'never'`. 
Because `references` can be domain-derived, implement `account_enumeration_risk_elevated` as a low/medium “contextual_enrichment” signal, and avoid representing it as a breach/compromise finding. 
Deduplication keys that work well at module level (without vendor-specific variants) are: `(signal_type, entity_type=email, entity_value=email)` plus a stable discriminator for exposure signals (e.g., store `details.credentials_leaked_recent` and `details.last_seen` in `evidence` so you can detect meaningful changes). 
Null/no-hit handling: EmailRep can return a valid response where `references = 0`, `reputation = "none"`, `profiles = []`, and `last_seen = "never"`; treat these as “no signal emitted” outcomes and only store as enrichment if your correlation layer needs it. 
Provider/client vs module split: keep HTTP and auth/rate-limit/backoff logic in the provider client; keep “emit vs no-op” decisions and severity conditional rules in the module `rules.py`; keep field-path preservation (raw `details.*`) in the module mapper so evidence remains auditable. 

### Overall classification for current Zima stage

For the two specified modules, EmailRep should be treated as a **signal-producing provider** with a narrow set of direct findings (credential leak / breach presence), plus conservative risk context (public presence) for enumeration risk scoring.

{
  "provider": "emailrep",
  "provider_category": "reputation",
  "provider_role": "signal_producer",
  "module_mappings": [
    {
      "module": "username_exposure",
      "provider_method": "get_reputation(email)",
      "endpoint_or_artifact": "GET https://emailrep.io/{email}",
      "classification": "direct_signal_input",
      "entity_types": ["email"],
      "gating_logic": "Validate email format. Emit signals only when details.credentials_leaked == true OR (details.data_breach == true AND details.credentials_leaked == false).",
      "source_module_name_for_emitted_signals": "username_exposure",
      "notes": "Use explicit leak/breach booleans; do not infer compromise from reputation/suspicious alone. Cache aggressively due to quota limits.",
      "citation_refs": ["turn7view0", "turn3view1", "turn3view0"]
    },
    {
      "module": "account_enumeration_risk",
      "provider_method": "get_reputation(email)",
      "endpoint_or_artifact": "GET https://emailrep.io/{email}",
      "classification": "direct_signal_input",
      "entity_types": ["email"],
      "gating_logic": "Emit a contextual risk signal only when references > 0 OR len(details.profiles) > 0 OR details.data_breach == true OR details.credentials_leaked == true.",
      "source_module_name_for_emitted_signals": "account_enumeration_risk",
      "notes": "references may include domain/related sources; treat primarily as enrichment/risk context.",
      "citation_refs": ["turn7view0", "turn3view1"]
    }
  ],
  "signal_contracts": [
    {
      "module": "username_exposure",
      "source": "username_exposure",
      "provider": "emailrep",
      "provider_method": "get_reputation(email)",
      "signal_type": "credential_breach_found",
      "category": "identity_security",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "details.credentials_leaked == true",
      "severity": "high",
      "severity_is_conditional": "yes",
      "conditional_rule": "If details.credentials_leaked_recent == true => high; else => medium.",
      "evidence_fields": [
        "email",
        "reputation",
        "suspicious",
        "references",
        "details.credentials_leaked",
        "details.credentials_leaked_recent",
        "details.data_breach",
        "details.first_seen",
        "details.last_seen"
      ],
      "enrichment_fields": [
        "details.profiles",
        "details.domain_exists",
        "details.domain_reputation",
        "details.free_provider",
        "details.disposable",
        "details.deliverable",
        "details.valid_mx",
        "details.accept_all"
      ],
      "summary_template": "Credentials for {entity} were found in credential leaks (EmailRep).",
      "tags": ["breach", "credential_stuffing", "dark_web"],
      "evidence_status": "documented",
      "notes": "EmailRep does not provide breach names or password material in the documented response fields; treat as leak indicator only.",
      "citation_refs": ["turn7view0", "turn3view1"]
    },
    {
      "module": "username_exposure",
      "source": "username_exposure",
      "provider": "emailrep",
      "provider_method": "get_reputation(email)",
      "signal_type": "data_breach_found",
      "category": "identity_security",
      "entity_type": "email",
      "finding_kind": "true_finding",
      "trigger_condition": "details.data_breach == true AND details.credentials_leaked == false",
      "severity": "medium",
      "severity_is_conditional": "no",
      "conditional_rule": "unknown",
      "evidence_fields": [
        "email",
        "reputation",
        "suspicious",
        "references",
        "details.data_breach",
        "details.first_seen",
        "details.last_seen"
      ],
      "enrichment_fields": [
        "details.profiles",
        "details.domain_reputation",
        "details.domain_exists",
        "details.free_provider",
        "details.disposable"
      ],
      "summary_template": "{entity} appears in historical data breach sources (EmailRep).",
      "tags": ["breach", "pii_exposure"],
      "evidence_status": "documented",
      "notes": "Designed to avoid double-emitting when credentials_leaked is true (which may include breach-derived leaks).",
      "citation_refs": ["turn7view0", "turn3view1"]
    },
    {
      "module": "account_enumeration_risk",
      "source": "account_enumeration_risk",
      "provider": "emailrep",
      "provider_method": "get_reputation(email)",
      "signal_type": "account_enumeration_risk_elevated",
      "category": "account_security",
      "entity_type": "email",
      "finding_kind": "contextual_enrichment",
      "trigger_condition": "(references > 0) OR (len(details.profiles) > 0) OR (details.data_breach == true) OR (details.credentials_leaked == true)",
      "severity": "low",
      "severity_is_conditional": "yes",
      "conditional_rule": "If len(details.profiles) > 0 OR details.data_breach == true OR details.credentials_leaked == true => medium; else low.",
      "evidence_fields": [
        "email",
        "reputation",
        "suspicious",
        "references",
        "details.profiles",
        "details.data_breach",
        "details.credentials_leaked"
      ],
      "enrichment_fields": [
        "details.deliverable",
        "details.domain_exists",
        "details.domain_reputation",
        "details.new_domain",
        "details.days_since_domain_creation",
        "details.free_provider",
        "details.disposable"
      ],
      "summary_template": "{entity} shows public presence signals that can increase account enumeration and targeting risk (EmailRep).",
      "tags": ["phishing", "credential_stuffing"],
      "evidence_status": "documented",
      "notes": "references may include domain-level sources; treat as contextual only and calibrate thresholds in production.",
      "citation_refs": ["turn7view0", "turn3view1"]
    }
  ],
  "confidence_guidance": [
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "credential_breach_found",
      "source_reliability": "Direct boolean leak indicators from EmailRep; lacks source attribution in documented fields.",
      "freshness_considerations": "Use details.credentials_leaked_recent as explicit 90-day recency; first_seen/last_seen mix multiple observation types.",
      "corroboration_rules": "Corroborate with at least one breach-name provider before automating remediation beyond user notification.",
      "calibration_todo": "Measure false positives and decide downgrade window for historical leaks."
    },
    {
      "module": "username_exposure",
      "signal_type_or_use_case": "data_breach_found",
      "source_reliability": "Direct boolean data_breach indicator; breach metadata not provided in documented response fields.",
      "freshness_considerations": "No breach-specific recency flag; timestamps may not isolate breach event timing.",
      "corroboration_rules": "Enrich via providers that return breach name/date/data classes for remediation.",
      "calibration_todo": "Consider merging into one exposure signal if duplication outweighs value."
    },
    {
      "module": "account_enumeration_risk",
      "signal_type_or_use_case": "account_enumeration_risk_elevated",
      "source_reliability": "references and profiles are useful but references may be domain-derived per vendor; treat as weak signal unless supported by profiles/breach flags.",
      "freshness_considerations": "No explicit recency semantics for references/profiles; handle as time-stable context.",
      "corroboration_rules": "Use correlation with internal auth telemetry before escalating response workflows.",
      "calibration_todo": "Tune references threshold in production and validate utility vs noise."
    }
  ]
}
