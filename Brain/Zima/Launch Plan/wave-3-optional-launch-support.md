---
title: "wave 3 - optional launch support"
tags: [zima, research, providers, launch, wave_3]
type: provider_launch_wave
created: 2026-03-22
updated: 2026-03-22
---

[[./_index|Provider Launch Plan]] · [[../../launch-provider-status-board|Launch Provider Status Board]]

# Wave 3 - Optional Launch Support

Only do this wave after Waves 0-2 are materially complete.

## Phone Enrichment

| provider | role | target modules |
|---|---|---|
| [[../phone/truecaller/truecaller|truecaller]] | caller context enrichment | `phone_exposure` |
| [[../phone/numverify/numverify|numverify]] | carrier and line-type enrichment | `phone_exposure` |
| [[../phone/callername/callername|callername]] | caller-name enrichment | `phone_exposure` |

## Dark-Web Support

| provider | role | target modules |
|---|---|---|
| [[../darkweb/ahmia/ahmia|ahmia]] | dark-web mention support | `darkweb_identity_monitor` |
| [[../darkweb/darksearch/darksearch|darksearch]] | dark-web mention support | `darkweb_identity_monitor` |

## Extension Store Metadata Support

| provider | role | target modules |
|---|---|---|
| [[../cloud/chrome_web_store_api/chrome_web_store_api|chrome_web_store_api]] | Chrome extension metadata enrichment | `extension_risk` |
| [[../cloud/firefox_addons_site_api/firefox_addons_site_api|firefox_addons_site_api]] | Firefox extension metadata enrichment | `extension_risk` |

## Password Manager Export — Additional Targets

Add after Bitwarden and Proton Pass exporters are stable. These formats are more complex or serve smaller segments of Zima's target audience.

| module | role | target output |
|---|---|---|
| `pm_exporter_1password` | 1Password import package (CSV + JSON) | `account_onboarding` |

**Format notes:**
- 1Password has two import paths: CSV (limited fields) and `.1pux` JSON (full-fidelity, preferred)
- `.1pux` is a zip archive containing `export.data` JSON — more work than Bitwarden but covers all fields

## Email Alias — Additional Providers

Add if SimpleLogin or Addy.io have adoption gaps. Only pull in if there is a clear user need.

| provider | role | target modules |
|---|---|---|
| custom domain aliasing | per-service aliasing via user's own domain | `alias_management` |

**Note:** custom domain support requires DNS management capability or user-managed DNS. Scope carefully — this is more infrastructure surface than a provider integration.

## Working Rule

This wave should not delay launch. Use it to improve confidence, polish, and optional exposure coverage.
