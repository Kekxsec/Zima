---
title: "wave 0 - anchor and baseline"
tags: [zima, research, providers, launch, wave_0]
type: provider_launch_wave
created: 2026-03-22
updated: 2026-03-22
---

[[./_index|Provider Launch Plan]] · [[../../launch-provider-status-board|Launch Provider Status Board]]

# Wave 0 - Anchor and Baseline

Do these first. They define the launch product, the trust model, and the first signal registry slice.

## Providers

| provider | role | target modules | why now |
|---|---|---|---|
| [[../breach/hibp/hibp|hibp]] | breach anchor | `breach_monitor` | calibrates the identity exposure story |
| [[../social/accounts/accounts|accounts]] | account discovery anchor | `account_inventory` | anchors likely-account inventory |
| [[../tools/osquery/osquery|osquery]] | local inventory anchor | `os_security`, `patch_status`, `software_vulnerability`, browser inventory | strongest broad local evidence collector |
| [[../tools/browser_extension_detector/browser_extension_detector|browser_extension_detector]] | browser extension inventory anchor | `extension_risk` | simplest local browser inventory source |
| [[../tools/get_browser_extension_info/get_browser_extension_info|get_browser_extension_info]] | extension metadata normalization | `extension_risk` | turns extension IDs into usable evidence |

## Definition Of Done

For each provider:

- `prompt.md` is implementation-grade
- `output.md` is complete
- classification is explicit
- target modules are frozen
- auth, rate limit, licensing, and evidence fields are captured

## Immediate Deliverable

Freeze the first launch module set from this wave:

- `breach_monitor`
- `account_inventory`
- `os_security`
- `patch_status`
- `software_vulnerability`
- `extension_risk`
