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

## Email Account Identifier — Pipeline Features

These features run inside the email account identifier pipeline. They improve account discovery quality and extend it into remediative territory.

### Newsletter and Subscription Detection

Not an external provider. A pipeline stage that runs before the account classifier, stripping noise from the inbox signal.

| module | role | signals used |
|---|---|---|
| `newsletter_detection` | classify and triage newsletters, mailing lists, and promotional subscriptions | `List-Unsubscribe`, `List-ID`, bulk-mail header patterns, known ESP domains, sender frequency, absence of account/security semantics |

**Output:** a review queue showing sender/service name, message volume, last seen date, unsubscribe availability, confidence level, and recommended action.

**Design rule:** review workflow only. No silent automated unsubscribes. The user approves every action.

**Sequencing constraint:** build after the mbox parser phase is complete. Runs as a pre-pass before account classification so noise is removed before the account inventory is built.

### Email Alias Integration

Action providers that create per-service email aliases after account discovery is complete. Sit in the remediation layer — Zima proposes, the user approves, the provider creates.

| provider | role | target modules |
|---|---|---|
| [[../privacy/simplelogin/simplelogin\|simplelogin]] | per-service alias creation and management | `alias_management` |
| [[../privacy/addy_io/addy_io\|addy.io]] | per-service alias creation and management | `alias_management` |

**Alias flow:**
1. Zima identifies a confirmed service from `account_inventory`
2. Zima proposes an alias (naming pattern, domain selection)
3. User approves
4. Zima creates the alias via provider API and stores the `service → alias` mapping
5. Alias is inserted into the password-manager export for that service

**Feature flags required:** per-user provider API key storage, alias naming pattern config, custom domain support.

**Sequencing constraint:** depends on `account_inventory` reaching sufficient confidence. Do not build until newsletter detection has been running and account discovery noise is reduced.

## Working Rule

Treat most of this wave as `enrichment_only` unless the evidence clearly justifies a user-facing finding.
