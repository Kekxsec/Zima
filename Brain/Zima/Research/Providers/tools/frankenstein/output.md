---
title: "output / tools / frankenstein"
aliases: ["frankenstein output", "frankenstein signal registry"]
tags: [zima, research, outputs, signal-registry, tools, frankenstein, graph_exclude]
type: provider_research_output
provider: frankenstein
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: frankenstein.md
obsidianUIMode: preview
---

# FRANKENSTEIN (Dual-Phenomenology DNS + HTTP/S Site Checker)

**Source:** https://github.com/Ringmast4r/FRANKENSTEIN
**Author:** Ringmast4r
**Language:** Go
**License:** Not explicitly stated
**Stars:** 4

FRANKENSTEIN performs **simultaneous DNS and HTTP/S reconnaissance** on a list of domains. It classifies each target as ALIVE (both DNS and HTTP respond), DNS-ONLY (DNS resolves but no web service), or DEAD (neither responds). It also extracts TLS certificate data, security headers, server software fingerprints, and response timing.

**Strategic value for Zima:** Domain health and security header auditing for the user's domain portfolio. After LeakIX identifies exposed services, FRANKENSTEIN can audit the full list of subdomains for TLS misconfigurations, missing security headers, and dead/orphaned DNS entries. It's a **domain posture checker**.

---

## A. Tool/API Surface Appendix

### CLI Interface

```bash
./frankenstein -input domains.txt
```

**Input:** Text file with one domain per line.

### Probe Capabilities

#### DNS Probing
- A/AAAA record resolution
- CNAME lookups
- MX record discovery
- NS record identification
- Detection of DNS-only entries (DNS resolves, no HTTP)

#### HTTP/S Probing
- Status code capture
- Page title extraction
- Server software identification (Server header)
- Full redirect chain following

#### TLS Certificate Analysis
- Certificate issuer and subject
- Common Name (CN) extraction
- Expiry date detection
- Self-signed certificate detection
- Certificate chain analysis

#### Security Header Auditing
- HSTS (Strict-Transport-Security)
- X-Frame-Options
- Cache-Control
- Content-Security-Policy presence
- X-Content-Type-Options

#### Performance Metrics
- Response timing per domain
- P50, P90, P95 percentile statistics across batch
- Retry mechanism: failed domains get a second attempt with 3x timeout

### Concurrency

50 concurrent workers — handles thousands of domains in a single batch run.

### Output

**SQLite database** with full results, exportable to CSV.
**HTML viewer:** Built-in sortable, searchable, filterable table with charts.

### Output Schema (per domain)

| Field | Type | Description |
|---|---|---|
| `domain` | string | Target domain |
| `status` | enum | ALIVE / DNS-ONLY / DEAD |
| `dns_a` | string[] | A/AAAA records |
| `dns_cname` | string | CNAME record |
| `dns_mx` | string[] | MX records |
| `dns_ns` | string[] | NS records |
| `http_status` | int | HTTP response code |
| `http_title` | string | Page title |
| `http_server` | string | Server software |
| `http_redirect_chain` | string[] | Redirect URLs |
| `tls_issuer` | string | Certificate issuer |
| `tls_cn` | string | Certificate CN |
| `tls_expiry` | timestamp | Certificate expiry |
| `tls_self_signed` | bool | Self-signed detection |
| `hsts` | bool | HSTS header present |
| `x_frame_options` | string | X-Frame-Options value |
| `cache_control` | string | Cache-Control value |
| `response_time_ms` | int | Response latency |

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| browser_configuration | direct_signal_input | security_header_audit | FRANKENSTEIN HTTP/S probe | direct_signal_input | domain | Requires domain list (from user or from LeakIX subdomain enumeration). Only scan user-owned domains. | github.com/Ringmast4r/FRANKENSTEIN README | Missing HSTS, X-Frame-Options, CSP are configurable findings. |
| infrastructure_exposure | direct_signal_input | tls_certificate_audit | FRANKENSTEIN TLS probe | direct_signal_input | domain | Same gating. | github.com/Ringmast4r/FRANKENSTEIN README | Expired/self-signed certs and near-expiry warnings. |
| infrastructure_exposure | enrichment_only | dns_health_check | FRANKENSTEIN DNS probe | enrichment_only | domain | Same gating. | github.com/Ringmast4r/FRANKENSTEIN README | DNS-ONLY and DEAD entries indicate orphaned infrastructure. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| infrastructure_exposure | infrastructure_exposure | frankenstein | tls_certificate_audit | `tls_cert_expired` | infrastructure_security | high | no | — | domain | true_finding | `tls_expiry < now()` | `domain`, `tls_expiry`, `tls_issuer`, `tls_cn` | `http_status`, `http_server` | "TLS certificate for {domain} expired on {tls_expiry} (issuer: {tls_issuer})." | documented | README | Expired cert = active security risk and user-facing error. |
| infrastructure_exposure | infrastructure_exposure | frankenstein | tls_certificate_audit | `tls_cert_expiring_soon` | infrastructure_security | medium | yes | High if expiry < 7 days; medium if < 30 days | domain | true_finding | `tls_expiry < now() + 30 days` | `domain`, `tls_expiry`, `tls_issuer` | — | "TLS certificate for {domain} expires in {days_until_expiry} days." | documented | README | Proactive warning. |
| infrastructure_exposure | infrastructure_exposure | frankenstein | tls_certificate_audit | `tls_self_signed` | infrastructure_security | medium | no | — | domain | true_finding | `tls_self_signed == true` | `domain`, `tls_issuer`, `tls_cn` | — | "Self-signed TLS certificate detected on {domain}." | documented | README | Self-signed certs indicate dev/staging exposure or MITM risk. |
| browser_configuration | browser_configuration | frankenstein | security_header_audit | `missing_security_headers` | infrastructure_security | low | yes | Medium if HSTS missing on auth/login page; low for general missing headers | domain | true_finding | `hsts == false OR x_frame_options == null` | `domain`, `hsts`, `x_frame_options`, `cache_control` | `http_status`, `http_server` | "Domain {domain} missing security headers: {missing_headers_list}." | documented | README | Configurable — which missing headers matter depends on domain purpose. |
| infrastructure_exposure | infrastructure_exposure | frankenstein | dns_health_check | `orphaned_dns_entry` | infrastructure_security | low | no | — | domain | enrichment_finding | `status == "DNS-ONLY"` | `domain`, `dns_a`, `dns_cname`, `dns_ns` | — | "DNS records exist for {domain} but no HTTP/S service responds — potential orphaned infrastructure." | inferred | README | Orphaned DNS entries can be targets for subdomain takeover. |

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| infrastructure_exposure | tls_cert_expired / tls_self_signed | High: Direct probe of live infrastructure. Certificate data is cryptographic fact — no ambiguity. | High: Live probe at scan time. | None needed — certificate state is deterministic. | None. |
| browser_configuration | missing_security_headers | High: Direct probe. Header presence/absence is deterministic. | High: Live probe. | Cross-reference with security best practices (OWASP). Not all missing headers are equally important. | Define severity tiers: which headers matter for which domain types. |
| infrastructure_exposure | orphaned_dns_entry | Medium: DNS-ONLY status may indicate planned infrastructure (pre-launch) rather than abandonment. | High: Live probe. | Check if the DNS-ONLY domain also appears in LeakIX or certificate transparency as having had a service. | Track false positive rate for DNS-ONLY entries that are intentional. |

---

## Provider Summary

### Strongest Use Cases

- **TLS certificate auditing** — Expired, expiring, and self-signed cert detection across a domain portfolio. High reliability, zero ambiguity.
- **Security header compliance** — Quick check of HSTS, X-Frame-Options, CSP across all user subdomains.
- **Orphaned DNS detection** — Find DNS entries pointing nowhere — potential subdomain takeover targets.
- **Batch performance** — 50 concurrent workers process thousands of domains fast. Suitable for scanning an entire subdomain list from LeakIX.

### What Not To Use It For

- Not a vulnerability scanner (no CVE detection, no exploit checks).
- Not an alternative to nmap/nuclei for deep service enumeration.
- Don't use DNS-ONLY status alone as a security signal — it's informational context.

### Implementation Cautions

- **Go binary:** Must be compiled or pre-built for each target platform (macOS, Linux, Windows).
- **Domain ownership:** Only scan domains the user owns. Same ethical/legal constraint as LeakIX.
- **Output parsing:** Results in SQLite — straightforward to query. No JSON API; batch CLI tool only.
- **License:** Not stated. Contact author (Ringmast4r) for terms before commercial use.
- **False positives on DNS-ONLY:** Many domains have DNS records without active HTTP services intentionally (mail servers, CNAME aliases, etc.).

### Current Zima Stage Fit

- **Phase:** Infrastructure auditing — runs after LeakIX subdomain discovery
- **Module:** `infrastructure_exposure` (TLS, DNS), `browser_configuration` (security headers)
- **Classification:** `direct_signal_input` (TLS/header findings), `enrichment_only` (DNS health)
- **Pipeline position:** LeakIX subdomains → FRANKENSTEIN batch probe → [TLS + header + DNS findings]

---

# Structured JSON

```json
{
  "provider": "frankenstein",
  "provider_category": "tools",
  "provider_role": "direct_signal_input",
  "source": "https://github.com/Ringmast4r/FRANKENSTEIN",
  "requires_api_key": false,
  "requires_network": true,
  "install": "go build (from source)",
  "module_mappings": [
    {
      "module": "infrastructure_exposure",
      "provider_role": "direct_signal_input",
      "provider_method": "tls_certificate_audit",
      "classification": "direct_signal_input",
      "entity_types": ["domain"],
      "gating_logic": "Requires domain list. Only scan user-owned domains.",
      "notes": "TLS cert expiry, self-signed detection."
    },
    {
      "module": "browser_configuration",
      "provider_role": "direct_signal_input",
      "provider_method": "security_header_audit",
      "classification": "direct_signal_input",
      "entity_types": ["domain"],
      "gating_logic": "Same as above.",
      "notes": "Missing HSTS, X-Frame-Options, CSP."
    },
    {
      "module": "infrastructure_exposure",
      "provider_role": "enrichment_only",
      "provider_method": "dns_health_check",
      "classification": "enrichment_only",
      "entity_types": ["domain"],
      "gating_logic": "Same as above.",
      "notes": "DNS-ONLY entries = potential orphaned infrastructure."
    }
  ],
  "signal_contracts": [
    {
      "signal_type": "tls_cert_expired",
      "severity": "high",
      "finding_kind": "true_finding"
    },
    {
      "signal_type": "tls_cert_expiring_soon",
      "severity": "medium",
      "severity_is_conditional": true,
      "finding_kind": "true_finding"
    },
    {
      "signal_type": "tls_self_signed",
      "severity": "medium",
      "finding_kind": "true_finding"
    },
    {
      "signal_type": "missing_security_headers",
      "severity": "low",
      "severity_is_conditional": true,
      "finding_kind": "true_finding"
    },
    {
      "signal_type": "orphaned_dns_entry",
      "severity": "low",
      "finding_kind": "enrichment_finding"
    }
  ],
  "confidence_guidance": [
    {
      "signal_type_or_use_case": "tls_certificate_audit",
      "source_reliability": "High (live cryptographic probe)",
      "freshness_considerations": "High (live at scan time)",
      "corroboration_rules": "None needed — deterministic",
      "calibration_todo": "None"
    }
  ]
}
```
