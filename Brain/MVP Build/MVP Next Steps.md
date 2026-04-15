---
tags: [zima, status, next-steps]
created: 2026-03-21
updated: 2026-04-15
status: archived_reference
---

← [[../Zima|Zima]] · [[../next-steps-to-launch|Current Launch Note]]

# Next Steps

*Historical planning note preserved for archive links. The active launch tracker now lives in [[../next-steps-to-launch]].*

---

## Launch Direction (updated 2026-03-23)

The launch product is a **one-and-done paid personal security audit**, not an ongoing monitoring subscription. See [[launch-execution-guide]] for the comprehensive build plan.

---

## Current Focus (2026-03-23)

### 1. Provider Research (In Progress)

Complete `output.md` for all launch providers (~25 providers across 4 rounds). This is the blocker for everything else.

- Round 1 (scan loop anchors): `hibp`, `accounts`, `osquery`, `browser_extension_detector`, `get_browser_extension_info`
- Round 2 (enrichment): `dehashed`, `leakcheck`, `breachdirectory`, `emailrep`, `epieos`, `holehe`, `maigret`, `whatsmyname`
- Round 3 (audit completion): `posture`, `macos_native`, `windows_native`, `linux_native`, `malicious_extension_sentry`, `hudson_rock`
- Round 4 (hardening depth): `chromium_enterprise_policies`, `firefox_enterprise_policies`, `crxcavator`, `lynis`, `trivy`, `grype`

Track progress at: [[../Research/launch-research-dashboard|Launch Research Dashboard]]

### 2. Signal Registry Synthesis

After research: collect signal rows -> deduplicate -> assign module ownership -> freeze severity -> write canonical `signal-registry.md`.

See: [[pre-stage-06-signal-registry-handoff]]

### 3. Stage 6: Scan Engine Build

After signal registry is frozen: provider clients -> module rules/mappers -> ScanOrchestrator -> API endpoints -> correlation -> scoring -> remediation playbooks.

### 4. Mbox Scanner + Account-Identify Integration

After Stage 6 core: local mbox parser -> message classifier -> service resolver -> merge with passive discovery -> breach cross-reference -> guided reset flow -> password manager export.

Repo to absorb: `Kekxsec/Account-Identify`

### 5. Browser Hardening + Tool Recommendations

Remediation content (no code dependency): DNS-over-HTTPS setup, HTTPS-only mode, recommended extensions, recommended browser, tool recommendations (Bitwarden, Ente Auth, Quad9, etc.)

---

## Remaining MVP Stages

| Stage | What | Gate |
|---|---|---|
| 06 | Scan engine + API | Signal registry frozen |
| Mbox + Account-Identify | Account discovery + PM migration | Stage 6 core working |
| 07 | Stripe one-time payment + GDPR | Stage 6 done |
| 08 | Pre-launch hardening | Stage 7 done - **must pass before real users** |

Stage 06b (breach alerts) is **deferred past launch** - one-time audit doesn't need ongoing alerts.

---

## Open Questions / Decisions

- [ ] Signal registry: synthesize canonical registry from provider research outputs
- [ ] Signal registry: finalize severity rules for conditional providers
- [ ] Signal registry: define provisional confidence policy for implementation
- [ ] Mbox scanner architecture: client-side (in Account-Identify) vs backend component
- [ ] Frontend tech: confirm Next.js or alternative for the scan results UI
- [ ] Pricing: confirm one-time audit price point
- [ ] Landing page: when to build (before or after Stage 8?)

---

## Code Quality State (2026-03-21)

| Check | Status |
|---|---|
| mypy (614 source files) | ✅ 0 errors |
| ruff | ✅ clean |
| import checker | ✅ passing |
| Tests | ✅ 17/17 (Stage 5 scope) |

---

## See Also

- [[launch-execution-guide]] - comprehensive launch build plan
- [[MVP Master]] - full stage status
- [[MVP - Road to Launch]] - post-launch roadmap
- [[pre-stage-06-signal-registry-handoff]] - detailed bridge from research to Stage 6
- [[../Architecture/Design Principles]] - rules to stay within
- [[../Research/Signal Research Guide|Signal Research Guide]] - signal registry research process
