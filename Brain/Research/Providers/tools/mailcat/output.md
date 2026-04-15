---
title: "output / tools / mailcat"
aliases: ["mailcat output", "mailcat signal registry"]
tags: [zima, research, outputs, signal-registry, tools, mailcat]
type: provider_research_output
provider: mailcat
provider_category: tools
status: complete
prompt_note: prompt.md
provider_folder: mailcat.md
obsidianUIMode: preview
kind: reference
llm_include: true
code_scope: backend
---

# mailcat (Username → Email Address Finder)

**Source:** https://github.com/sharsil/mailcat
**Author:** sharsil
**Language:** Python
**Install:** `pip3 install mailcat` (or clone + run `./mailcat.py`)

mailcat discovers **existing email addresses** for a given username across 37+ email providers, covering 170+ domains and 100+ aliases. It operates **without notifying the target** — checks are passive (SMTP verification, registration probes, account recovery flows). This is the **inverse of holehe**: holehe takes an email and finds services the email is registered on; mailcat takes a username and finds which email addresses exist using that username pattern.

**Strategic value for Zima:** Closes the gap left by the `accounts` (soxoj) tool being unavailable. Given a username (from maigret/whatsmyname), mailcat surfaces associated email addresses. Those email addresses then feed the breach lookup chain (HIBP, LeakCheck, DeHashed).

---

## A. Tool/API Surface Appendix

### CLI Interface

```bash
./mailcat.py username
# Examples:
./mailcat.py johndoe
./mailcat.py johndoe --tor
./mailcat.py johndoe --proxy http://127.0.0.1:8080
./mailcat.py johndoe -m 20   # max 20 concurrent connections
```

**Positional arg:** `username` — the username to search for across email providers.

**Options:**
| Flag | Description |
|---|---|
| `--tor` | Route all checks through Tor |
| `--proxy http://IP:PORT` | Use a specific HTTP proxy |
| `-m` / `--max-connections` | Max concurrent connections (default: 10) |

### Detection Methods

mailcat uses a combination of techniques per provider:

| Method | Description | Notes |
|---|---|---|
| SMTP verification | Connects to mail server, probes if address exists | Low noise, no notification |
| API checking | Uses provider's public API (e.g. password reset) | Provider-specific |
| Registration validation | Submits registration form with email, checks response | May have side effects on some providers |
| Account recovery | Checks if recovery flow acknowledges the address | Most silent method |

**No user notification by design** — the README explicitly states "without user notification."

### Supported Providers (37+ services, 170+ domains)

Major services covered:

| Category | Services |
|---|---|
| Global | Gmail, Outlook, Yahoo, iCloud, ProtonMail |
| Russian | Yandex, Mail.Ru |
| European | Posteo, Tutanota, Fastmail |
| Polish | wp.pl, onet.pl, interia.pl |
| Regional | Various country-specific providers |

Full domain list: 170+ including aliases (e.g. googlemail.com for gmail.com).

### Output Schema

Output is printed to stdout. Format is text-based (not structured JSON by default).

Per-provider result states (inferred from OSINT cli tool skeleton pattern, consistent with soxoj ecosystem):

| State | Indicator | Meaning |
|---|---|---|
| Hit | `[+]` | Email address exists at this provider |
| No hit | `[-]` | Email address does not exist |
| Rate limited | `[x]` | Provider rate-limited this check |
| Error | `[!]` | Check failed (network, provider change, etc.) |

**Hit output:** When an email is found (`[+]`), the output includes the discovered email address (e.g. `johndoe@gmail.com`).

**Note:** No official JSON output mode documented. Zima integration should either:
1. Parse stdout for `[+]` lines and extract the discovered email addresses, or
2. Contribute a `--json` flag to the project if needed.

### Concurrency and Rate Limits

- Default: 10 concurrent connections
- User-configurable via `-m` flag
- No built-in delay controls beyond connection pooling
- Zima should run at low concurrency (5–10 max) to avoid provider blocks

### Privilege Requirements

None — standard HTTP/SMTP network access only.

### Installation

```bash
git clone https://github.com/sharsil/mailcat
cd mailcat
pip install -r requirements.txt
./mailcat.py username
```

---

## Module Mapping Table

| module | provider_role | provider_method | endpoint_or_artifact | classification | entity_types | gating_logic | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|
| account_inventory | direct_signal_input | username_to_email_discovery | SMTP/API checks per email provider | direct_signal_input | username | Requires a username as input. Gate on username being provided by user or derived from maigret/whatsmyname output. Run once per unique username. | github.com/sharsil/mailcat README | Discovered email addresses are first-class findings — feed directly into breach lookup chain. |
| identity_exposure | enrichment_only | username_to_email_discovery | SMTP/API checks per email provider | enrichment_only | username | Same as above. | github.com/sharsil/mailcat README | Enriches identity graph: username → email addresses. Email addresses then chain to breach providers. |

---

## Signal Contract Table

| module | source | provider | provider_method | signal_type | category | severity | severity_is_conditional | conditional_rule | entity_type | finding_kind | trigger_condition | evidence_fields | enrichment_fields | summary_template | evidence_status | citation_refs | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| account_inventory | account_inventory | mailcat | username_to_email_discovery | `email_address_discovered` | identity_exposure | low | yes | Escalate to medium if discovered email subsequently found in breach (via HIBP/LeakCheck). | username | enrichment_finding | `result.state == "hit"` (stdout `[+]` line) | `username`, `discovered_email`, `provider_domain` | `breach_found` (from downstream HIBP/LeakCheck lookup) | "Email address {discovered_email} found for username {username}." | inferred (stdout parsing) | github.com/sharsil/mailcat README | Signal severity on its own is low — email existence is not a finding. Severity elevates when the email appears in a breach. |

### Signal Design Notes

- **`email_address_discovered`** is a **precursor signal**, not a standalone security finding. Email addresses found by mailcat become inputs to the breach lookup chain.
- The real value is: `username → mailcat → email addresses → HIBP/LeakCheck → breach_found`
- Do not surface `email_address_discovered` to the user on its own. Surface it only when:
  1. It is a newly identified email not already in the user's identity inventory, AND
  2. It subsequently triggers a breach finding
- Alternatively, surface it as a low-severity "identity footprint" enrichment item in an account inventory screen.

---

## Confidence Guidance

| module | signal_type_or_use_case | source_reliability | freshness_considerations | corroboration_rules | calibration_todo |
|---|---|---|---|---|---|
| account_inventory | email_address_discovered | Medium: SMTP and API checks are technically reliable but provider behaviour changes. False positives possible if SMTP server has catch-all configuration. False negatives if provider uses CAPTCHA or blocks probes. | High (live check at scan time). | Confirm discovered emails via breach lookup (HIBP/LeakCheck). A discovered email that also appears in a breach is high-confidence identity data. | Monitor per-provider false positive rate. Catch-all SMTP servers return hits for all addresses (e.g. some corporate domains). Add domain-level exclusion list for known catch-alls. |

---

## Provider Summary

### Strongest Use Cases

- **Username → email address discovery**: Given a username (from user onboarding or maigret discovery), surfaces associated email addresses across major providers.
- **Closing the identity chain**: Enables `username → email → breach` pipeline without the user needing to enumerate all their email addresses manually.
- **Non-invasive**: Passive checks only; does not notify the target.

### What Not To Use It For

- Do not treat discovered email addresses as confirmed breach findings — they require downstream breach lookup.
- Do not run at high concurrency — SMTP probing at scale triggers provider blocks.
- Do not rely on SMTP-based results for catch-all domains (corporate and some personal domains accept all addresses).

### Implementation Cautions

- **Output parsing:** No JSON mode documented. Stdout parsing required. Pin to a specific version to avoid parsing breakage.
- **SMTP catch-all risk:** Some mail servers return success for all email addresses regardless of existence. Add a blocklist of known catch-all domains.
- **Side effects:** Registration-flow checks may create partial registration state on some providers. Monitor which providers use this method and whether Zima's ToS permits it.
- **Tor support:** Available if privacy routing is needed for the scanning infrastructure.
- **License:** Not explicitly stated in repo — check before commercial use.

### Current Zima Stage Fit

- **Phase:** Identity discovery layer — runs after username collection, before breach lookup
- **Module:** `account_inventory` (direct signal input for email discovery), `identity_exposure` (enrichment)
- **Classification:** `direct_signal_input` for email discovery; feeds into breach lookup as enrichment
- **Pipeline position:** `username (user-provided or from maigret)` → mailcat → `discovered email addresses` → HIBP/LeakCheck/DeHashed

---

# Structured JSON

```json
{
  "provider": "mailcat",
  "provider_category": "tools",
  "provider_role": "direct_signal_input",
  "source": "https://github.com/sharsil/mailcat",
  "requires_api_key": false,
  "requires_network": true,
  "install": "git clone https://github.com/sharsil/mailcat && pip install -r requirements.txt",
  "coverage": "37+ email providers, 170+ domains, 100+ aliases",
  "detection_methods": ["smtp_verification", "api_checking", "registration_validation", "account_recovery"],
  "no_user_notification": true,
  "module_mappings": [
    {
      "module": "account_inventory",
      "provider_role": "direct_signal_input",
      "provider_method": "username_to_email_discovery",
      "endpoint_or_artifact": "SMTP/API checks per email provider",
      "classification": "direct_signal_input",
      "entity_types": ["username"],
      "gating_logic": "Requires username input; run once per unique username",
      "notes": "Discovered emails feed breach lookup chain"
    }
  ],
  "signal_contracts": [
    {
      "module": "account_inventory",
      "provider": "mailcat",
      "provider_method": "username_to_email_discovery",
      "signal_type": "email_address_discovered",
      "category": "identity_exposure",
      "severity": "low",
      "severity_is_conditional": true,
      "conditional_rule": "Escalate to medium if discovered email found in breach (HIBP/LeakCheck)",
      "entity_type": "username",
      "finding_kind": "enrichment_finding",
      "trigger_condition": "result.state == hit",
      "evidence_fields": ["username", "discovered_email", "provider_domain"],
      "summary_template": "Email address {discovered_email} found for username {username}.",
      "evidence_status": "inferred"
    }
  ],
  "confidence_guidance": [
    {
      "module": "account_inventory",
      "signal_type_or_use_case": "email_address_discovered",
      "source_reliability": "Medium (SMTP/API probing; catch-all domains are false positive risk)",
      "freshness_considerations": "High (live check)",
      "corroboration_rules": "Confirm via breach lookup; email in breach = high confidence identity data",
      "calibration_todo": "Build catch-all domain blocklist; monitor per-provider accuracy"
    }
  ]
}
```
