---
title: "output / breach / wikileaks"
aliases: ["wikileaks output", "wikileaks signal registry"]
tags: [zima, research, outputs, signal-registry, breach, wikileaks, graph_exclude]
type: provider_research_output
provider: wikileaks
provider_category: breach
status: not_started
prompt_note: prompt.md
provider_folder: wikileaks.md
obsidianUIMode: preview
---
There is no official, structured breach/credential API exposed by WikiLeaks; the only machine‑readable interface is a generic MediaWiki API for the auxiliary “our.wikileaks.org” wiki, while the main leak corpus is only searchable via HTML UIs with documented text search operators but no documented JSON or schema. As a result, WikiLeaks should not currently be wired into `breach_monitor` as an automated signal producer; at best it is a human‑driven research/enrichment source, and all direct breach signals should be considered out of scope until you build your own crawl/parse pipeline over their dumps.

---

## A. API Surface Appendix

### 1. `https://wikileaks.org/search` (simple search UI)

- **Endpoint / artifact**

    - Path: `https://wikileaks.org/search` (simple search box in header and homepage “Custom Search” widgets)

    - There is also an “Advanced search” at `https://wikileaks.org/search/advanced`

- **Purpose**

    - Full‑text search across WikiLeaks‑hosted document collections (war logs, emails, cables, featured projects, etc.), primarily by keyword/phrase with rich operators.

- **Supported entity types (for your usage)**

    - Effectively arbitrary text; typical Zima‑relevant entities would be: `email`, `domain`, `company`, `person_name`, `keyword`.

    - Email search is explicitly supported via quoting (e.g., `"burton@stratfor.com"`).[ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

- **Auth / execution**

    - No authentication for interactive use; public HTML form.[arxiv](https://arxiv.org/abs/2405.17681)

    - No documented API key, rate limits, or automation policy; any scraping/automation would require separate legal/ToS review. (No official automation docs found.)

- **Request parameters & semantics**

    - The documentation describes **search operators** that are typed into the single search box; parameters like `@title`, `@content`, `SENTENCE`, `PARAGRAPH`, proximity and quorum operators, and Boolean `|`/`!`/`-`, but not HTTP query parameter names. [ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

    - Examples from docs (all typed into the box, not querystring names):

        - `"International Criminal Court"` – phrase search.

        - `ECHR | "European Court of Human Rights"` – OR.

        - `Egypt !Mubarak` or `Egypt -Mubarak` – exclude term.

        - `@title Haiti @content Martelly` – constrain title vs body.

        - `"Australia trade"~10` – proximity search.

        - `"Pakistan toxic chemicals US drone strikes"/5` – quorum (at least 5 of 6 words).

        - `Oakland SENTENCE port SENTENCE "Occupy Wall Street"` – sentence‑level co‑occurrence.

        - Notes that `@` is an operator, so email addresses must be quoted, e.g. `"burton@stratfor.com"`.[ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

- **Response format & fields**

    - Response is **HTML**, not JSON; the pages rendered at `/search` and `/search/advanced` are standard web pages with a list of matching documents, dates, and descriptions.[arxiv](https://arxiv.org/abs/2405.17681)

    - No official schema or machine‑readable field list is documented for search results (e.g., no published JSON with `title`, `url`, etc. specifically for this search service).

- **Presence / optionality**

    - Because there is no documented machine format, _all_ field‑level structure (titles, dates, links) is effectively **undocumented/inferred from HTML** and may change without notice.

- **Response variants**

    - Successful hit: HTML page with non‑zero results; count and list are visible to humans but not documented as JSON fields.

    - Successful no‑hit: HTML page with “0 results” messaging; not documented as a specific status code or JSON body.

    - Partial/limited: not documented; any pagination or truncation is done via the HTML UI (`page` parameter in advanced search URL) but without a schema.

    - Errors: standard HTTP errors or generic error pages; no structured error schema documented.

- **Citation refs**

    - Search operators and behavior: `https://wikileaks.org/search/info/`.[ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

    - Existence of advanced search UI: `https://wikileaks.org/search/advanced`

    - General site search presence: `https://wikileaks.org` and `https://search.wikileaks.org`.[arxiv](https://arxiv.org/abs/2405.17681)


---

### 2. `https://wikileaks.org/search/advanced` (advanced search UI)

This is essentially the same search index as `/search` with additional HTML form filters; it does **not** expose a separate documented API.

- **Endpoint / artifact**

    - Path: `https://wikileaks.org/search/advanced`

- **Purpose**

    - Provide form‑based controls (likely date ranges, document collections, file types, etc.) on top of the same full‑text search used by simple search. (The visible page heading is “Advanced search”.)[arxiv](https://arxiv.org/abs/2405.17681)

- **Supported entity types**

    - Same as `/search` – arbitrary text, including emails/domains as quoted strings.[ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

- **Auth / execution**

    - Public HTML UI; no documented token or rate‑limit scheme.

- **Request parameters & semantics**

    - URL shows `page=0`; other parameters are encapsulated in HTML forms and **not documented as an API**.[arxiv](https://arxiv.org/abs/2405.17681)

    - Semantics for filtering (e.g., specific leak collections) are visible in the UI controls but not described as a stable machine contract.

- **Response format & fields**

    - HTML only; same caveats as simple search.

- **Response variants / errors**

    - Same as `/search`.

- **Citation refs**

    - `https://wikileaks.org/search/advanced?page=0`


---

### 3. `https://our.wikileaks.org/api.php` (MediaWiki API for auxiliary wiki)

This is **the only documented machine‑readable API** on a WikiLeaks‑controlled domain, but it serves the _our.wikileaks.org_ wiki (meta information and documentation), not the main leak corpus.

- **Endpoint / artifact**

    - Base path: `https://our.wikileaks.org/api.php`

- **Purpose**

    - Standard MediaWiki API for querying pages, revisions, categories, etc. on the _our.wikileaks.org_ site (help, docs, etc.).[semanticscholar](https://www.semanticscholar.org/paper/b59ba142941e6b823984c58a15a4a4e811f79389)

- **Supported entity types (for your use)**

    - Wiki pages and metadata; not directly emails/passwords.

    - For Zima, this is at best a `company`/`topic` enrichment source (e.g., pages documenting specific WikiLeaks projects or tools), not a breach dataset.

- **Auth / execution**

    - Read operations (e.g., `action=query`) require only standard read rights, no auth by default.[semanticscholar](https://www.semanticscholar.org/paper/b59ba142941e6b823984c58a15a4a4e811f79389)

    - Standard MediaWiki `format` parameter controls output (`json`, `jsonfm`, `xml`, etc.). The `jsonfm` “pretty JSON in HTML” module is also documented.[our.wikileaks](https://our.wikileaks.org/api.php?action=help&modules=jsonfm)

- **Key modules / methods relevant to search**

    1. `action=query&list=search` (Search module)

        - Official MediaWiki docs (upstream) describe:

            - Example: `api.php?action=query&list=search&srsearch=Nelson%20Mandela&utf8=&format=json`.[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

            - Response structure (from MediaWiki docs, not WikiLeaks‑specific):

                - `batchcomplete` (string).

                - `continue` object with `sroffset` and `continue` for pagination.

                - `query.searchinfo.totalhits` (integer).

                - `query.search[]` array with objects containing at least:

                    - `ns` (namespace id, int),

                    - `title` (string),

                    - `pageid` (int),

                    - `size` (int, bytes),

                    - `wordcount` (int),

                    - `snippet` (HTML excerpt),

                    - `timestamp` (ISO8601).[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

        - The our.wikileaks API help confirms MediaWiki `action=query` with `list=search` as an available list type.[semanticscholar](https://www.semanticscholar.org/paper/b59ba142941e6b823984c58a15a4a4e811f79389)

    2. Other `action=query` lists and props (less relevant to breach use‑case):

        - Lists include: `allpages`, `allusers`, `recentchanges`, `categorymembers`, etc.[semanticscholar](https://www.semanticscholar.org/paper/b59ba142941e6b823984c58a15a4a4e811f79389)

        - Output format controlled via `format=json`, `format=xml`, etc.; `jsonfm` for pretty JSON in HTML.[our.wikileaks](https://our.wikileaks.org/api.php?action=help&modules=jsonfm)

- **Presence / optionality**

    - `action`, `format`, and either `titles` / `pageids` / `revids` or a `generator`/`list` selection are required.[semanticscholar](https://www.semanticscholar.org/paper/b59ba142941e6b823984c58a15a4a4e811f79389)

    - For `list=search`, `srsearch` is required (upstream docs).[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

    - Pagination fields `continue` / `sroffset` appear only when more results exist.[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

- **Response variants**

    - Hit with more results than limit: includes `continue` block with `sroffset`.[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

    - Hit within limit: `batchcomplete` and `query.search` without `continue`.[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

    - No‑hit: `totalhits` 0 and empty `query.search[]` (upstream behavior).[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

    - Errors: MediaWiki standard error JSON with an `error` object (not shown in our.wikileaks help, but standard).

- **Citation refs**

    - our.wikileaks MediaWiki API help: `https://our.wikileaks.org/api.php?action=help&modules=query`.[semanticscholar](https://www.semanticscholar.org/paper/b59ba142941e6b823984c58a15a4a4e811f79389)

    - Example JSON output description from our.wikileaks API (Semantic MediaWiki `action=ask` example): `format=json` mentioned explicitly.[our.wikileaks](https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1)

    - MediaWiki upstream `API:Search` docs with example request and JSON response: `https://www.mediawiki.org/wiki/API:Search`.[mediawiki](https://www.mediawiki.org/wiki/API:Search/pt)

    - JSON formatting module `jsonfm`: `https://our.wikileaks.org/api.php?action=help&modules=jsonfm`.[our.wikileaks](https://our.wikileaks.org/api.php?action=help&modules=jsonfm)


---

### 4. `https://our.wikileaks.org/api.php?action=ask` (Semantic MediaWiki query)

The earlier example at `our.wikileaks.org/api.php?action=ask&query=...` is a **Semantic MediaWiki** query; it is machine‑readable but again serves meta‑wiki pages, not breach data.[our.wikileaks](https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1)

- **Endpoint / artifact**

    - Example: `https://our.wikileaks.org/api.php?action=ask&query=[[Modification date::+]]|limit=5|offset=1`. [our.wikileaks](https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1)

- **Purpose**

    - Execute Semantic MediaWiki structured queries against properties and pages on _our.wikileaks.org_.[our.wikileaks](https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1)

- **Supported entity types**

    - Wiki page concepts and properties; not leaked email/passwords.

- **Auth / execution**

    - Same MediaWiki auth model as above; `format=json` can be specified to get JSON instead of HTML representation.[our.wikileaks](https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1)

- **Response format & fields**

    - Example JSON (HTML representation truncated) shows:

        - `query-continue-offset` (int),

        - `query.printrequests[]`,

        - `query.results` (map keyed by page title, each containing:

            - `printouts` (property values),

            - `fulltext`,

            - `fullurl`,

            - `namespace`,

            - `exists`,

            - `displaytitle`),

        - `query.meta` with `hash`, `count`, `offset`, `time`.[our.wikileaks](https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1)

- **Citation refs**

    - Example and structure: `https://our.wikileaks.org/api.php?action=ask&query=...`.[our.wikileaks](https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1)


---

### 5. Other references / non‑APIs

- **CableSearch API** – a **third‑party project** indexing WikiLeaks Cablegate content with its own API, unaffiliated with WikiLeaks and documented on external sites.

    - Not hosted under `wikileaks.org` and not controlled by WikiLeaks; should be treated as a separate provider if you ever integrate it.

- **Conclusion for API surface**

    - For the **main leak corpus**, WikiLeaks only documents **HTML search UIs with text operators**, not a programmatic breach/credential API.

    - The only JSON APIs under a WikiLeaks domain are generic MediaWiki/Semantic MediaWiki for `our.wikileaks.org`, which are **not leak datasets and not credential/PII feeds**.


---

## B. Module Mapping Table

Requested columns:
`module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes`

text

``| module         | provider_role   | provider_method         | endpoint_or_artifact                            | classification     | entity_types                  | gating_logic                                                                                                                                      | citation_refs                                                                                           | notes | |----------------|-----------------|-------------------------|--------------------------------------------------|--------------------|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|-------| | breach_monitor | signal_producer | search (simple/advanced)| https://wikileaks.org/search and /search/advanced| out_of_scope       | email, domain, keyword        | Do not integrate as automated source until a stable, documented machine-readable API or local mirror is available; current output is HTML only. | https://wikileaks.org/search/info/ https://wikileaks.org/search/advanced       | HTML UI only; no documented JSON or schema. Mentions may indicate exposure but require manual review and custom parsing. | | breach_monitor | signal_producer | N/A (MediaWiki search)  | https://our.wikileaks.org/api.php?action=query  | utility_only (global), out_of_scope (breach_monitor) | topic, wiki_page, company | For breach_monitor specifically, ignore; this API indexes the our.wikileaks.org wiki, not the leak corpus or credential dumps.                   | https://our.wikileaks.org/api.php?action=help&modules=query https://www.mediawiki.org/wiki/API:Search | Could optionally be used by a future “provider_docs” or “intel_notes” module to enrich human investigations, but not for credential signals. | | breach_monitor | signal_producer | N/A (Semantic ask)      | https://our.wikileaks.org/api.php?action=ask    | utility_only (global), out_of_scope (breach_monitor) | topic, wiki_page          | For breach_monitor, ignore; Semantic MediaWiki `ask` queries surface metadata about wiki pages, not leaked credential data.                     | https://our.wikileaks.org/api.php?action=ask&query=...                                         | Same as above; meta/documentation, not breach data. |``

**Key takeaway:** for the only mapped module (`breach_monitor`), WikiLeaks is **not safely usable as an automated signal source** with the current public interfaces; treat it as out_of_scope for automated signals and, at most, a manual research tool.

---

## C. Signal Contract Table

Per your instructions, only include rows for **standalone signals** that should actually be emitted by a module. Given:

- No documented breach/credential API.

- Only HTML document search for the leak corpus.[ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

- The single JSON API is for a meta‑wiki, not leaks.


…there is **no implementation‑safe way** to define field‑level `trigger_condition` in terms of provider fields for breach monitoring.

Accordingly, the signal contract table is **intentionally empty**:

text

`| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes | |--------|--------|----------|-----------------|------------|----------|----------|-------------------------|------------------|------------|--------------|-------------------|-----------------|-------------------|------------------|-----------------|---------------|-------|`

**Explanation:**

- Any realistic detection of credential exposure in WikiLeaks documents would require **your own crawler, document store, and NLP/regex pipeline** operating on bulk leaks or local mirrors (e.g., torrents or Cablegate dumps), not on a stable provider API response.

- Because there is no provider JSON schema for “credential_leak” or even “document result with typed fields,” defining Zima’s `trigger_condition` on “actual API field names” would be speculative and brittle.[ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

- To stay within your “do not invent field names” requirement, we must defer signal contracts until you own the ingestion/parsing layer and can expose **your own** normalized schema.


---

## D. Severity Rules (Conceptual – non‑binding)

Since there are **no concrete signal types** wired for this provider, there are no production severity rules to codify. However, if in the future you ingest WikiLeaks content into your own pipeline and expose structured fields (e.g., `document_text`, `collection`, `leak_name`, `found_password_like`, `contains_hash`), the calibration **relative to your guide** should look like:

- **critical**

    - Direct, recent plaintext credentials or secrets extracted from WikiLeaks documents, especially privilege accounts or production keys (e.g., a password or API key in a leaked config file).[haveibeenpwned](https://haveibeenpwned.com/Breach/AKP)

- **high**

    - Leaked internal emails or documents containing **sensitive PII** or clear account identifiers for your org, even if no explicit password is detected (e.g., HR attachments, internal auth tokens heavily redacted but still exposing structure).[haveibeenpwned](https://haveibeenpwned.com/Breach/AKP)

- **medium**

    - Mentions of corporate email addresses or domains in politically sensitive leaks **without** direct credential evidence (e.g., you appear as correspondent or third party).[haveibeenpwned](https://haveibeenpwned.com/Breach/AKP)

- **low / info**

    - Pure contextual mentions (e.g., your domain in a news summary), historical records far removed from current infrastructure, or content obviously unrelated to authentication or PII.


But these are **future design notes**, not rules you can implement against WikiLeaks’ current public interface.

---

## E. Confidence Guidance Table

Even without concrete signals, you asked for confidence guidance per module / use‑case.

Requested columns:
`module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo`

text

`| module         | signal_type_or_use_case                                          | source_reliability                                                                                                            | freshness_considerations                                                                                                                   | corroboration_rules                                                                                                                                       | calibration_todo | |----------------|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|------------------| | breach_monitor | Manual research: “email/domain mentioned in WikiLeaks documents” | WikiLeaks is generally reliable for authenticity of published documents, but curation and context may be politically charged.  | Many leaks are years old; political/email dumps often date to 2000s–2010s, so credential relevance decays quickly.                | Treat any mention as **unverified**: corroborate with dedicated breach providers (HIBP, BreachDirectory, Leak-Lookup, etc.) and live credential checks.  | If you later build your own corpus index, empirically measure how often WikiLeaks‑based hits align with confirmed credential compromises to set default confidence. | | breach_monitor | Future pipeline: “structured leak corpus index from local mirror” | Reliability would depend on your acquisition (torrents / verified archives vs. 3rd‑party mirrors); original dumps are stable.  | Staleness depends on collection; new leaks are sporadic, not continuous; last major headline leak on main site is from 2018–2021.  | Cross‑check extracted credentials against other breach APIs, login telemetry, and password reuse detectors; require multiple corroborating indicators before high/critical. | Design calibration experiment using historical leaks plus internal telemetry to estimate precision/recall of your detection heuristics on WikiLeaks‑derived content. |`

---

## F. Provider Summary for Implementation

### Strongest potential signal types

Given current interfaces:

- **Practical strongest “signal” is not a direct breach signal, but a human‑driven investigation cue**:

    - “This corporate email or domain appears in WikiLeaks documents (e.g., AKP emails, HBGary emails, etc.).”

- Standalone breach signals (passwords, access tokens, etc.) would only be reliably extractable **after you ingest and parse leak dumps yourself**, outside the official HTML search UI.


### What WikiLeaks should _not_ be used for in Zima (current stage)

- **Not** as a structured credential or PII breach API.

    - There is no documented method like `search(email)` returning JSON with `password`, `hash`, `salt`, etc., unlike dedicated breach APIs (e.g., BreachDirectory, Leak‑Lookup).

- **Not** as a high‑volume automated search backend.

    - Only HTML search is documented; automation/scraping is undocumented and likely against operational expectations for a high‑risk journalism site.

- **Not** as a primary source for live credential compromise detection.

    - Leak content is often old and politically focused, not credential dumps; AKP/HBGary‑style email sets contain many non‑user addresses and internal chatter.


### API / auth / rate‑limit / licensing cautions

- **No official API** for the main corpus:

    - Only a search UI with sophisticated text operators is documented, not a REST/JSON API.[ojs.aaai](https://ojs.aaai.org/index.php/AAAI/article/view/31995)

- **Automation & scraping risk:**

    - WikiLeaks is positioned as a high‑risk publisher concerned with source protection and anti‑censorship; they do not advertise programmatic scraping.[arxiv](https://arxiv.org/abs/2405.17681)

    - Before any automated integration (e.g., headless browser, DOM parsing), you’d need:

        - Legal review (jurisdiction, publication rights, Copyright).

        - ToS / robots.txt review (not covered in docs retrieved).

        - Strict throttling.

- **Licensing / redistribution:**

    - Published documents are often copyrighted material republished under investigative‑journalism context; bulk ingestion into a commercial SaaS product raises legal concerns beyond technical scope.[arxiv](https://arxiv.org/abs/2405.17681)


### Provider role classification at current Zima stage

- Despite being tagged in your provider map as `provider_category: breach` and `provider_role: signal_producer`, the actual public interfaces support only:

    - **Enrichment for human analysts** (“does this identity appear in politically sensitive leaks?”).

    - **Utility** for understanding WikiLeaks itself via MediaWiki API (our.wikileaks.org)


Given your constraints (no invented fields, implementation‑grade triggers, production automation):

- Treat **WikiLeaks as `enrichment_only/utility_only` and effectively **deferred** for automated `breach_monitor` signal production.

- If you want WikiLeaks‑derived signals, you should:

    - Acquire datasets (torrents / archives) and host them locally.

    - Build your own parsers and schema (document, collection, extracted_email, extracted_credential, etc.).

    - Expose that via a **Zima‑internal provider** with a clean JSON contract, and then define signals against _your_ fields, not WikiLeaks’ UI.


---

## G. Structured JSON Output

json

`{   "provider": "wikileaks",  "provider_category": "breach",  "provider_role": "signal_producer",  "module_mappings": [    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "search (simple/advanced)",      "endpoint_or_artifact": "https://wikileaks.org/search and https://wikileaks.org/search/advanced",      "classification": "out_of_scope",      "entity_types": ["email", "domain", "keyword"],      "gating_logic": "Do not integrate as automated source until a stable, documented machine-readable API or local mirror is available; current output is HTML only.",      "citation_refs": [        "https://wikileaks.org/search/info/",        "https://wikileaks.org/search/advanced"      ],      "notes": "HTML UI only; no documented JSON or schema. Mentions may indicate exposure but require manual review and custom parsing."    },    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "MediaWiki query (list=search)",      "endpoint_or_artifact": "https://our.wikileaks.org/api.php?action=query",      "classification": "utility_only",      "entity_types": ["topic", "wiki_page", "company"],      "gating_logic": "For breach_monitor specifically, ignore; this API indexes the our.wikileaks.org wiki, not the leak corpus or credential dumps.",      "citation_refs": [        "https://our.wikileaks.org/api.php?action=help&modules=query",        "https://www.mediawiki.org/wiki/API:Search"      ],      "notes": "Could optionally be used by a future documentation/intel module to enrich human investigations, but not for credential signals."    },    {      "module": "breach_monitor",      "provider_role": "signal_producer",      "provider_method": "Semantic MediaWiki ask",      "endpoint_or_artifact": "https://our.wikileaks.org/api.php?action=ask",      "classification": "utility_only",      "entity_types": ["topic", "wiki_page"],      "gating_logic": "For breach_monitor, ignore; Semantic MediaWiki ask queries surface metadata about wiki pages, not leaked credential data.",      "citation_refs": [        "https://our.wikileaks.org/api.php?action=ask&query=%5B%5BModification+date%3A%3A%2B%5D%5D%7Climit%3D5%7Coffset%3D1"      ],      "notes": "Meta/documentation only."    }  ],  "signal_contracts": [],  "confidence_guidance": [    {      "module": "breach_monitor",      "signal_type_or_use_case": "Manual research: email/domain mentioned in WikiLeaks documents",      "source_reliability": "WikiLeaks is generally reliable for authenticity of published documents, but context is politically charged and curation is opaque.",      "freshness_considerations": "Many major email/cable dumps are from 2000s–2010s; credential relevance decays quickly over time.",      "corroboration_rules": "Treat any mention as unverified; corroborate with dedicated breach APIs and live credential checks before treating as confirmed compromise.",      "calibration_todo": "If you later build a corpus index, measure overlap between WikiLeaks-derived hits and confirmed compromises to set default confidence levels."    },    {      "module": "breach_monitor",      "signal_type_or_use_case": "Future pipeline: structured leak corpus index from local mirror",      "source_reliability": "Depends on acquisition path; original WikiLeaks dumps are stable, but third-party mirrors may introduce noise.",      "freshness_considerations": "New WikiLeaks publications are sporadic; leaks are often historical rather than continuous streams.",      "corroboration_rules": "Cross-check extracted credentials with other breach sources and internal telemetry; require multiple indicators before assigning high/critical severity.",      "calibration_todo": "Design experiments using historical leaks plus authentication telemetry to estimate precision/recall of detection heuristics on WikiLeaks-derived content."    }  ] }`
