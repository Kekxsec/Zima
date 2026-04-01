---
title: "pillar / exposure and attack surface"
tags: [zima, research, pillars, exposure_attack_surface]
type: security_pillar_hub
pillar: exposure_attack_surface
obsidianUIMode: preview
---

[[../research|Research]] · [[_index|Security Pillars]]

# exposure and attack surface

## framing

- external exposure, impersonation, monitoring, and hostile-surface discovery
- strong fit for passive OSINT, internet intelligence, and scan-assisted enrichment
- likely the broadest area for provider diversity

## network

- scope: local network posture, router security, WiFi security, and unexpected exposed services
- suggested modules: `router_security`, `wifi_security`, `local_network_scan`, `firmware_version_check`
- provider hubs: [[../Providers/ip/ip|ip]], [[../Providers/reputation/reputation|reputation]], [[../Providers/tools/tools|tools]]

## domain

- scope: DNS security, reputation, certificates, DMARC/SPF/DKIM, and subdomain exposure
- suggested modules: `dns_security`, `tls_configuration`, `domain_reputation`, `dmarc_spf_dkim`, `subdomain_enumeration`, `certificate_monitor`
- provider hubs: [[../Providers/domain/domain|domain]], [[../Providers/reputation/reputation|reputation]], [[../Providers/threat_intel/threat_intel|threat_intel]], [[../Providers/tools/tools|tools]]

## email

- scope: mailbox rules, forwarding, phishing exposure, and email security configuration
- suggested modules: `mailbox_security`, `phishing_detection`, `forwarding_rule_check`, `email_security_config`
- provider hubs: [[../Providers/social/social|social]], [[../Providers/domain/domain|domain]], [[../Providers/reputation/reputation|reputation]], [[../Providers/threat_intel/threat_intel|threat_intel]], [[../Providers/cloud/cloud|cloud]]

## infrastructure

- scope: internet-facing assets, exposed services, banners, and vulnerable remote software
- suggested modules: `exposed_services`, `port_scanning`, `service_banner_analysis`, `cve_correlation`
- provider hubs: [[../Providers/ip/ip|ip]], [[../Providers/reputation/reputation|reputation]], [[../Providers/threat_intel/threat_intel|threat_intel]], [[../Providers/domain/domain|domain]], [[../Providers/tools/tools|tools]]

## privacy

- scope: people-search exposure, data broker exposure, and public oversharing of personal information
- suggested modules: `data_broker_exposure`, `public_profile_scan`, `people_search_exposure`
- provider hubs: [[../Providers/social/social|social]], [[../Providers/phone/phone|phone]], [[../Providers/search/search|search]]

## darkweb

- scope: dark web mentions, credential dumps, marketplace exposure, and threat-actor references tied to identities or organizations
- suggested modules: `darkweb_identity_monitor`, `credential_dump_monitor`, `threat_actor_mentions`
- provider hubs: [[../Providers/darkweb/darkweb|darkweb]], [[../Providers/breach/breach|breach]], [[../Providers/social/social|social]]

## threat_intel

- scope: malicious infrastructure, IOC matches, phishing feeds, and emerging threat monitoring
- suggested modules: `phishing_feed_monitor`, `malware_ioc_monitor`, `emerging_threats`, `domain_ioc_match`
- provider hubs: [[../Providers/threat_intel/threat_intel|threat_intel]], [[../Providers/reputation/reputation|reputation]], [[../Providers/domain/domain|domain]], [[../Providers/ip/ip|ip]], [[../Providers/search/search|search]]
