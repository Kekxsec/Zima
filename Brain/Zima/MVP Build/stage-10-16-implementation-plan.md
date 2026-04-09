Two providers need updating:
  - epieos → DEFERRED — no public API, ToS prohibits automation, enterprise contract required. Remove from
  registry.
  - accounts (soxoj) → DEFERRED — GitHub repo 404. Replaced by mailcat + holehe + maigret pipeline.

  ---
  Full Confirmed Provider Scope at Launch

  Identity Pillar — P0/P1

  ┌────────────────┬────────────────────────────────┬─────────────────────────┬─────────┬──────────────┐
  │    Provider    │              Path              │         Module          │ Priorit │    Status    │
  │                │                                │                         │    y    │              │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │                │                                │                         │         │ client done, │
  │ hibp           │ providers/breach/hibp          │ breach_monitor          │ P0      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │                │                                │ breach_monitor,         │         │ client done, │
  │ dehashed       │ providers/breach/dehashed      │ credential_exposure     │ P0      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │                │                                │                         │         │ client done, │
  │ leakcheck      │ providers/breach/leakcheck     │ credential_exposure     │ P0      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ breachdirector │ providers/breach/breachdirecto │                         │         │ client done, │
  │ y              │ ry                             │ breach_monitor          │ P1      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │                │                                │                         │         │ client done, │
  │ hudson_rock    │ providers/breach/hudson_rock   │ stealer_log_exposure    │ P1      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │                │                                │ account_enumeration_ris │         │ client done, │
  │ emailrep       │ providers/reputation/emailrep  │ k                       │ P1      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │                │                                │ account_inventory, acco │         │ client done, │
  │ holehe         │ providers/tools/holehe         │ unt_enumeration_risk    │ P1      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │                │                                │                         │         │ client done, │
  │ maigret        │ providers/tools/maigret        │ username_exposure       │ P1      │  no schema/m │
  │                │                                │                         │         │ apper        │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ mailcat        │ providers/tools/mailcat        │ account_inventory       │ P1      │ not          │
  │                │                                │                         │         │ implemented  │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ whatsmyname    │ providers/tools/whatsmyname    │ account_inventory,      │ P1      │ not          │
  │                │                                │ alias_correlation       │         │ implemented  │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ intelx         │ providers/threat_intel/intelx  │ breach_monitor, darkweb │ P1      │ client stub  │
  │                │                                │ _identity_monitor       │         │ only         │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ socid_extracto │ providers/tools/socid_extracto │ username_exposure,      │         │ not          │
  │ r              │ r                              │ account_inventory       │ P2      │ implemented  │
  │                │                                │ (enrichment)            │         │              │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ emailformat    │ providers/social/emailformat   │ alias_correlation       │ P2      │ client stub  │
  │                │                                │                         │         │ only         │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ gravatar       │ providers/social/gravatar      │ public_profile_scan     │ P2      │ client stub  │
  │                │                                │                         │         │ only         │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ skymem         │ providers/social/skymem        │ username_exposure       │ P2      │ client stub  │
  │                │                                │                         │         │ only         │
  ├────────────────┼────────────────────────────────┼─────────────────────────┼─────────┼──────────────┤
  │ emailcrawlr    │ providers/social/emailcrawlr   │ username_exposure       │ P2      │ client stub  │
  │                │                                │                         │         │ only         │
  └────────────────┴────────────────────────────────┴─────────────────────────┴─────────┴──────────────┘

  Identity Pillar — Optional at Launch (P2/P3)

  ┌────────────┬──────────────────────────────┬──────────────────────────┬──────────┐
  │  Provider  │             Path             │          Module          │ Priority │
  ├────────────┼──────────────────────────────┼──────────────────────────┼──────────┤
  │ numverify  │ providers/phone/numverify    │ phone_exposure           │ P2       │
  ├────────────┼──────────────────────────────┼──────────────────────────┼──────────┤
  │ truecaller │ providers/phone/truecaller   │ phone_exposure           │ P2       │
  ├────────────┼──────────────────────────────┼──────────────────────────┼──────────┤
  │ callername │ providers/phone/callername   │ phone_exposure           │ P2       │
  ├────────────┼──────────────────────────────┼──────────────────────────┼──────────┤
  │ ahmia      │ providers/darkweb/ahmia      │ darkweb_identity_monitor │ P3       │
  ├────────────┼──────────────────────────────┼──────────────────────────┼──────────┤
  │ darksearch │ providers/darkweb/darksearch │ darkweb_identity_monitor │ P3       │
  └────────────┴──────────────────────────────┴──────────────────────────┴──────────┘

  ---
  Device Pillar — P0 (local subprocess, agent-dependent)

  ┌───────────────────┬──────────────────────────────────┬──────────────────────┬─────────┬────────────┐
  │     Provider      │               Path               │        Module        │ Priorit │   Status   │
  │                   │                                  │                      │    y    │            │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │                   │                                  │ os_security,         │         │ not implem │
  │ osquery           │ providers/tools/osquery          │ patch_status, softwa │ P0      │ ented      │
  │                   │                                  │ re_vulnerability     │         │            │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ posture           │ providers/tools/posture          │ device baseline      │ P0      │ not implem │
  │                   │                                  │                      │         │ ented      │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ macos_native      │ providers/tools/macos_native     │ device baseline      │ P0      │ not implem │
  │                   │                                  │                      │         │ ented      │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ windows_native    │ providers/tools/windows_native   │ device baseline      │ P0      │ not implem │
  │                   │                                  │                      │         │ ented      │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ linux_native      │ providers/tools/linux_native     │ device baseline      │ P0      │ not implem │
  │                   │                                  │                      │         │ ented      │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ lynis             │ providers/tools/lynis            │ os_security,         │ P1      │ not implem │
  │                   │                                  │ firewall_status      │         │ ented      │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ trivy             │ providers/tools/trivy            │ software_vulnerabili │ P1      │ not implem │
  │                   │                                  │ ty                   │         │ ented      │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ grype             │ providers/tools/grype            │ software_vulnerabili │ P1      │ not implem │
  │                   │                                  │ ty                   │         │ ented      │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ oui_master_databa │ providers/tools/oui_master_datab │ device_inventory     │ P2      │ research   │
  │ se                │ ase                              │ (offline enrichment) │         │ complete   │
  ├───────────────────┼──────────────────────────────────┼──────────────────────┼─────────┼────────────┤
  │ syft              │ providers/tools/syft             │ software_inventory   │ P2      │ not implem │
  │                   │                                  │                      │         │ ented      │
  └───────────────────┴──────────────────────────────────┴──────────────────────┴─────────┴────────────┘

  ---
  Browser Pillar — P0 (local collector-dependent)

  ┌────────────────────────┬────────────────────────────────────┬──────────────────┬────────┬──────────┐
  │        Provider        │                Path                │      Module      │ Priori │  Status  │
  │                        │                                    │                  │   ty   │          │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │ browser_extension_dete │ providers/tools/browser_extension_ │ extension_risk   │ P0     │ not impl │
  │ ctor                   │ detector                           │                  │        │ emented  │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │ get_browser_extension_ │ providers/tools/get_browser_extens │ extension_risk   │ P0     │ not impl │
  │ info                   │ ion_info                           │                  │        │ emented  │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │ malicious_extension_se │ providers/tools/malicious_extensio │ extension_risk   │ P0     │ not impl │
  │ ntry                   │ n_sentry                           │                  │        │ emented  │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │ chromium_enterprise_po │ providers/tools/chromium_enterpris │ browser_configur │ P1     │ not impl │
  │ licies                 │ e_policies                         │ ation            │        │ emented  │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │ firefox_enterprise_pol │ providers/tools/firefox_enterprise │ browser_configur │ P1     │ not impl │
  │ icies                  │ _policies                          │ ation            │        │ emented  │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │                        │                                    │                  │        │ client   │
  │ crxcavator             │ providers/threat_intel/crxcavator  │ extension_risk   │ P1     │ stub     │
  │                        │                                    │                  │        │ only     │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │ chrome_web_store_api   │ providers/cloud/chrome_web_store_a │ extension_risk   │ P2     │ not impl │
  │                        │ pi                                 │                  │        │ emented  │
  ├────────────────────────┼────────────────────────────────────┼──────────────────┼────────┼──────────┤
  │ firefox_addons_site_ap │ providers/cloud/firefox_addons_sit │ extension_risk   │ P2     │ not impl │
  │ i                      │ e_api                              │                  │        │ emented  │
  └────────────────────────┴────────────────────────────────────┴──────────────────┴────────┴──────────┘

  ---
  Infrastructure (Wave 2 — researched, selective)

  ┌──────────────┬───────────────────────────────┬───────────────────────────────┬──────────┬────────────┐
  │   Provider   │             Path              │            Module             │ Priority │   Status   │
  ├──────────────┼───────────────────────────────┼───────────────────────────────┼──────────┼────────────┤
  │ leakix       │ providers/threat_intel/leakix │ infrastructure_exposure       │ Wave 2   │ research   │
  │              │                               │                               │          │ complete   │
  ├──────────────┼───────────────────────────────┼───────────────────────────────┼──────────┼────────────┤
  │ frankenstein │ providers/tools/frankenstein  │ infrastructure_exposure,      │ Wave 2   │ research   │
  │              │                               │ browser_configuration         │          │ complete   │
  └──────────────┴───────────────────────────────┴───────────────────────────────┴──────────┴────────────┘

  ---
  Post-Launch / Enterprise

  ┌───────────────┬───────────────────────────────────────────────────────────────────────────────────────┐
  │   Provider    │                                         Notes                                         │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
  │ sociallinks   │ Commercial identity graph, 500+ sources — requires trial contract                     │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
  │ huginn_muninn │ DHCP fingerprint DB, 11M records — unique value but P3                                │
  ├───────────────┼───────────────────────────────────────────────────────────────────────────────────────┤
  │ twilio        │ Currently in registry but research places it post-OTP-only scope — clarify if keeping │
  │               │  for phone enrichment or removing                                                     │
  └───────────────┴───────────────────────────────────────────────────────────────────────────────────────┘

  ---
  Revised Staged Implementation Plan

  Stage 10 — Complete the Identity Provider Layer

  10a — Breach providers schema/mapper (HIBP, DeHashed, LeakCheck, HudsonRock, BreachDirectory)
  - Introduce ProviderFinding typed dataclass in base/models.py
  - schemas.py + mapper.py for each
  - Fix async bug in Numverify + Twilio

  10b — Social/reputation schema/mapper (EmailRep, EmailFormat, Gravatar, Skymem, EmailCrawlr)
  - Promote EmailFormat, Gravatar, Skymem, EmailCrawlr to registry
  - schemas.py + mapper.py for each

  10c — IntelX client + schema/mapper
  - Full client implementation (has official Python SDK)
  - Add to registry

  10d — New subprocess tools (Mailcat, WhatsmyName, SocidExtractor)
  - Full client implementations
  - schemas.py + mapper.py
  - Add to registry

  ---
  Stage 11 — Identity Module Signal Rules

  11a — breach_monitor mapper/rules/schemas (empty stubs — implement now)
  11b — credential_exposure rules/mapper
  11c — stealer_log_exposure rules/mapper (HudsonRock)
  11d — account_enumeration_risk rules/mapper (EmailRep + Holehe)
  11e — account_inventory rules/mapper (Holehe + Mailcat + WhatsmyName)
  11f — username_exposure rules/mapper (Maigret + SocidExtractor + Skymem)
  11g — alias_correlation rules/mapper (EmailFormat + WhatsmyName)
  11h — phone_exposure rules/mapper (Numverify + Truecaller + CallerName)
  11i — darkweb_identity_monitor module (new — IntelX)
  11j — public_profile_scan module (new — Gravatar + EmailCrawlr)

  ---
  Stage 12 — Device Pillar

  12a — Device provider clients: osquery, posture, macos_native, windows_native, linux_native
  12b — Device provider clients: lynis, trivy, grype, syft, oui_master_database
  12c — Device modules: os_security, patch_status, software_vulnerability, firewall_status
  12d — Device module: device_inventory (offline, uses OUI master DB)

  ---
  Stage 13 — Browser Pillar

  13a — Browser provider clients: browser_extension_detector, get_browser_extension_info,
  malicious_extension_sentry
  13b — Browser provider clients: chromium_enterprise_policies, firefox_enterprise_policies, crxcavator,
  chrome_web_store_api, firefox_addons_site_api
  13c — Browser modules: extension_risk, browser_configuration

  ---
  Stage 14 — File Upload Parsers

  14a — mbox parser improvements (richer metadata, dedup)
  14b — Password manager parsers: 1Password, Bitwarden, LastPass, Dashlane, Keeper, NordPass, generic CSV
  14c — Upload API endpoint (POST /api/v1/assets/import)

  ---
  Stage 15 — Infrastructure (Wave 2, selective)

  15a — LeakIX client + schema/mapper + infrastructure_exposure module
  15b — Frankenstein client + schema/mapper

  ---
  Stage 16 — Integration & Wiring

  - Remove epieos from registry (deferred)
  - Clarify/remove twilio scope
  - Orchestrator updated to use ProviderFinding types throughout
  - Policy evaluate_provider_policy() enforced at orchestrator level for all providers
  - End-to-end scan test for each pillar

  ---
  One question before I start Stage 10: Should twilio stay in the registry for phone enrichment (lookup
  carrier/line type on phone assets), or was it only ever for OTP sending — in which case it belongs in auth/
   not providers/?

  ---
  Stage 17 — Zima Companion (Phase 1: Browser Visibility)

  Goal: Signed native Rust binary that collects browser/OS state and POSTs snapshots to the backend.
  Phase 1 is visibility-only — no automated remediation.

  17a — DB models: CompanionSession + BrowserSnapshot in backend/app/db/models/companion.py
        Registered in backend/app/db/migrations/env.py
  17b — Alembic migration: e5f6a7b8c9d0_add_companion_tables.py
        Creates companion_sessions (unique on user_id) + browser_snapshots (JSONB raw_snapshot)
  17c — CompanionRepository: upsert_session, get_session_by_user, update_last_seen,
        insert_snapshot, get_latest_snapshot — in backend/app/db/repositories/companion.py
  17d — Auth utils: create_companion_token / decode_companion_token in backend/app/auth/utils.py
        get_companion_user() dependency in backend/app/api/dependencies.py (Bearer-only, no cookie)
  17e — API router: 4 endpoints in backend/app/api/v1/companion.py
        POST /companion/setup-token, POST /companion/register, POST /companion/snapshot, GET /companion/status
        Wired into backend/app/api/router.py
  17f — Config additions: companion_setup_token_expire_minutes, companion_token_expire_days
  17g — Rust companion scaffold: companion/ directory with Cargo.toml, rust-toolchain.toml,
        .cargo/config.toml, src/{main,config,auth,models,client,snapshot}.rs,
        src/collectors/{mod,browser,os}.rs
  17h — Browser baselines JSON: companion/baselines/{chrome,brave,firefox}-v1.json
        5 rules each covering DNS-over-HTTPS, safe browsing, HTTPS-only, extension auto-update, and
        browser-specific privacy controls
  17i — Build infrastructure: companion/Makefile (build-mac-arm/x86/universal/linux/windows),
        .github/workflows/companion-ci.yml, .github/workflows/companion-release.yml
        Release workflow: matrix build all 4 targets, optional macOS codesign, GitHub Release
  17j — Frontend: SetupTokenResponse + CompanionStatusResponse types added to frontend/src/types/api.ts
        Companion status card added to frontend/src/app/(dashboard)/browser/page.tsx
        — polls GET /companion/status every 30s
        — "Generate setup token" button → POST /companion/setup-token → shows install command
  17k — Documentation: Brain/Zima/Companion/{architecture,building,baselines}.md created
        Rule 11 (Companion Architecture Boundary) appended to .claude/CLAUDE.md
