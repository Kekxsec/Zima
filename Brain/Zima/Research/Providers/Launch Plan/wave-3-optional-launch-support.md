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

## Working Rule

This wave should not delay launch. Use it to improve confidence, polish, and optional exposure coverage.
