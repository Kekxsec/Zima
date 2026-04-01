---
title: "Awesome OSINT MCP Servers — Mitigation Stage Reference"
aliases: ["osint mcp servers", "mcp mitigation", "awesome-osint-mcp"]
tags: [zima, research, mitigation, mcp, osint, reference]
type: research_reference
source: https://github.com/soxoj/awesome-osint-mcp-servers
status: reference_only
last_reviewed: 2026-03-23
obsidianUIMode: preview
---

# Awesome OSINT MCP Servers

**Source:** https://github.com/soxoj/awesome-osint-mcp-servers
**Curator:** soxoj (maigret / socid-extractor author)
**Purpose:** Curated list of MCP (Model Context Protocol) servers that expose OSINT tools to LLMs like Claude, Cursor, and Windsurf.

---

## What This Is

MCP servers wrap OSINT tools as structured tools callable by LLM agents. This means an LLM can invoke a Shodan lookup, run a VirusTotal scan, or execute maigret — all through a conversational interface without the user needing CLI knowledge.

**Relevance to Zima:** This collection directly informs Zima's **Mitigation / Active Investigation** stage. When Zima surfaces a finding (e.g. breach detected, suspicious extension, exposed identity), the next question is "what do I do next?" — MCP servers enable deeper investigation through guided, LLM-mediated OSINT without exposing raw CLI complexity to the user.

---

## MCP Servers Listed

### SOCMINT

| Tool | What it does | Already a Zima provider? |
|---|---|---|
| **maigret** | Username search across 3000+ sites; account aggregation | YES — `tools/maigret` (complete) |
| **Xquik** | X/Twitter intelligence: user lookup, follower analysis, account monitoring | No — X/Twitter social provider |

### Network Scanning

| Tool | What it does | Already a Zima provider? |
|---|---|---|
| **Shodan** | IP reconnaissance, DNS ops, vulnerability tracking, device discovery | No — `ip/` category candidate |
| **ZoomEye** | Network asset intelligence, dork-based searches | No — `ip/` category candidate |
| **DNSTwist** | DNS fuzzing for typosquatting / phishing domain detection | YES — `tools/dnstwist` (in vault) |
| **OSINT Toolkit** | Unified recon: WHOIS, Nmap, DNS lookups, typosquatting | Partial — nmap/dnstwist already in vault |

### Other

| Tool | What it does | Already a Zima provider? |
|---|---|---|
| **VirusTotal** | URL, file hash, IP, domain analysis + relationship mapping | YES — `threat_intel/virustotal` (in vault) |

---

## Mitigation Stage Integration Plan

### Concept: "Investigate Further" Flow

When Zima surfaces a finding to a user, a natural next step is guided investigation. MCP servers enable this as an **LLM-mediated investigation layer** — the user can ask "tell me more about this exposure" and the agent invokes the appropriate OSINT tool automatically.

### Recommended Mitigation Integrations

#### 1. Breach Finding → Deeper Identity Investigation
**Finding:** Credential breach detected for `user@email.com`
**MCP flow:**
- → maigret MCP: discover all username accounts linked to this identity
- → socid-extractor: enrich found profiles with platform UIDs and linked accounts
- **Output:** Full identity footprint map shown to user with remediation priority order

#### 2. Suspicious Extension → Threat Verification
**Finding:** Malicious extension ID detected
**MCP flow:**
- → VirusTotal MCP: submit extension hash/ID for multi-engine threat analysis
- **Output:** Confirmed threat classification with removal instructions

#### 3. Domain Exposure → Phishing Risk Check
**Finding:** Email domain exposed in breach or attack surface expanded
**MCP flow:**
- → DNSTwist MCP: discover lookalike/typosquatting domains targeting the user's domain
- → Shodan MCP: check if domain's infrastructure has exposed services
- **Output:** Attack surface expansion report with specific domain threats

#### 4. Network/IP Exposure → Asset Discovery
**Finding:** IP address or infrastructure details exposed
**MCP flow:**
- → Shodan MCP: full IP reconnaissance and vulnerability check
- → ZoomEye MCP: cross-reference with ZoomEye asset index
- **Output:** Infrastructure exposure report with patching priorities

### Implementation Approach Options

**Option A: MCP server integration in Zima backend**
- Zima's LLM-powered "what to do next" advisor uses MCP servers as tools
- User gets conversational deep-dive capability after initial scan
- Requires: MCP server hosting/connectivity, appropriate auth for each tool

**Option B: MCP server reference guide for users**
- Zima's remediation output includes: "To investigate further, connect these MCP servers to Claude"
- Link to setup guides for each relevant MCP server
- Lower engineering lift; higher user friction
- Best for: early-stage Zima where "investigate further" is advanced/power-user territory

**Option C: Zima-native investigation flows (no MCP)**
- Build investigation flows natively using the provider research already in the vault
- Maigret, VirusTotal, Shodan already have/will have provider integrations
- No dependency on MCP protocol; cleaner control over UX
- Best for: controlled Zima product experience

**Recommendation:** Start with Option C (native flows using already-researched providers). Reference Option A for future "Claude-powered investigation" feature once core product is stable.

---

## Providers to Add to Vault (from this list, not yet present)

| Provider | Category | Priority | Notes |
|---|---|---|---|
| **Shodan** | ip/ | P2 | Device/network exposure; strong for infrastructure-exposed identities. API key required. Free tier available. |
| **ZoomEye** | ip/ | P3 | Alternative to Shodan; Chinese-operated (privacy/GDPR considerations). |
| **Xquik (X/Twitter)** | social/ | P3 | X/Twitter intelligence; requires X API access (expensive since 2023). |

---

## Notes

- This list is maintained by soxoj — the same developer behind maigret, socid-extractor, and accounts. His OSINT ecosystem (maigret → socid-extractor → sociallinks-api → MCP servers) represents a coherent investigation pipeline.
- The MCP abstraction is well-suited to Zima's LLM-augmented remediation advisor concept.
- Prioritise native provider integrations first; MCP server integration is a Phase 2 consideration.
