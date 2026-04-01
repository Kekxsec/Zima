---
title: "wave 2 - hardening and enrichment"
tags: [zima, research, providers, launch, wave_2]
type: provider_launch_wave
created: 2026-03-22
updated: 2026-03-22
---

[[./_index|Provider Launch Plan]] · [[../../launch-provider-status-board|Launch Provider Status Board]]

# Wave 2 - Hardening and Enrichment

These providers make the launch audit more complete and actionable, but they are not first blockers.

## Device Hardening

| provider | role | target modules |
|---|---|---|
| [[../tools/lynis/lynis|lynis]] | host hardening evidence | `os_security`, `firewall_status` |
| [[../tools/trivy/trivy|trivy]] | software vulnerability evidence | `software_vulnerability` |
| [[../tools/grype/grype|grype]] | software vulnerability evidence | `software_vulnerability` |
| [[../tools/syft/syft|syft]] | inventory and SBOM support | `software_inventory` |

## Browser Configuration and Enrichment

| provider | role | target modules |
|---|---|---|
| [[../tools/chromium_enterprise_policies/chromium_enterprise_policies|chromium_enterprise_policies]] | browser policy evidence | `browser_configuration` |
| [[../tools/firefox_enterprise_policies/firefox_enterprise_policies|firefox_enterprise_policies]] | browser policy evidence | `browser_configuration` |
| [[../threat_intel/crxcavator/crxcavator|crxcavator]] | extension risk enrichment | `extension_risk` |

## Identity and Privacy Enrichment

| provider | role | target modules |
|---|---|---|
| [[../social/emailformat/emailformat|emailformat]] | alias support | `alias_correlation` |
| [[../social/gravatar/gravatar|gravatar]] | public profile enrichment | `public_profile_scan` |
| [[../social/skymem/skymem|skymem]] | public email exposure support | `username_exposure` |
| [[../social/emailcrawlr/emailcrawlr|emailcrawlr]] | public email mention support | `username_exposure` |

## Working Rule

Treat most of this wave as `enrichment_only` unless the evidence clearly justifies a user-facing finding.
