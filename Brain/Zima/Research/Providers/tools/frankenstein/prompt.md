---
title: "prompt / tools / frankenstein"
tags: [zima, research, providers, tools, frankenstein]
type: provider_research_prompt
provider: frankenstein
status: complete
---

# Research Prompt: FRANKENSTEIN

Research FRANKENSTEIN (https://github.com/Ringmast4r/FRANKENSTEIN) as a domain health and security header auditing tool for Zima.

Focus on: DNS probing (A/AAAA, CNAME, MX, NS), HTTP/S probing (status, server, titles, redirects), TLS certificate analysis (expiry, self-signed, issuer), security header audit (HSTS, X-Frame-Options, CSP), SQLite output schema, 50-worker concurrency, Go binary distribution.

Classification target: direct_signal_input (TLS/headers), enrichment_only (DNS health)
Module target: infrastructure_exposure, browser_configuration
Signal targets: tls_cert_expired, tls_cert_expiring_soon, tls_self_signed, missing_security_headers, orphaned_dns_entry
