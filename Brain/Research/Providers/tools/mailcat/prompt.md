---
title: "prompt / tools / mailcat"
tags: [zima, research, providers, tools, mailcat]
type: provider_research_prompt
provider: mailcat
status: complete
kind: artifact
llm_include: false
code_scope: backend
---

# Research Prompt: mailcat

Research the mailcat tool (https://github.com/sharsil/mailcat) as a username-to-email discovery provider for Zima.

Focus on:
1. CLI interface — all flags, options, output format
2. Detection methods per provider (SMTP, API, registration, recovery)
3. Full list of supported email providers and domains (170+)
4. Output schema — how hits vs no-hits are reported; JSON mode availability
5. False positive risks (catch-all SMTP servers)
6. Side effects (registration flow probes — do they leave traces?)
7. Integration position: username → mailcat → discovered emails → breach lookup chain
8. License terms

Classification target: direct_signal_input (email discovery), enrichment_only (feeds breach chain)
Module target: account_inventory
Signal target: email_address_discovered (precursor, low severity on own — escalates via breach lookup)
