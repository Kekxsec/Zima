---
title: "output / threat_intel / intelx"
aliases: ["intelx output", "intelx signal registry", "intelligence x"]
tags: [zima, research, outputs, signal-registry, threat_intel, intelx]
type: provider_research_output
provider: intelx
provider_category: threat_intel
status: complete
prompt_note: prompt.md
provider_folder: intelx.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# Intelligence X (Breach, Dark Web & Paste Search Engine)

**Service:** https://intelx.io
**API Docs:** https://intelx.io/developers
**Official Python SDK:** `pip install intelx` (official, maintained by IntelX)
**CLI wrapper (Ringmast4r):** https://github.com/Ringmast4r/Intelx_CLI_Free_Version (basic — prefer official SDK)
**Auth:** Free API key from intelx.io account registration
**Free tier:** Yes — 90 results per search, limited preview, basic functionality

Intelligence X is a **legitimate commercial OSINT search engine** that indexes breach data, dark web content, paste sites, public document repositories, and WHOIS history. It's the most comprehensive single-source for answering: "Where does this email/domain/IP appear across leaked datasets, pastes, and dark web forums?"

**Strategic value for Zima:** Complementary to HIBP and DeHashed. HIBP tells you *which breach* — IntelX tells you *where the data appeared and in what context* (paste site, dark web forum, document repository). This is the **breach context enrichment** layer.

---

## A. Tool/API Surface Appendix

### Authentication

```python
# Register free account at intelx.io
# API key available in account settings
from intelx import intelx
ix = intelx(key="YOUR_API_KEY")
```

### API Endpoints

#### 1. Search

```python
# Search for an email across all indexed sources
results = ix.search("user@example.com")

# Search with selector type
results = ix.search("example.com", type=1)  # 1=domain
```

**Supported selectors:**

| Type ID | Selector | Description |
|---|---|---|
| 0 | email | Email address search |
| 1 | domain | Domain search |
| 2 | URL | Full URL search |
| 3 | IP | IP address search |
| 4 | CIDR | IP range search |
| 5 | system hash | File/system hash search |
| 7 | phone | Phone number search |
| 8 | username | Username search |
| 10 | bitcoin address | Crypto address search |

#### 2. Phonebook (identity resolution)

```python
# Find email addresses, domains, URLs associated with a selector
phonebook = ix.phonebook("example.com")
```

Returns associated emails, subdomains, URLs — useful for identity graph expansion.

#### 3. File Preview / Download

```python
# Preview a specific result
preview = ix.preview(result_id)

# Download full content
content = ix.download(result_id)
```

### Response Schema (search result)

```json
{
  "id": "abc123",
  "name": "paste-2024-01-example.txt",
  "date": "2024-01-15T00:00:00Z",
  "bucket": "pastes",
  "type": "text/plain",
  "media": 0,
  "size": 45000,
  "storageid": "...",
  "accesslevel": 1,
  "systemid": "..."
}
```

**Bucket types (source categories):**

| Bucket | Description |
|---|---|
| `pastes` | Pastebin, GitHub Gists, etc. |
| `leaks` | Breach/leak databases |
| `darknet` | Dark web forums, marketplaces |
| `whois` | Historical WHOIS records |
| `documents` | Public document repositories |
| `web` | General web content |

### Free Tier Limits

| Feature | Free | Professional |
|---|---|---|
| Results per search | 90 | 10,000+ |
| Preview | Limited | Full |
| Downloads | Limited | Full |
| Phonebook | Available | Full |
| Rate limit | ~10 req/min (estimated) | Higher |
| Buckets | All | All |

### Official Python SDK

```bash
pip install intelx
```

The official SDK handles pagination, file downloads, and phonebook queries. It's well-maintained and the recommended integration path. Do not use Ringmast4r's CLI wrapper — it's limited to basic search with no structured output.

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| breach_monitor | enrichment_only | email_search | `ix.search(email, type=0)` | enrichment_only | email | Requires confirmed email address. Run after HIBP/DeHashed to add breach context (where data appeared). | intelx.io/developers | Context enrichment: which paste sites, dark web forums, document repos mention this email. |
| breach_monitor | enrichment_only | domain_search | `ix.search(domain, type=1)` | enrichment_only | domain | Requires domain. Used to find all breach/paste/darkweb mentions of the user's domain. | intelx.io/developers | Broader than email search — catches mentions the email-specific search might miss. |
| username_exposure | enrichment_only | phonebook_lookup | `ix.phonebook(selector)` | enrichment_only | email, domain | Run after initial identity collection. Phonebook returns associated emails/subdomains/URLs. | intelx.io/developers | Identity graph expansion — find email addresses and subdomains associated with a domain. |
| darkweb_identity_monitor | direct_signal_input | email_search_darknet | `ix.search(email, type=0)` filtered to `bucket=darknet` | direct_signal_input | email | Requires email. Filter results to darknet bucket only. | intelx.io/developers | Dark web mention of user's email is a high-severity finding. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| breach_monitor | breach_monitor | intelx | email_search | `breach_context_found` | data_exposure | low | yes | Escalate to medium if bucket=leaks; high if bucket=darknet | email | enrichment_finding | `search_results.length > 0` | `id`, `name`, `date`, `bucket`, `size` | `type`, `media`, `accesslevel` | "Email {email} found in {bucket} source: {name} (dated {date})." | documented | intelx.io/developers | Context signal — adds "where" to HIBP's "which breach." |
| darkweb_identity_monitor | darkweb_identity_monitor | intelx | email_search_darknet | `darkweb_mention_found` | identity_exposure | high | no | — | email | true_finding | `search_results filtered to bucket=darknet has results` | `id`, `name`, `date`, `bucket` | `size`, `type` | "Email {email} mentioned in dark web source: {name} (dated {date})." | documented | intelx.io/developers | High-severity finding. Dark web mention indicates active trading or targeting. |

### Signal Design Notes

- **`breach_context_found`** is enrichment — adds context to HIBP/DeHashed breach findings. On its own, a paste mention is low severity. In the darknet bucket, it escalates to high.
- **`darkweb_mention_found`** is a true finding — if a user's email appears on dark web forums/marketplaces, that's actionable intel.
- **90-result free tier limit** means we may miss results for heavily-breached emails. Document this limitation to the user.
- **Do not display content previews** — IntelX results may contain actual leaked data. Only surface metadata (source name, date, bucket type).

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| breach_monitor | breach_context_found | High: IntelX is a well-established OSINT platform used by law enforcement, enterprise security teams, and researchers. Data is indexed from real sources. | Medium: Index is point-in-time. Sources may have been taken down since indexing. Date field indicates when IntelX indexed it, not necessarily when the data was leaked. | Cross-reference with HIBP/DeHashed — if same breach appears in both, high confidence. If IntelX finds something HIBP doesn't, it may be from a paste or forum not covered by HIBP. | Track overlap rate with HIBP. If IntelX consistently finds results HIBP misses, it justifies the additional API call. |
| darkweb_identity_monitor | darkweb_mention_found | Medium-High: Dark web indexing is inherently incomplete. IntelX covers a subset of dark web forums — not all. Absence does not mean safety. | Medium: Dark web sources are ephemeral. A mention indexed 2 years ago may no longer be actively traded. | Corroborate with Hudson Rock (stealer logs) and dedicated dark web monitors if available. | Monitor for false associations — domain-level mentions that don't specifically identify the user. |

---

## Provider Summary

### Strongest Use Cases

- **Breach context enrichment:** HIBP says "your email was in the Dropbox breach." IntelX tells you "your email appears in 3 paste sites and a dark web forum post from 2024."
- **Dark web monitoring:** Free-tier dark web mention detection for personal emails. Few other free/cheap tools provide this.
- **Identity graph expansion:** Phonebook API reveals associated emails, subdomains, and URLs from a single selector — feeds back into the discovery pipeline.

### What Not To Use It For

- Do not use as the primary breach lookup — HIBP is more comprehensive and purpose-built for that. IntelX is a context layer.
- Do not display content previews to users — results may contain actual leaked data, passwords, PII.
- Do not rely on the 90-result free tier limit for heavily-breached domains (enterprise domains may have thousands of results).

### Implementation Cautions

- **Free tier is limiting** — 90 results per search. For personal users (1-3 emails), this is fine. For enterprise domains, you'll truncate.
- **Data sensitivity:** IntelX indexes raw breach data. Your application must never surface actual leaked content — metadata only.
- **Legal:** IntelX is a legitimate OSINT service operating within legal frameworks. However, accessing and storing breach data may have GDPR implications. Review DPA requirements.
- **Use official Python SDK** (`pip install intelx`), not Ringmast4r's wrapper.
- **Rate limits:** Free tier is conservative. Implement backoff and caching.

### Current Zima Stage Fit

- **Phase:** Breach enrichment layer — runs after HIBP/DeHashed, adds context
- **Module:** `breach_monitor` (enrichment), `darkweb_identity_monitor` (direct signal), `username_exposure` (phonebook enrichment)
- **Classification:** `enrichment_only` for breach context, `direct_signal_input` for dark web mentions
- **Pipeline position:** HIBP/DeHashed → [breach confirmed] → IntelX → [breach context: where/when/how data appeared] → user report

---

# Structured JSON

```json
{
  "provider": "intelx",
  "provider_category": "threat_intel",
  "provider_role": "enrichment_only",
  "source": "https://intelx.io",
  "api_docs": "https://intelx.io/developers",
  "requires_api_key": true,
  "api_key_cost": "free (90 results/search limit)",
  "requires_network": true,
  "install": "pip install intelx",
  "module_mappings": [
    {
      "module": "breach_monitor",
      "provider_role": "enrichment_only",
      "provider_method": "email_search",
      "endpoint_or_artifact": "ix.search(email, type=0)",
      "classification": "enrichment_only",
      "entity_types": ["email"],
      "gating_logic": "Requires confirmed email. Run after HIBP/DeHashed.",
      "notes": "Adds breach context: where data appeared (paste, darknet, document repo)."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider_role": "direct_signal_input",
      "provider_method": "email_search_darknet",
      "endpoint_or_artifact": "ix.search(email) filtered to bucket=darknet",
      "classification": "direct_signal_input",
      "entity_types": ["email"],
      "gating_logic": "Requires email. Filter to darknet bucket.",
      "notes": "Dark web mention = high-severity finding."
    },
    {
      "module": "username_exposure",
      "provider_role": "enrichment_only",
      "provider_method": "phonebook_lookup",
      "endpoint_or_artifact": "ix.phonebook(selector)",
      "classification": "enrichment_only",
      "entity_types": ["email", "domain"],
      "gating_logic": "Run after identity collection",
      "notes": "Identity graph expansion — associated emails, subdomains, URLs."
    }
  ],
  "signal_contracts": [
    {
      "module": "breach_monitor",
      "provider": "intelx",
      "signal_type": "breach_context_found",
      "category": "data_exposure",
      "severity": "low",
      "severity_is_conditional": true,
      "conditional_rule": "Medium if bucket=leaks; High if bucket=darknet",
      "finding_kind": "enrichment_finding",
      "evidence_fields": ["id", "name", "date", "bucket", "size"],
      "summary_template": "Email {email} found in {bucket} source: {name} (dated {date})."
    },
    {
      "module": "darkweb_identity_monitor",
      "provider": "intelx",
      "signal_type": "darkweb_mention_found",
      "category": "identity_exposure",
      "severity": "high",
      "finding_kind": "true_finding",
      "evidence_fields": ["id", "name", "date", "bucket"],
      "summary_template": "Email {email} mentioned in dark web source: {name} (dated {date})."
    }
  ],
  "confidence_guidance": [
    {
      "module": "breach_monitor",
      "source_reliability": "High (well-established OSINT platform)",
      "freshness_considerations": "Medium (point-in-time index)",
      "corroboration_rules": "Cross-reference with HIBP/DeHashed",
      "calibration_todo": "Track HIBP overlap rate; measure unique findings"
    }
  ]
}
```
