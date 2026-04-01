---
title: "output / threat_intel / leakix"
aliases: ["leakix output", "leakix signal registry"]
tags: [zima, research, outputs, signal-registry, threat_intel, leakix, graph_exclude]
type: provider_research_output
provider: leakix
provider_category: threat_intel
status: complete
prompt_note: prompt.md
provider_folder: leakix.md
obsidianUIMode: preview
---

# LeakIX (Exposed Services & Data Leak Search Engine)

**Service:** https://leakix.net
**API Docs:** https://docs.leakix.net
**CLI wrapper (Ringmast4r):** https://github.com/Ringmast4r/leakix (basic — do not use; use official API directly)
**Official Python client:** `pip install leakix`
**Auth:** Free API key from leakix.net account registration
**Free tier:** Yes — rate-limited but functional for prototype use

LeakIX is a **legitimate, well-regarded OSINT search engine** that indexes exposed services across the public internet: misconfigured databases, open directories, vulnerable endpoints, exposed cloud storage, and data-leaking services. Think of it as **Shodan, but focused specifically on data exposure** rather than just open ports.

**Strategic value for Zima:** Fills a gap no current provider covers — "has my domain's infrastructure been exposed?" If a user's email domain has an open MongoDB, an exposed Elasticsearch cluster, or a leaking S3 bucket, LeakIX surfaces it. This is the **infrastructure exposure** module that Zima doesn't have yet.

---

## A. Tool/API Surface Appendix

### Authentication

```bash
# Register free account at leakix.net
# API key available in account settings
export LEAKIX_API_KEY="your-api-key"
```

### REST API Endpoints

#### 1. Search

```
GET https://leakix.net/search?scope=leak&q=domain:example.com
Authorization: api-key YOUR_API_KEY
```

**Query scopes:**
| Scope | What it searches |
|---|---|
| `leak` | Confirmed data leaks (exposed databases with contents) |
| `service` | Exposed services (open ports, misconfigurations) |

**Query filters:**
| Filter | Example | Description |
|---|---|---|
| `domain:` | `domain:example.com` | Search by domain |
| `ip:` | `ip:1.2.3.4` | Search by IP address |
| `port:` | `port:9200` | Search by exposed port |
| `protocol:` | `protocol:elasticsearch` | Search by protocol/service type |
| `country:` | `country:US` | Filter by country |
| `tag:` | `tag:open-database` | Filter by tag |

#### 2. Host Lookup

```
GET https://leakix.net/host/{ip_or_domain}
Authorization: api-key YOUR_API_KEY
```

Returns all known exposed services and leaks for a specific host.

#### 3. Subdomains

```
GET https://leakix.net/api/subdomains/{domain}
Authorization: api-key YOUR_API_KEY
```

Returns discovered subdomains from certificate transparency logs and scanning.

### Response Schema (per result)

```json
{
  "ip": "1.2.3.4",
  "host": "example.com",
  "port": "9200",
  "protocol": "elasticsearch",
  "transport": ["tcp"],
  "summary": "Open Elasticsearch cluster with 150GB data",
  "time": "2026-03-15T10:30:00Z",
  "ssl": {
    "detected": true,
    "enabled": false,
    "jarm_hash": "..."
  },
  "http": {
    "status": 200,
    "title": "...",
    "headers": {}
  },
  "geoip": {
    "country_name": "United States",
    "city_name": "Ashburn",
    "as_name": "Amazon.com Inc.",
    "as_num": 14618
  },
  "leak": {
    "severity": "high",
    "dataset": {
      "rows": 1500000,
      "size": 150000000,
      "collections": 12
    }
  },
  "tags": ["open-database", "elasticsearch", "no-auth"]
}
```

### Rate Limits (free tier)

- Not publicly documented per-minute/per-day limits
- Free tier is rate-limited (expect ~100 req/day based on community reports)
- Sufficient for Zima prototype (1 user scan = 2-5 API calls: domain search + host lookups)

### Official Python Client

```python
import leakix

client = leakix.Client(api_key="your-key")

# Search for exposed services on a domain
results = client.search("domain:example.com", scope="leak")

# Get host details
host = client.host("1.2.3.4")

# Get subdomains
subs = client.subdomains("example.com")
```

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| infrastructure_exposure | direct_signal_input | domain_leak_search | `GET /search?scope=leak&q=domain:{domain}` | direct_signal_input | domain, email_domain | Requires user's email domain or explicitly provided domain. Only trigger for domains the user owns or is associated with. | docs.leakix.net | Primary use: check if user's domain has exposed databases or services. |
| infrastructure_exposure | direct_signal_input | host_lookup | `GET /host/{ip_or_domain}` | direct_signal_input | ip_address, domain | Requires IP or domain from prior scan. Used for deeper investigation of a specific host. | docs.leakix.net | Secondary: drill into specific hosts found in domain search. |
| data_exposure | enrichment_only | subdomain_enumeration | `GET /api/subdomains/{domain}` | enrichment_only | domain | Requires domain. Run as enrichment to expand attack surface before leak search. | docs.leakix.net | Feeds subdomain list back into leak search. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| infrastructure_exposure | infrastructure_exposure | leakix | domain_leak_search | `exposed_service_found` | infrastructure_security | medium | yes | Critical if leak.dataset.rows > 100000 or protocol in [elasticsearch, mongodb, mysql, redis]. High if service has no auth. Medium for other exposed services. | domain | true_finding | `search_results.length > 0 AND result.leak != null` | `ip`, `host`, `port`, `protocol`, `summary`, `time`, `leak.severity`, `leak.dataset.rows`, `leak.dataset.size` | `geoip.country_name`, `geoip.as_name`, `ssl.enabled`, `tags` | "Exposed {protocol} service found on {host}:{port} — {summary}." | documented | docs.leakix.net | Core signal. Exposed database on user's domain is a high-priority finding. |
| infrastructure_exposure | infrastructure_exposure | leakix | domain_leak_search | `exposed_service_no_auth` | infrastructure_security | high | no | — | domain | true_finding | `result.tags contains "no-auth"` | `ip`, `host`, `port`, `protocol`, `tags` | `geoip`, `ssl` | "Unauthenticated {protocol} service exposed on {host}:{port}." | documented | docs.leakix.net | Subset of exposed_service_found; no-auth tag indicates zero authentication on a publicly reachable service. |

### Signal Design Notes

- **`exposed_service_found`** is the core signal. If LeakIX has indexed an exposed database on a user's domain, that's a legitimate infrastructure exposure finding.
- **Severity scaling:** An exposed Elasticsearch cluster with 1.5M rows is critical. An open Redis on a dev subdomain is medium. Use `leak.dataset.rows`, `protocol`, and `tags` for conditional severity.
- **Freshness matters:** LeakIX results include timestamps. Services indexed >90 days ago may have been remediated. Flag stale results as lower confidence.
- **User must own/control the domain** — do not run infrastructure scans on domains the user doesn't own. Gating: derive domain from user's email address, or require explicit confirmation.

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| infrastructure_exposure | exposed_service_found | High: LeakIX actively scans the internet and verifies exposed services. Data is first-party (their own scanners). | Medium: Results reflect the time of last scan. Services may have been patched since. Check `time` field — results older than 90 days should be flagged as potentially stale. | Corroborate with a live check: attempt to connect to the exposed port/service to confirm it's still open. If live check fails, downgrade to "previously exposed." | Track false positive rate (services that were exposed but are now remediated). Consider adding a live verification step for high-severity findings. |
| data_exposure | subdomain_enumeration | Medium-High: Certificate transparency + scanning is reliable for subdomain discovery. Some subdomains may be internal-only or no longer active. | High (CT logs are near-real-time). | Cross-reference with DNS resolution to confirm subdomains are live. | Monitor for expired/parked subdomains that inflate the count without real exposure. |

---

## Provider Summary

### Strongest Use Cases

- **"Is my domain leaking data?"** — The primary question LeakIX answers. Exposed databases, open cloud storage, unauthenticated services on the user's infrastructure.
- **Infrastructure attack surface mapping** — Subdomain enumeration + service scanning gives a comprehensive view of what's exposed.
- **Data breach context** — When HIBP/DeHashed report a breach on a domain, LeakIX can show *how* the data was exposed (open database, misconfigured service).

### What Not To Use It For

- Do not use for personal identity exposure (email/username lookup). That's what HIBP/maigret/holehe handle.
- Do not use for domains the user doesn't own — both ethically and legally.
- Do not treat stale results as confirmed current exposures without live verification.

### Implementation Cautions

- **Domain ownership verification:** Only scan domains derived from user's verified email address. Never scan arbitrary domains.
- **Stale data risk:** Results may be weeks/months old. A "critical" exposed database may have been patched yesterday. Consider adding a light live check (TCP connect probe) before surfacing critical findings.
- **Free tier limits:** Sufficient for prototype (1 scan = 2-5 API calls). Production use may need a paid plan.
- **Data sensitivity:** LeakIX sometimes includes sample data from exposed databases in its results. Do not display raw leaked data to the user — only surface the existence and metadata of the exposure.
- **Use official Python client**, not Ringmast4r's wrapper (which is basic and has no structured output).

### Current Zima Stage Fit

- **Phase:** Infrastructure exposure module — new module not currently in Zima
- **Module:** `infrastructure_exposure` (new), potentially `data_exposure`
- **Classification:** `direct_signal_input` (exposed services are real findings)
- **Pipeline position:** User email domain → LeakIX domain search → [exposed service findings] + [subdomain list] → optional live verification

---

# Structured JSON

```json
{
  "provider": "leakix",
  "provider_category": "threat_intel",
  "provider_role": "direct_signal_input",
  "source": "https://leakix.net",
  "api_docs": "https://docs.leakix.net",
  "requires_api_key": true,
  "api_key_cost": "free (rate-limited)",
  "requires_network": true,
  "install": "pip install leakix",
  "module_mappings": [
    {
      "module": "infrastructure_exposure",
      "provider_role": "direct_signal_input",
      "provider_method": "domain_leak_search",
      "endpoint_or_artifact": "GET /search?scope=leak&q=domain:{domain}",
      "classification": "direct_signal_input",
      "entity_types": ["domain", "email_domain"],
      "gating_logic": "Requires user's verified email domain. Only scan owned domains.",
      "notes": "Core signal: exposed databases and services on user's domain."
    },
    {
      "module": "data_exposure",
      "provider_role": "enrichment_only",
      "provider_method": "subdomain_enumeration",
      "endpoint_or_artifact": "GET /api/subdomains/{domain}",
      "classification": "enrichment_only",
      "entity_types": ["domain"],
      "gating_logic": "Requires domain",
      "notes": "Feeds subdomain list back into leak search for expanded coverage."
    }
  ],
  "signal_contracts": [
    {
      "module": "infrastructure_exposure",
      "provider": "leakix",
      "provider_method": "domain_leak_search",
      "signal_type": "exposed_service_found",
      "category": "infrastructure_security",
      "severity": "medium",
      "severity_is_conditional": true,
      "conditional_rule": "Critical if leak.dataset.rows > 100000 or service is database with no-auth. High if no-auth.",
      "entity_type": "domain",
      "finding_kind": "true_finding",
      "trigger_condition": "search results non-empty with leak data",
      "evidence_fields": ["ip", "host", "port", "protocol", "summary", "time", "leak.severity", "leak.dataset"],
      "enrichment_fields": ["geoip", "ssl", "tags"],
      "summary_template": "Exposed {protocol} service found on {host}:{port} — {summary}.",
      "evidence_status": "documented"
    }
  ],
  "confidence_guidance": [
    {
      "module": "infrastructure_exposure",
      "signal_type_or_use_case": "exposed_service_found",
      "source_reliability": "High (first-party scanning by LeakIX)",
      "freshness_considerations": "Medium (results may be stale; check time field)",
      "corroboration_rules": "Live verification probe recommended for high/critical findings",
      "calibration_todo": "Track remediation rate; consider stale result threshold (>90 days)"
    }
  ]
}
```
