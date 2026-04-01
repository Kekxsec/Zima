---
title: "output / breach / leakix"
aliases: ["leakix output", "leakix signal registry"]
tags: [zima, research, outputs, signal-registry, breach, leakix, graph_exclude]
type: provider_research_output
provider: leakix
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: leakix.md
obsidianUIMode: preview
---
LeakIX can act as a signal producer for your `credential_exposure` module based on leak-scope events that explicitly expose credentials or secrets, and as enrichment-only for `stealer_log_exposure`; all other outputs are best treated as network/misconfiguration context rather than standalone signals in your current module set.

---

## API Surface Appendix

### Scopes and data model

- LeakIX exposes two logical scopes:

    - `service`: index of all scanned services in roughly the last year, with banners, protocol info, and software fingerprints.[docs.leakix](https://docs.leakix.net/docs/getting-started/)

    - `leak`: misconfigurations and vulnerabilities discovered during service scans, including open status pages, public configs, and misconfigured ACLs; access to “critical leaks” is reserved for trusted/commercial users.[docs.leakix](https://docs.leakix.net/docs/getting-started/)

- All APIs that return events use **l9format** (`l9event` objects) as the base schema, with fields like `event_type`, `event_source`, `event_fingerprint`, network coordinates, protocol-specific blocks, `service.credentials`, and `leak.dataset`


### l9event core fields (documented)

From `l9format` docs and the `/search` example:

- Top-level:

    - `event_type` (string): `"service"` or `"leak"`.

    - `event_source` (string): plugin name (e.g. `DotEnvConfigPlugin`, `DotDsStoreOpenPlugin`).

    - `event_pipeline` (array[string]): pipeline steps used to obtain the event.

    - `event_fingerprint` (string): stable identifier; good natural dedup key.

    - `ip` (string), `host` (string), `reverse` (string), `port` (string), `mac` (string), `vendor` (string).

    - `transport` (array[string]): e.g. `["tcp","tls","http"]`.

    - `protocol` (string): e.g. `"https"`.

    - `summary` (string): banner/summary, often human-readable description of the leak.

    - `time` (string, RFC3339): indexing time.

    - `tags` (array[string] or null).

    - `geoip.*`, `network.*` blocks with location and ASN metadata.

- `http` object (when HTTP/S): `root`, `url`, `status`, `length`, `header` (map), `title`, `favicon_hash`

- `ssl` object: `detected`, `enabled`, `jarm`, `cypher_suite`, `version`, `certificate.{cn,domain,fingerprint,key_algo,key_size,issuer_name,not_before,not_after,valid}`

- `ssh` object: `fingerprint`, `version`, `banner`, `motd`

- `service` object (documented in `l9format` + fields docs):

    - `service.credentials`:

        - `noauth` (bool): service credentials not present.

        - `username` (keyword), `password` (keyword), `key` (keyword), `raw` (keyword): other captured credential material (e.g. base64-encoded key in `.env`).

    - `service.software`:

        - `name`, `version`, `os`, `modules[] { name, version }`, `fingerprint`.

- `leak` object (leak scope only; also separately documented as “leak specific fields”):

    - `stage` (keyword): example `open` (other values not documented).

    - `type` (keyword): e.g. `"configuration"` in schema example.

    - `severity` (keyword): examples `low`, `medium`, `high`, `critical`

    - `dataset`:

        - `rows` (int), `files` (int), `size` (int, bytes), `collections`/`databases` (int; naming differs between docs), `infected` (bool), `ransom_notes` (text or array of text)

    - Additional leak-level fields in fields doc:

        - `creation_date`, `update_date` (date), `age` (integer days the leak has been open).[docs.leakix](https://docs.leakix.net/docs/query/fields/)


> Note: older examples under `/api-documentation` show `dataset` directly at the event root rather than under `leak.dataset`, and service credentials/metadata without the `service.` prefix. This appears to be an evolution of the schema; your mapper should be tolerant to both shapes (documented vs legacy) and treat the mapping as **derived from examples only**.[leakix](https://leakix.net/api-documentation)

---

### Endpoint: GET `/search`

**Purpose**
Full-text/YQL search over the index, returning lists of `l9event` objects in either `service` or `leak`

**Path & method**

- `GET https://leakix.net/search`[docs.leakix](https://docs.leakix.net/docs/api/search/)


**Supported entity types**

- `ip` (via `ip:` field).

- `domain/host` (via `host:` and other DNS fields)


**Auth / execution requirements**

- Headers:

    - `Accept: application/json` (required).[docs.leakix](https://docs.leakix.net/docs/api/search/)

    - `api-key: <key>` (required for full index access; free researcher keys available)

- Query parameters (documented):[docs.leakix](https://docs.leakix.net/docs/api/search/)

    - `scope` (string, required): `"service"` or `"leak"`.

    - `q` (string, required): URL-encoded search query in LeakIX YQL syntax.

    - `page` (int, optional): page index, default `0`.


**Top-level response**

- On success: `200` with a JSON array of `l9event` objects (`[]` in example; shape described above)

- Example leak result (truncated):[docs.leakix](https://docs.leakix.net/docs/api/search/)

    - `event_type: "leak"`, `event_source: "DotDsStoreOpenPlugin"`, `event_pipeline: [...]`, `event_fingerprint: <sha256-like>`.

    - `ip`, `host`, `port`, `transport`, `protocol`.

    - `http` block.

    - `summary`: description of files discovered via `.DS_Store`.

    - `time`.

    - `ssl`, `ssh`, `service.credentials`, `service.software`.

    - `leak.stage`, `leak.severity`, `leak.dataset.{rows,files,size,collections,infected,ransom_notes}`.

    - `tags`, `geoip.*`, `network.*`.


**Field presence**

- `event_type`, `event_source`, `event_fingerprint`, `ip`, `port`, `time` appear in all examples (likely stable, but not explicitly guaranteed)

- Blocks such as `http`, `ssl`, `ssh`, `service`, `leak`, `tags`, `geoip`, `network` may be `null` or omitted depending on protocol/scope; this is **derived from examples only**


**No-hit / partial results / errors**

- Successful no-hit: not explicitly documented; typical behavior is `200` with an empty array — treat this as **inferred from standard REST patterns and examples**.

- Pagination: `page` parameter supports offset-like paging; docs do not state max pages per query; Rapid7’s module notes pagination and page caps but that is third-party.

- Rate limiting: all API calls, including `/search`, are limited to ~1 request per second; exceeding limit returns `429` with `x-limited-for` header indicating backoff duration.[docs.leakix](https://docs.leakix.net/docs/api/search/)


---

### Endpoint: GET `/host/{ip}`

**Purpose**
Return all known services and leaks for a single host IP.[leakix](https://leakix.net/api-documentation)

**Path & method**

- `GET https://leakix.net/host/{ipv4}`[leakix](https://leakix.net/api-documentation)


**Supported entity type**

- `ip`.


**Auth / execution**

- Headers:

    - `Accept: application/json`.[leakix](https://leakix.net/api-documentation)

    - `api-key: <key>` recommended/required for full index (docs show example with API key).[leakix](https://leakix.net/api-documentation)

- No query parameters documented.


**Response**

- 200 OK with object:

    - `{"Services":[...services...], "Leaks":[...leaks...]}`.[leakix](https://leakix.net/api-documentation)

- `Services` and `Leaks` are arrays of service-scope and leak-scope events, respectively (shape equivalent to `l9event`), though older examples show slightly different nesting names as noted above.

- Example service elements show fields: `ip`, `port`, `type`, `time`, `date`, `data` (banner), `headers`, `plugin`, `network`, `geoip`, `credentials`, `software`, `reverse`, `hostname`, `dataset`, `certificate`, `scheme`.[leakix](https://leakix.net/api-documentation)


**Presence / variants**

- Docs state “will reply two lists, `Services` and `Leaks`”; domain endpoint explicitly allows them to be `null`, so it is reasonable to assume host can also return `null` or empty arrays when nothing is known; this is **derived from examples and domain docs**

- No explicit special “no-hit” schema beyond `Services`/`Leaks` being `null`/empty.

- Errors such as invalid IP or unauthorized are not documented; treat as **unclear**.


---

### Endpoint: GET `/domain/{domain}`

**Purpose**
Return information about a specific domain and its subdomains, with both service and leak events.[docs.leakix](https://docs.leakix.net/docs/api/domain/)

**Path & method**

- `GET https://leakix.net/domain/{domain}`[docs.leakix](https://docs.leakix.net/docs/api/domain/)


**Supported entity type**

- `domain` (plus any subdomains included in `Services`/`Leaks`).


**Auth / execution**

- Headers:

    - `Accept: application/json`.

    - `api-key: <key>`.[docs.leakix](https://docs.leakix.net/docs/api/domain/)


**Response**

- 200 OK with an object containing:

    - `Services`: array of `l9event` service-scope events or `null`.[docs.leakix](https://docs.leakix.net/docs/api/domain/)

    - `Leaks`: array of `l9event` leak-scope events or `null`.[docs.leakix](https://docs.leakix.net/docs/api/domain/)

- Example service shows full l9event-like structure (including `event_type: "service"`, `event_source`, pipeline, network fields, HTTP, SSL, summary, etc.).[docs.leakix](https://docs.leakix.net/docs/api/domain/)


**Variants / errors**

- Services or Leaks explicitly allowed to be `null` when no information is found.[docs.leakix](https://docs.leakix.net/docs/api/domain/)

- Other error codes and bodies not documented (treat as **unclear**).


---

### Endpoint: GET `/api/subdomains/:domain`

**Purpose**

Passive subdomain enumeration for a given domain, with basic metadata.

**Path & method**

- `GET https://leakix.net/api/subdomains/{domain}`


**Supported entity type**

- `domain` (returns subdomains as distinct hostnames).


**Auth / execution**

- Headers:

    - `Accept: application/json`.

    - `api-key: <key>`; “Registered and pro users are getting more results”, so free/unauthenticated use is restricted.[docs.leakix](https://docs.leakix.net/docs/api/subdomains/)

- No query parameters documented.


**Response**

- 200 OK with JSON array of objects:[docs.leakix](https://docs.leakix.net/docs/api/subdomains/)

    - `subdomain` (string): FQDN.

    - `distinct_ips` (int): number of unique IPs observed.

    - `last_seen` (string, RFC3339 timestamp).

- Example shows multiple subdomains objects in an array.[docs.leakix](https://docs.leakix.net/docs/api/subdomains/)


**Variants / errors**

- If there are no subdomains, likely 200 with empty array; this is **inferred from example structure** (not explicit).

- Rate limiting: same 1 rps/`429`/`x-limited-for` behavior documented at endpoint level.[docs.leakix](https://docs.leakix.net/docs/api/subdomains/)

- Other errors such as invalid domain not documented.


---

### Endpoint: GET `/bulk/search`

**Purpose**

High-volume export of search results as JSONL, avoiding pagination; pro users only.[docs.leakix](https://docs.leakix.net/docs/api/bulk/)

**Path & method**

- `GET https://leakix.net/bulk/search`[docs.leakix](https://docs.leakix.net/docs/api/bulk/)


**Supported entity types**

- Same as `/search` but the endpoint is oriented around query-wide exports rather than per-entity queries.


**Auth / execution**

- Headers:

    - `api-key: <key>` (required; bulk is “pro users only”).[docs.leakix](https://docs.leakix.net/docs/api/bulk/)

- Query parameters:

    - `q`: URL-encoded YQL query string (same syntax as `/search`)

- No `scope` parameter documented; Rapid7 module suggests bulk is “leak scope only” but that is third-party; treat scope behavior as **unclear**, and assume you must encode any scope limitation directly in `q` (e.g. `event_type:leak`)


**Response**

- Successful: 200 OK and body is a JSONL file containing `l9event` records, typically downloaded via `wget` example.[docs.leakix](https://docs.leakix.net/docs/api/bulk/)

- Intended for offline processing; not entity-scoped.


**Rate limiting / errors**

- Same 1 rps global limit, `429`/`x-limited-for` semantics.[docs.leakix](https://docs.leakix.net/docs/api/bulk/)

- Other error payloads not documented.


---

### (Inferred) Endpoint: GET `/api/plugins`

**Purpose (third-party)**

- Rapid7 Metasploit module and Sploitus notes mention an `/api/plugins` endpoint to list current LeakIX scanner plugins.

- Not documented in official LeakIX docs; treat as **inferred from third-party only** and **utility-only** (no direct signals).


**Shape / fields**

- No official schema; third-party tooling expects an array of plugin metadata used for filtering.

- For signal design, rely instead on the public l9plugins repository, which describes plugin names, protocols, and descriptions in a table.[github](https://github.com/LeakIX/l9plugins)


---

### Global: Query language and fields

- LeakIX query syntax is YQL-based with documented field types and global fields (e.g. `plugin`, `ip`, `host`, `http.url`, `summary`, `geoip.*`, `network.*`).[docs.leakix](https://docs.leakix.net/docs/query/fields/)

- “Leak specific fields” include `leak.severity`, `leak.dataset.*`, and `service.credentials.*` used in leak scope.[docs.leakix](https://docs.leakix.net/docs/query/fields/)


These documented field names are what your rules and mapper should bind to; any older variants (e.g. root-level `dataset`) should be treated as compatibility shims, not first-class schema.

---

## Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|credential_exposure|signal_producer|`search_leaks_by_domain_or_ip`|`GET /search?scope=leak`|direct_signal_input|domain, ip|Only process `event_type == "leak"` events for monitored domains/IPs; then apply additional field-level rules (credentials/secrets, datasets) before emitting signals.|[https://docs.leakix.net/docs/api/search/](https://docs.leakix.net/docs/api/search/) ; [https://docs.leakix.net/docs/api/l9format/](https://docs.leakix.net/docs/api/l9format/) ; [https://docs.leakix.net/docs/query/fields/](https://docs.leakix.net/docs/query/fields/)|Primary source of credential/secret and data-exposure findings; must respect rate limiting (~1 rps) and leak visibility tiers.|
|credential_exposure|signal_producer|`lookup_host_by_ip`|`GET /host/{ip}`|direct_signal_input|ip, domain (via host)|Use as IP-centric variant when your workflow keys off IP; treat `Leaks` array as same as leak-scope `l9event`s and feed into same rules as `/search` results.|[https://leakix.net/api-documentation](https://leakix.net/api-documentation) ; [https://docs.leakix.net/docs/api/l9format/](https://docs.leakix.net/docs/api/l9format/)|Host endpoint returns `Services` and `Leaks`; leaks may use slightly older field nesting; mapper must normalize into the documented l9event shape.|
|credential_exposure|signal_producer|`get_domain_details`|`GET /domain/{domain}`|direct_signal_input|domain, subdomain|Use for domain-level aggregation; process `Leaks` array with same rules as leak-scope search; ignore or treat `Services` as enrichment for this module.|[https://docs.leakix.net/docs/api/domain/](https://docs.leakix.net/docs/api/domain/) ; [https://docs.leakix.net/docs/api/l9format/](https://docs.leakix.net/docs/api/l9format/)|`Services`/`Leaks` may be `null`; handle gracefully; helpful when you want all events for a domain, not filtered by IP.|
|credential_exposure|enrichment_only|`search_services_by_domain_or_ip`|`GET /search?scope=service`|enrichment_only|domain, ip|Only attach as context to credential_exposure signals (e.g. same host also has open DB or NTLM service); do not emit standalone credential_exposure signals from pure service-scope events.|[https://docs.leakix.net/docs/api/search/](https://docs.leakix.net/docs/api/search/) ; [https://docs.leakix.net/docs/query/fields/](https://docs.leakix.net/docs/query/fields/)|Service-scope events describe exposed services and misconfigurations (open ports, banners) but, by themselves, usually lack explicit credential material; better suited for a separate misconfiguration/network module.|
|credential_exposure|enrichment_only|`get_subdomains`|`GET /api/subdomains/:domain`|enrichment_only|domain, hostname|Use to expand the set of domains/hosts to query with leak searches; do not treat subdomain presence as a credential exposure signal.|[https://docs.leakix.net/docs/api/subdomains/](https://docs.leakix.net/docs/api/subdomains/)|Registered/pro accounts get more subdomains; results are passive OSINT context only.[docs.leakix](https://docs.leakix.net/docs/api/subdomains/)|
|credential_exposure|utility_only|`bulk_leak_export`|`GET /bulk/search`|utility_only|none (batch export)|Use for offline backfills or bulk analytics, not per-entity real-time lookups; downstream processing should apply the same credential-exposure rules as live `/search`/`/domain`/`/host` streams.|[https://docs.leakix.net/docs/api/bulk/](https://docs.leakix.net/docs/api/bulk/) ; [https://docs.leakix.net/docs/api/l9format/](https://docs.leakix.net/docs/api/l9format/)|Pro-only; returns JSONL; useful if you want to build historical baselines or precompute coverage; still subject to 1 rps limit.|
|credential_exposure|enrichment_only|`list_plugins`|(inferred) `GET /api/plugins`|utility_only|none|Optional: ingest plugin catalog for reporting or tuning rules (e.g. which plugins tend to return secrets vs generic misconfig); do not create signals directly from plugin list.|[https://www.rapid7.com/db/modules/auxiliary/gather/leakix_search/](https://www.rapid7.com/db/modules/auxiliary/gather/leakix_search/) ; [https://sploitus.com/exploit?id=MSF%3AAUXILIARY-GATHER-LEAKIX_SEARCH-](https://sploitus.com/exploit?id=MSF%3AAUXILIARY-GATHER-LEAKIX_SEARCH-) ; [https://github.com/LeakIX/l9plugins](https://github.com/LeakIX/l9plugins)|`/api/plugins` endpoint is not officially documented; rely instead on the l9plugins repo to understand plugin semantics. Treat all of this as third-party/inferred.|
|stealer_log_exposure|enrichment_only|`domain_context_for_stealer_host`|`GET /domain/{domain}`|enrichment_only|domain, subdomain|When you already have a stealer-log-based signal for a domain/host, pull associated LeakIX `Services`/`Leaks` to show concurrent misconfigurations or database exposures; never emit stealer_log_exposure solely from LeakIX.|[https://docs.leakix.net/docs/api/domain/](https://docs.leakix.net/docs/api/domain/) ; [https://docs.leakix.net/docs/api/search/](https://docs.leakix.net/docs/api/search/) ; [https://docs.leakix.net/docs/getting-started/](https://docs.leakix.net/docs/getting-started/)|LeakIX does not index malware stealer panels or logs; it indexes misconfigured or exposed services; for stealer_log_exposure module this is strictly enrichment.|
|stealer_log_exposure|enrichment_only|`host_context_for_stealer_ip`|`GET /host/{ip}`|enrichment_only|ip|Similar to domain context but keyed on IP; never used to generate stealer_log_exposure signals on its own.|[https://leakix.net/api-documentation](https://leakix.net/api-documentation) ; [https://docs.leakix.net/docs/api/l9format/](https://docs.leakix.net/docs/api/l9format/)|Only attach as evidence that a compromised endpoint also has exposed services or leaks; keep module responsibilities separate.|

---

## Signal Contract Table

Only the `credential_exposure` module should emit standalone signals for LeakIX at this stage. `stealer_log_exposure` consumes LeakIX purely as enrichment/context.

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|credential_exposure|credential_exposure|leakix|`search_leaks_by_domain_or_ip` (`GET /search?scope=leak`, plus `/host`, `/domain`)|`secret_config_file_exposed`|secrets|critical|yes|Treat as **critical** when `service.credentials.password`, `service.credentials.key`, or `service.credentials.raw` is non-empty, or when `plugin`/`event_source` corresponds to configuration-file plugins such as `dotenv_http`, `configjson_http`, `gitconfig_http`, `idxconfig_http`, or `firebase_http`; otherwise consider downgrading to **high** pending calibration.|domain|true_finding|`event_type == "leak"` AND ( `service.credentials.password != ""` OR `service.credentials.key != ""` OR `service.credentials.raw != ""` OR `plugin` (or `event_source`) in [`dotenv_http`,`configjson_http`,`gitconfig_http`,`idxconfig_http`,`firebase_http`] ) AND (`host` or `ip` belongs to the monitored asset set).|`event_fingerprint`, `event_type`, `event_source`, `plugin` (global field), `ip`, `host`, `port`, `protocol`, `http.url`, `http.status`, `summary`, all `service.credentials.*`, `leak.stage`, `leak.severity`, all `leak.dataset.*`, `time`, `tags`.|`geoip.*`, `network.*`, `ssl.*`, `http.header`, `http.title`, `service.software.*`, any legacy root-level `dataset` block if present.|`LeakIX detected an exposed configuration or secrets file (plugin {{plugin}}) on {{host}} ({{ip}}:{{port}}) that appears to contain credentials or other sensitive secrets.`|derived|[https://docs.leakix.net/docs/api/l9format/](https://docs.leakix.net/docs/api/l9format/) ; [https://docs.leakix.net/docs/query/fields/](https://docs.leakix.net/docs/query/fields/) ; [https://docs.leakix.net/docs/api/search/](https://docs.leakix.net/docs/api/search/) ; [https://leakix.net/api-documentation](https://leakix.net/api-documentation) ; [https://github.com/LeakIX/l9plugins](https://github.com/LeakIX/l9plugins)|Uses documented credential fields and leak-specific dataset fields; plugin-to-”secret config” mapping is derived from official plugin descriptions (e.g. `.env`, `config.json`, `.git/config`) and should be marked as implementation guidance, not a strict schema guarantee.|
|credential_exposure|credential_exposure|leakix|`search_leaks_by_domain_or_ip` (`GET /search?scope=leak`, plus `/host`, `/domain`)|`database_exposed_without_auth`|data_breach|high|yes|Set **high** when `event_type == "leak"` AND plugin indicates open or explored data stores (e.g. `mysql_explore`, `mongo_explore`, `elasticsearch_explore`, `couchdb_open`, `firebase_http`) AND `leak.dataset.rows > 0`; optionally escalate to **critical** if `leak.dataset.rows` is very large or `leak.dataset.infected`/`ransom_notes` indicates ransomware, after calibration.|domain|true_finding|`event_type == "leak"` AND `plugin` (or `event_source`) in [`mysql_explore`,`mongo_explore`,`elasticsearch_explore`,`couchdb_open`,`firebase_http`] AND `leak.dataset.rows > 0` AND (`service.credentials.noauth == true` OR service still reachable) AND (`host` or `ip` belongs to monitored asset set).|`event_fingerprint`, `event_type`, `event_source`, `plugin`, `ip`, `host`, `port`, `protocol`, `summary`, `leak.stage`, `leak.severity`, all `leak.dataset.*` (esp. `rows`, `size`, `infected`, `ransom_notes`), `service.credentials.noauth`, `time`, `tags`.|`geoip.*`, `network.*`, `ssl.*`, `http.*`, `service.software.*`, any legacy `dataset` block if present.|`LeakIX reports an unauthenticated {{plugin}} data store at {{ip}}:{{port}} for {{host}} exposing approximately {{leak.dataset.rows}} records.`|inferred|[https://docs.leakix.net/docs/api/l9format/](https://docs.leakix.net/docs/api/l9format/) ; [https://docs.leakix.net/docs/query/fields/](https://docs.leakix.net/docs/query/fields/) ; [https://docs.leakix.net/docs/getting-started/](https://docs.leakix.net/docs/getting-started/) ; [https://github.com/LeakIX/l9plugins](https://github.com/LeakIX/l9plugins)|Plugin list and descriptions show open/explore plugins for various databases; combining these with `leak.dataset.rows`>0 is an inferred but reasonable indicator of exposed data, not just an open  Final severity escalation based on dataset size and infection status should be calibrated on real-world data.|

Notes on evidence_status:

- `secret_config_file_exposed`: **derived** — fields and plugin names are documented; the assumption that these plugins usually surface secrets is based on plugin descriptions but may not always hold (e.g. configs with no secrets)

- `database_exposed_without_auth`: **inferred** — it combines documented leak dataset fields with plugin semantics indicating open/explored databases; evidence of actual PII/content still requires verification.


No standalone signals are defined for `stealer_log_exposure` because LeakIX does not index stealer logs or C2 infrastructure; using it there purely as enrichment avoids conflating infrastructure misconfig with malware-log exposure.

---

## Severity Rules

### `secret_config_file_exposed`

- **Base severity**: `critical`.

    - Rationale: events that populate `service.credentials.password`, `service.credentials.key`, or `service.credentials.raw` represent direct credential or secret exposure, often in cleartext configuration files like `.env` or `config.json`, matching your “direct credential exposure / plaintext passwords / exposed secrets” definition for critical.

- **Conditional logic** (as in table):

    - If no explicit credential fields are populated and plugin is generic (e.g. `gitconfig_http` where only remote URLs are visible), you may downgrade to `high` until you implement content-aware parsing.

    - Future calibration may refine severity by incorporating LeakIX’s own `leak.severity` and `leak.dataset` attributes, but those should remain supporting evidence, not authoritative overrides.

- Your initial provider assessment (~0.80 confidence) is compatible with treating such findings as high-impact but still requiring corroboration before auto-remediation.


### `database_exposed_without_auth`

- **Base severity**: `high`.

    - Rationale: an unauthenticated datastore with nonzero `leak.dataset.rows` suggests exposed data and potential PII, meeting your “confirmed breach / exposed PII / verified malicious infra” threshold for high even if specific credential values are not extracted.

- **Escalation**:

    - Consider escalating to `critical` when:

        - `leak.dataset.rows` or `leak.dataset.size` is very large,

        - `leak.dataset.infected == true` or `leak.dataset.ransom_notes` contains ransom notes (indicates active compromise), or

        - you correlate with other providers confirming active exploitation.

    - These escalation rules should be driven by empirical distributions of dataset sizes and infection flags observed across your corpus.


Overall, your first-pass severity expectations align well with using LeakIX primarily for **critical** secrets in config files and **high** for confirmed exposed datastores, with lower severities reserved for pure misconfig/service exposures that would live in other modules.

---

## Confidence Guidance

### Confidence considerations per signal/use case

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|credential_exposure|`secret_config_file_exposed`|LeakIX runs active scans with specialized plugins (`dotenv_http`, `configjson_http`, `gitconfig_http`, etc.), and l9format events encode explicit credentials/keys when parsed; this yields relatively high structural reliability for presence of exposed config files.|Use `time`, `leak.creation_date`, `leak.update_date`, and `age` to downrank stale findings; older leaks may have been remediated even if still indexed; restrict high/critical alerts to recent events (e.g. `age < 30`) by default.|For high-impact actions (password reset, key revocation), re-fetch `http.url` directly and confirm the file still exists and still contains sensitive tokens/passwords; cross-check with internal scanners or other exposer search engines when available.|Measure: (a) fraction of config-leak events that are still reachable when Zima checks, (b) rate at which `service.credentials.*` truly correspond to live secrets vs benign strings; adjust severity and confidence thresholds based on false-positive/false-negative trade-offs.|
|credential_exposure|`database_exposed_without_auth`|Plugins such as `mysql_explore`, `mongo_explore`, `elasticsearch_explore`, `couchdb_open`, and `firebase_http` indicate successful connections and enumeration of databases/indexes, giving high confidence that the service was open at scan time.|`age` and `update_date` are critical: exposed databases are often closed quickly once discovered; treat older-than-N days leaks as medium/low or enrichment only; large `leak.dataset.rows` with very old timestamps should be carefully validated.[docs.leakix](https://docs.leakix.net/docs/query/fields/)|Attempt a safe, read-only connection using the same protocol where legally and ethically permitted; confirm that authentication is still disabled and that data structure resembles what LeakIX reported; never rely solely on historical `leak.dataset.*` for immediate breach conclusions.|Build distributions of `leak.dataset.rows`, `size`, and `age` per plugin; empirically determine thresholds where events are more likely to be stale vs active; calibrate severity tiers and whether to auto-page analysts based on those distributions.|
|stealer_log_exposure|host/domain context enrichment|LeakIX does not provide stealer logs; its value here is contextual (showing that a host seen in malware logs also has misconfig/leaks), which is reasonably reliable given it keys on IP/host from the same data.|Freshness for context is less strict; even older leaks can show that an asset has a history of poor hygiene; still, consider downweighting context where `age` is very high or `stage` is not `open` if additional values appear later.[docs.leakix](https://docs.leakix.net/docs/query/fields/)|Only use LeakIX enrichment after a stealer_log_exposure signal exists from another provider; check that IP/host matches and that events are from the correct timeframe around the malware observation; do not change stealer-log severity solely based on LeakIX context.|Track how often assets with stealer logs also have LeakIX leaks; use this for risk-scoring but avoid using LeakIX alone to infer compromise; experiment with adding a “historical misconfig” factor into your global risk models rather than per-signal severity.|

---

## Tags

Recommended tags for the defined signal types:

- `secret_config_file_exposed`

    - `["breach","exposed_secret","plaintext_password"]` (when `service.credentials.password` is set) or `["breach","exposed_secret"]` otherwise.

- `database_exposed_without_auth`

    - `["breach","pii_exposure"]` (if you later infer PII) or more conservatively `["breach"]` until classification improves.


None of the current LeakIX outputs are appropriate for `stealer_log`, `malware`, or `c2` tags without additional corroborating providers.

---

## Implementation Notes

### Field paths and parsing

- Prefer the documented l9format paths (`service.credentials.*`, `leak.dataset.*`) but add shims to map legacy top-level `dataset` and credential fields seen in older examples from `/api-documentation`

- Always preserve `event_fingerprint` in evidence; this is a natural deduplication key across endpoints (`/search`, `/host`, `/domain`, `/bulk`)

- Preserve `summary` and `http.url` verbatim; they often contain human-readable cues about what was exposed (e.g. file paths, index names) that are useful in investigations.

- `plugin` (global searchable field) and `event_source` should both be retained to drive rule branching by plugin type.


### Null / empty / no-hit handling

- `/domain`: `Services` and `Leaks` can be `null` when no information exists; treat null as equivalent to empty array in your client.[docs.leakix](https://docs.leakix.net/docs/api/domain/)

- `/host`: may behave similarly even though not explicitly stated; handle both null and empty arrays gracefully.

- `/search`: expect `200` with an empty array when no results; do not treat that as an error.[docs.leakix](https://docs.leakix.net/docs/api/search/)

- `/api/subdomains`: expect `[]` when no subdomains; null is not documented, but client should handle either.[docs.leakix](https://docs.leakix.net/docs/api/subdomains/)


### Rate limits, auth, and licensing

- All endpoints: ~1 request/second; when exceeded, the API returns `429` and an `x-limited-for` header (ms); your client **must** sleep for that duration before retrying.

- Subdomains and bulk require API keys and have result/feature differences by plan (registered vs pro vs commercial)

- Sensitive/“critical” leaks are restricted to trusted users/commercial plans; coverage for free keys may systematically miss some of the highest-impact items.[docs.leakix](https://docs.leakix.net/docs/getting-started/)


### Deduplication and correlation

- Use `event_fingerprint` as the primary dedup key across all LeakIX-derived events; also keep `ip`, `host`, `port`, and `plugin` for secondary deduplication.

- If the same fingerprint appears via `/search`, `/host`, and `/domain`, deduplicate at your provider-client layer and feed a single canonical event into your mapper.


### Client vs mapper vs correlation layer

- **Provider client** (LeakIX integration):

    - Handle HTTP details (headers, API key, retries, rate limiting).

    - Normalize l9event shape (handling legacy vs documented nesting).

    - Expose a consistently-typed object model to mappers (e.g. `LeakixEvent`).

- **Module mapper (`modules/credential_exposure/mapper.py`)**:

    - Implement the field-based trigger conditions described above.

    - Map provider fields to Zima’s normalized schema (`signal_type`, `entity_type`, `summary`, `evidence`, `tags`).

    - Do not attempt to parse full HTTP bodies here; keep body inspection, if any, in a lower-level utility or separate enrichment pipeline.

- **Rules/correlation layer (`modules/*/rules.py`)**:

    - Decide final severity within the bounds given here, using global context (age, duplicate sightings, other providers).

    - Correlate multiple LeakIX events (e.g. config + DB) into a single higher-level incident if desired.


---

## Provider Summary

- **Strongest signal types for Zima (current modules):**

    - Direct exposures of configuration files that embed credentials or secrets (`.env`, `config.json`, `.git/config`), detectable via `service.credentials.*` and plugin names like `dotenv_http` and `configjson_http`

    - Exposed datastores discovered by “open”/”explore” plugins with non-zero `leak.dataset.rows`, indicating likely data exposure rather than just an open port.

- **What LeakIX should _not_ be used for (in this stage):**

    - Stealer-log or malware-log exposure detection (no support for stealer panels, logs, or C2 telemetry in docs).[docs.leakix](https://docs.leakix.net/docs/getting-started/)

    - Fine-grained identity events (logins, MFA, account behavior).

    - Deep WHOIS/registry, ASN enrichment beyond what is already present in `geoip.*` and `network.*`.

- **API/auth/rate-limit/licensing cautions:**

    - Strict global rate limit (~1 rps) with explicit backoff hints via `x-limited-for`; failing to respect this risks throttling and bans.

    - Free API keys exist but have reduced visibility into the most sensitive leaks; some features (bulk, richer subdomains, critical leaks) are plan-gated.

    - Schema has evolved; your client must normalize legacy vs current l9format layouts.

- **Overall role in Zima (current stage):**

    - Treat LeakIX as a **signal-producing provider** for the `credential_exposure` module (focused on secrets in configs and exposed datastores), and as **enrichment-only** for `stealer_log_exposure`.

    - Additional modules (e.g. `network_misconfiguration`, `exposed_service`) could later promote more LeakIX findings (service-scope events, open databases with no dataset info) into standalone signals, but these are out-of-scope for your current mapping.


---

## Structured JSON

json

`{   "provider": "leakix",  "provider_category": "breach",  "provider_role": "signal_producer",  "module_mappings": [    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "search_leaks_by_domain_or_ip",      "endpoint_or_artifact": "GET /search?scope=leak",      "classification": "direct_signal_input",      "entity_types": ["domain", "ip"],      "gating_logic": "Only process event_type == \"leak\" for monitored domains/IPs; then apply field-level rules for credentials/secrets and datasets before emitting signals.",      "citation_refs": [        "https://docs.leakix.net/docs/api/search/",        "https://docs.leakix.net/docs/api/l9format/",        "https://docs.leakix.net/docs/query/fields/"      ],      "notes": "Primary source of leak-scope events driving credential_exposure signals; subject to ~1 rps rate limit and leak visibility tiers."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "lookup_host_by_ip",      "endpoint_or_artifact": "GET /host/{ip}",      "classification": "direct_signal_input",      "entity_types": ["ip", "domain"],      "gating_logic": "Use as IP-centric variant; process Leaks array as l9event leak-scope events and feed into the same rules as /search.",      "citation_refs": [        "https://leakix.net/api-documentation",        "https://docs.leakix.net/docs/api/l9format/"      ],      "notes": "Services and Leaks arrays may reflect a slightly older event layout; normalize to documented l9format."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "get_domain_details",      "endpoint_or_artifact": "GET /domain/{domain}",      "classification": "direct_signal_input",      "entity_types": ["domain", "subdomain"],      "gating_logic": "Process Leaks array with the same rules as leak-scope search; ignore or treat Services as enrichment for this module.",      "citation_refs": [        "https://docs.leakix.net/docs/api/domain/",        "https://docs.leakix.net/docs/api/l9format/"      ],      "notes": "Services and Leaks may be null when no info is found."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "search_services_by_domain_or_ip",      "endpoint_or_artifact": "GET /search?scope=service",      "classification": "enrichment_only",      "entity_types": ["domain", "ip"],      "gating_logic": "Only attach as enrichment to existing credential_exposure signals for the same host/IP; do not emit standalone signals from service-scope events.",      "citation_refs": [        "https://docs.leakix.net/docs/api/search/",        "https://docs.leakix.net/docs/query/fields/"      ],      "notes": "Service-scope captures exposed services/banners; actual credential material is usually absent, better suited for a misconfiguration module."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "get_subdomains",      "endpoint_or_artifact": "GET /api/subdomains/:domain",      "classification": "enrichment_only",      "entity_types": ["domain", "hostname"],      "gating_logic": "Use to expand the asset graph (subdomains to query for leaks); never emits standalone credential_exposure signals.",      "citation_refs": [        "https://docs.leakix.net/docs/api/subdomains/"      ],      "notes": "Registered/pro users receive more subdomains; results are passive OSINT context."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "bulk_leak_export",      "endpoint_or_artifact": "GET /bulk/search",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Use for offline bulk export and backfills; downstream processing applies the same credential_exposure rules as live streams.",      "citation_refs": [        "https://docs.leakix.net/docs/api/bulk/",        "https://docs.leakix.net/docs/api/l9format/"      ],      "notes": "Pro-only; returns JSONL; still rate limited to ~1 rps."    },    {      "module": "credential_exposure",      "provider_role": "signal_producer",      "provider_method": "list_plugins",      "endpoint_or_artifact": "GET /api/plugins (inferred)",      "classification": "utility_only",      "entity_types": [],      "gating_logic": "Optional; ingest plugin catalog for reporting/tuning, not for direct signal generation.",      "citation_refs": [        "https://www.rapid7.com/db/modules/auxiliary/gather/leakix_search/",        "https://sploitus.com/exploit?id=MSF%3AAUXILIARY-GATHER-LEAKIX_SEARCH-",        "https://github.com/LeakIX/l9plugins"      ],      "notes": "Endpoint is not officially documented; plugin semantics come from the l9plugins repository."    },    {      "module": "stealer_log_exposure",      "provider_role": "signal_producer",      "provider_method": "domain_context_for_stealer_host",      "endpoint_or_artifact": "GET /domain/{domain}",      "classification": "enrichment_only",      "entity_types": ["domain", "subdomain"],      "gating_logic": "Only query LeakIX after a stealer_log_exposure signal exists for the same domain; attach Services/Leaks as context, not as new signals.",      "citation_refs": [        "https://docs.leakix.net/docs/api/domain/",        "https://docs.leakix.net/docs/getting-started/"      ],      "notes": "LeakIX does not index stealer logs; its role here is contextual infrastructure risk."    },    {      "module": "stealer_log_exposure",      "provider_role": "signal_producer",      "provider_method": "host_context_for_stealer_ip",      "endpoint_or_artifact": "GET /host/{ip}",      "classification": "enrichment_only",      "entity_types": ["ip"],      "gating_logic": "Same as domain context but keyed by IP; never emit stealer_log_exposure signals directly from LeakIX.",      "citation_refs": [        "https://leakix.net/api-documentation",        "https://docs.leakix.net/docs/api/l9format/"      ],      "notes": "Only used to show that compromised IPs also have misconfigurations or leaks."    }  ],  "signal_contracts": [    {      "module": "credential_exposure",      "source": "credential_exposure",      "provider": "leakix",      "provider_method": "search_leaks_by_domain_or_ip (GET /search?scope=leak, plus /host and /domain)",      "signal_type": "secret_config_file_exposed",      "category": "secrets",      "severity": "critical",      "severity_is_conditional": "yes",      "conditional_rule": "Set severity to critical when service.credentials.password, service.credentials.key, or service.credentials.raw is non-empty, or when plugin/event_source is a configuration-file plugin such as dotenv_http, configjson_http, gitconfig_http, idxconfig_http, or firebase_http. Consider downgrading to high when the plugin is generic and no explicit credential field is populated.",      "entity_type": "domain",      "finding_kind": "true_finding",      "trigger_condition": "event_type == \"leak\" AND (service.credentials.password != \"\" OR service.credentials.key != \"\" OR service.credentials.raw != \"\" OR plugin in [\"dotenv_http\",\"configjson_http\",\"gitconfig_http\",\"idxconfig_http\",\"firebase_http\"]) AND (host or ip is in the monitored asset set).",      "evidence_fields": [        "event_fingerprint",        "event_type",        "event_source",        "plugin",        "ip",        "host",        "port",        "protocol",        "http.url",        "http.status",        "summary",        "service.credentials.noauth",        "service.credentials.username",        "service.credentials.password",        "service.credentials.key",        "service.credentials.raw",        "leak.stage",        "leak.severity",        "leak.dataset.rows",        "leak.dataset.files",        "leak.dataset.size",        "leak.dataset.collections",        "leak.dataset.infected",        "leak.dataset.ransom_notes",        "time",        "tags"      ],      "enrichment_fields": [        "geoip.*",        "network.*",        "ssl.*",        "http.header",        "http.title",        "service.software.*",        "legacy dataset (if present at root)"      ],      "summary_template": "LeakIX detected an exposed configuration or secrets file (plugin {{plugin}}) on {{host}} ({{ip}}:{{port}}) that appears to contain credentials or other sensitive secrets.",      "evidence_status": "derived",      "citation_refs": [        "https://docs.leakix.net/docs/api/l9format/",        "https://docs.leakix.net/docs/query/fields/",        "https://docs.leakix.net/docs/api/search/",        "https://leakix.net/api-documentation",        "https://github.com/LeakIX/l9plugins"      ],      "notes": "Uses documented credential and leak fields combined with plugin descriptions for config/scanner plugins; plugin-to-secret mapping is not formally guaranteed and should be validated with content-aware checks over time."    },    {      "module": "credential_exposure",      "source": "credential_exposure",      "provider": "leakix",      "provider_method": "search_leaks_by_domain_or_ip (GET /search?scope=leak, plus /host and /domain)",      "signal_type": "database_exposed_without_auth",      "category": "data_breach",      "severity": "high",      "severity_is_conditional": "yes",      "conditional_rule": "Set severity to high when event_type == \"leak\" AND plugin/event_source is one of the open/explore datastore plugins (e.g. mysql_explore, mongo_explore, elasticsearch_explore, couchdb_open, firebase_http) AND leak.dataset.rows > 0. Escalate to critical when dataset rows or size is very large or when leak.dataset.infected or leak.dataset.ransom_notes indicates ransomware, after empirical calibration.",      "entity_type": "domain",      "finding_kind": "true_finding",      "trigger_condition": "event_type == \"leak\" AND plugin in [\"mysql_explore\",\"mongo_explore\",\"elasticsearch_explore\",\"couchdb_open\",\"firebase_http\"] AND leak.dataset.rows > 0 AND (service.credentials.noauth == true OR the service is reachable) AND (host or ip is in the monitored asset set).",      "evidence_fields": [        "event_fingerprint",        "event_type",        "event_source",        "plugin",        "ip",        "host",        "port",        "protocol",        "summary",        "leak.stage",        "leak.severity",        "leak.dataset.rows",        "leak.dataset.files",        "leak.dataset.size",        "leak.dataset.collections",        "leak.dataset.infected",        "leak.dataset.ransom_notes",        "service.credentials.noauth",        "time",        "tags"      ],      "enrichment_fields": [        "geoip.*",        "network.*",        "ssl.*",        "http.*",        "service.software.*",        "legacy dataset (if present at root)"      ],      "summary_template": "LeakIX reports an unauthenticated {{plugin}} data store at {{ip}}:{{port}} for {{host}} exposing approximately {{leak.dataset.rows}} records.",      "evidence_status": "inferred",      "citation_refs": [        "https://docs.leakix.net/docs/api/l9format/",        "https://docs.leakix.net/docs/query/fields/",        "https://docs.leakix.net/docs/getting-started/",        "https://github.com/LeakIX/l9plugins"      ],      "notes": "Combines documented leak.dataset fields with plugin semantics that indicate successful enumeration of databases/indices; specific data sensitivity (PII vs logs) is not exposed in the schema and must be inferred or corroborated elsewhere."    }  ],  "confidence_guidance": [    {      "module": "credential_exposure",      "signal_type_or_use_case": "secret_config_file_exposed",      "source_reliability": "Events are produced by targeted plugins (dotenv_http, configjson_http, gitconfig_http, etc.), and credentials are stored in explicit fields (service.credentials.*) when parsed; this yields relatively high structural reliability for presence of an exposed config endpoint.",      "freshness_considerations": "Use time, leak.creation_date, leak.update_date, and age fields to downrank stale findings; consider defaulting to strict alerting only for age < 30 days and treating older events as medium/low or enrichment.",      "corroboration_rules": "Before triggering automated remediation, re-fetch http.url and confirm both reachability and presence of actual secrets; optionally cross-check with internal scanners or other internet-wide scanners.",      "calibration_todo": "Measure how often config leaks reported by LeakIX remain reachable when Zima checks, and how often service.credentials.* correspond to true secrets; use these stats to refine severity thresholds and suppression logic."    },    {      "module": "credential_exposure",      "signal_type_or_use_case": "database_exposed_without_auth",      "source_reliability": "Open/explore datastore plugins connect and enumerate databases/indices, increasing confidence that the service was unauthenticated at scan time, but they do not classify data sensitivity.",      "freshness_considerations": "Rely on age and update_date to avoid over-alerting on long-closed exposures; large leaks with very old timestamps should be flagged as historical unless corroborated.",      "corroboration_rules": "Where allowed, attempt read-only connections to verify the service is still unauthenticated and assess data type; never make breach/PII assertions solely from historical leak.dataset values.",      "calibration_todo": "Build empirical distributions of leak.dataset.size/rows/age per plugin to choose quantitative thresholds for high vs critical and to decide when to suppress very old, low-size leaks."    },    {      "module": "stealer_log_exposure",      "signal_type_or_use_case": "LeakIX host/domain context enrichment for stealer-log signals",      "source_reliability": "LeakIX reliably ties leaks and services to IP/host; this is useful for showing that malware-compromised assets have a history of misconfiguration but does not itself indicate stealer-log exposure.",      "freshness_considerations": "Context remains useful even when older, but you may want to show age prominently so analysts understand if misconfigurations were historical.",      "corroboration_rules": "Always start from a stealer-log-based signal; verify that the LeakIX events share IP/host and are within a reasonable time window around the compromise before using them to adjust risk scoring.",      "calibration_todo": "Track correlation rates between stealer-log signals and LeakIX leaks; experiment with incorporating this as a risk multiplier in global scoring rather than changing per-signal severity."    }  ] }`
