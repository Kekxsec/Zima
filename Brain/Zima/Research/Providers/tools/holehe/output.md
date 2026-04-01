---
title: "output / tools / holehe"
aliases: ["holehe output", "holehe signal registry"]
tags: [zima, research, outputs, signal-registry, tools, holehe, graph_exclude]
type: provider_research_output
provider: holehe
provider_category: tools
status: not_started
prompt_note: prompt.md
provider_folder: holehe.md
obsidianUIMode: preview
---
# holehe Provider Integration Research for Zima

## API Surface Appendix

holehe is a local Python OSINT tool (CLI + importable modules) that checks whether an **email** is associated with accounts on many third‑party services by probing login/registration/forgot‑password flows and interpreting responses. The project’s primary maintained “documentation” is its repository README and source code on GitHub. 

### CLI artifact

**Artifact name**
`holehe` (console script entry point)

**Purpose**
Run a scan for a target email across the tool’s available modules and print a per‑site outcome list; optionally export a CSV. 

**Supported entity_type(s)**

- `email` (single target email per invocation) 

**Auth / execution requirements**

- No API keys or authentication are required for holehe itself; it issues real HTTP requests to third‑party services. 
- Designed to run on Python 3. 
- Typical install via PyPI: `pip3 install holehe`. 
- Network egress to the checked sites is required. 

**Parameters / flags (argparse)**
The CLI argument parser in `holehe/core.py` defines: 

- Positional: `email` (metavar `EMAIL`, `nargs='+'`; code uses the first item) 
- `--only-used` (store_true, `dest="onlyused"`): display only sites where email is used 
- `--no-color` (store_true, `dest="nocolor"`): do not colour terminal output 
- `--no-clear` (store_true, `dest="noclear"`): do not clear terminal before displaying results 
- `-NP` / `--no-password-recovery` (store_true, `dest="nopasswordrecovery"`): _do not try password recovery on the websites_ 
- `-C` / `--csv` (store_true, `dest="csvoutput"`): export results to CSV 
- `-T` / `--timeout` (int, default `10`, `dest="timeout"`): max timeout for requests 

**Important side behaviour (auto-update check)**
Before parsing args, the CLI calls `check_update()`, which fetches the current version from `https://pypi.org/pypi/holehe/json`, and if the version differs from `__version__` it attempts to run `pip install --upgrade holehe` and exits. This affects reproducibility and should be considered in Zima packaging. 

**Top-level output artefacts**

- **STDOUT**: A printed per‑site list (coloured unless `--no-color`), with symbols for used, not used, rate‑limited, and error. 
- **CSV file** (when `-C/--csv`): a file named like `holehe_<timestamp>_<email>_results.csv` is written; the code uses `csv.DictWriter(..., fieldnames=data[0].keys())` and writes all rows. 

**Response variants (CLI “result states”)**
The CLI prints different markers based on dictionary fields: 

- _Rate limited_: `results["rateLimit"] == True` (printed as `[x] domain`)
- _Error_: `"error" in results.keys()` and `results["error"] == True` (printed as `[!] domain`, optionally with an error message if present in `others`)
- _No hit_: `results["exists"] == False` (printed as `[-] domain`)
- _Hit_: `results["exists"] == True` (printed as `[+] domain`, optionally appending `emailrecovery`, `phoneNumber`, and some `others` keys)

**Always-present vs optional vs conditional fields**
This is split into: (a) fields documented in the README, and (b) additional fields present in current module implementations.

- **Documented per-module fields (README “Module Output”)**: 

    - `name` (string)
    - `rateLimit` (boolean)
    - `exists` (boolean)
    - `emailrecovery` (string or null; “sometimes partially obfuscated recovery emails”)
    - `phoneNumber` (string or null; “sometimes partially obfuscated recovery phone numbers”)
    - `others` (object or null; “any extra info”)
- **Additional per-module fields observed in module code (not listed in README output snippet)**:

    - `domain` (string) — used by CLI printing; present in example modules like `aboutme`, `facebook`, `amazon`, `mail_ru`, `samsung`, `adobe`, `odnoklassniki`. 
    - `method` (string) — matches the README module table values (_register_, _login_, _password recovery_, _other_). 
    - `frequent_rate_limit` (boolean) — aligns with README “Frequent Rate Limit” column (check mark vs cross). 
- **Conditional error field injected by orchestrator**

    - `error` (boolean) appears in the `launch_module` exception handler output dict, and the CLI has explicit printing behaviour for it. 
    - The CLI _appears_ to expect (optionally) an error message inside `others["errorMessage"]` when `"Message"` is present in `others.keys()` (this key relationship is inconsistent in the code and should not be relied upon as a stable contract). 

**Enum values / status values**

- `method` values are documented as: `register`, `login`, `password recovery`, `other` (from the README “Modules” table). 
- `rateLimit`, `exists`, `frequent_rate_limit`, `error` are booleans. 

### Python/library surface

holehe does not present a single official “SDK client” API in the README; instead it provides many module functions. The README’s Python example demonstrates importing an individual module and calling it with `(email, client, out)` in an async `trio` context using an `httpx.AsyncClient`. 

**Artifact(s) and callable shapes**

- **Per-site module functions**

    - Signature pattern: `async def <service>(email, client, out): ... out.append({...})` 
    - Inputs:
        - `email` (string)
        - `client` (`httpx.AsyncClient`) in typical module usage and in the README example 
        - `out` (list) mutated by appending one dict per module call 
    - Output: no return contract is documented; modules append a dict into `out`. 
- **Orchestration helpers in `holehe/core.py`** (useful if Zima wants to run “all modules” similarly to CLI)

    - `import_submodules("holehe.modules")`: walks packages and imports modules 
    - `get_functions(modules, args=None)`: collects callable functions from imported modules; has a conditional branch that excludes specific password-recovery modules when `args.nopasswordrecovery == True` (see next section). 
    - `launch_module(module, email, client, out)`: awaits a module and catches exceptions, appending an `error=True` record on failure. 
    - `is_email(email: str) -> bool`: regex-based email validation used by CLI. 

**Password-recovery module suppression (important for side-effects control)**
When `--no-password-recovery` is set, `get_functions` excludes specific modules by name check in code: `adobe`, `mail_ru`, `odnoklassniki`, `samsung`. This is a concrete implementation hook Zima can use to reduce recovery-flow probing. 

### Module catalogue artifact

The README includes a module table listing `Name`, `Domain`, `Method`, and whether it has `Frequent Rate Limit`. This is the closest thing to a provider-maintained “coverage list” and can be used in mappers for service normalisation / classification. 

### “Online version” mention

The README references a “Holehe Online Version” (linking to `osint.industries`). Because Zima’s intended integration is a local library/CLI, that online service is out-of-scope for implementation unless you intentionally opt into sending investigated emails to a third party. 

## Module Mapping Table

|module|provider_role|provider_method|endpoint_or_artifact|classification|entity_types|gating_logic|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|
|account_inventory|enrichment_only|Per-site module functions: `async def <service>(email, client, out)`; optionally orchestrated via `import_submodules()` + `get_functions()` + `launch_module()`|Python library modules under `holehe.modules.*` (preferred over CLI for controllable concurrency/side effects)|enrichment_only|email|Validate email with `holehe.core.is_email()`; default to **exclude password recovery modules** via `--no-password-recovery` equivalent (omit `adobe`, `mail_ru`, `odnoklassniki`, `samsung`); enforce your own concurrency limit (avoid CLI “fan out to all sites at once”); discard results where `rateLimit==True` from inventory write path (keep as run telemetry); allow per-module suppress/allow lists||holehe’s `exists` is best treated as **account-inventory enrichment**, not a Zima “security finding”. Recovery hints (`emailrecovery`, `phoneNumber`, and some `others`) are valuable enrichment but can be sensitive and should be handled as PII/secret-adjacent data.|
|account_enumeration_risk|utility_only|Same module functions / orchestrator; focus on fields `exists`, `emailrecovery`, `phoneNumber`, `method`, `frequent_rate_limit`|Same as above; do **not** use the “Holehe Online Version” because it externalises investigated emails|utility_only|email|Do not emit per-site signals by default; instead compute a **derived risk metric** (internal score) from counts of `exists==True` and presence of recovery hints (`emailrecovery`/`phoneNumber` non-null) while separating “rateLimited/error” from true negative; optionally rerun only a small subset of modules to confirm (reduce false positives)||holehe already operationalises account enumeration; the main Zima value here is _internal_ assessment and correlation (e.g., combine with breach/MFA modules), not standalone alerts.|

## Signal Contracts, Severity, and Tags

holehe’s maintained documentation explicitly frames output as “module output” for account presence checks and (sometimes) masked recovery hints; it does **not** describe any security event model, and the tool itself is best treated as enrichment/utility. 

Because of that (and consistent with your first-pass assessment), **no standalone Zima signals should be emitted directly from holehe** for either `account_inventory` or `account_enumeration_risk` in the current Zima stage.

### Signal Contract Table

|module|source|provider|provider_method|signal_type|category|severity|severity_is_conditional|conditional_rule|entity_type|finding_kind|trigger_condition|evidence_fields|enrichment_fields|summary_template|evidence_status|citation_refs|notes|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### Severity rules assessment

- Your first-pass severity assessment (“account existence is info/low and feeds inventory, not an alert”) is correct for this provider in isolation, because holehe’s outputs primarily describe _where an email may be registered_ and optional _masked recovery hints_, not credential compromise, malware, or active abuse. 
- If you later decide to create signals, you would need to justify them as **risk posture signals** (not incident signals) and keep them at `info`/`low` unless you can demonstrate direct exposure per your calibration guide; holehe alone does not provide plaintext credentials or breach confirmation. 

### Tags

No tags are provided because there are no emitted signal types for this provider in the current design.

## Confidence Guidance

|module|signal_type_or_use_case|source_reliability|freshness_considerations|corroboration_rules|calibration_todo|
|---|---|---|---|---|---|
|account_inventory|email→service account presence enrichment (`exists`)|Reliability is **module- and site-dependent**: each module encodes bespoke heuristics against third-party flows. `exists==True` is stronger than `exists==False`, because “no hit” may be caused by anti-bot behaviour or site changes that still return `rateLimit==False`. `rateLimit==True` is an explicit “don’t trust this attempt” signal.|Results are near-real-time but can drift quickly: sites change endpoints/behaviour, which can flip a module from working to always failing (see Snapchat breakage reports in issues).|Corroborate “account exists” before using it for security decisions by: (a) re-running a small subset of high-value modules with stricter throttling, (b) cross-checking with other inventory sources (SSO/IdP, SaaS admin APIs), (c) using breach/credential modules to determine if discovered accounts are in known leaks.|Build per-module precision/recall telemetry: track `{domain, method, frequent_rate_limit}` plus outcome rates (`exists`, `rateLimit`, `error`) over time; create allow/deny lists per tenant; add retry-with-backoff and VRF-style “confidence buckets” for `exists==True` vs `exists==False`.|
|account_enumeration_risk|internal derived metric: recovery hint exposure (`emailrecovery` / `phoneNumber`)|Masked recovery hints are more directly evidence-backed than bare existence, because they imply the remote service returned a specific recovery artefact (still masked). However, values are “sometimes partially obfuscated” and quality varies by module.|Freshness is volatile: some modules use password recovery endpoints and can break with minor UI/API changes; additionally, use of password recovery flows is more likely to be rate-limited or blocked.|Do not treat recovery hints as “PII exposure incident” without corroboration. Use them for correlation only (e.g., matching masked recovery phone digits to known phone) and risk scoring, not alerting. If you later alert, confirm by repeated checks and/or alternate providers.|Measure: (1) which modules actually return `emailrecovery`/`phoneNumber` in practice, (2) false positive rate when the user confirms they do/don’t have the account, (3) block/captcha rates per ASN/geo. Default-disable password recovery modules unless a user explicitly opts in.|

## Implementation Notes

### Parsing and field survivability

At minimum, preserve these per-result fields exactly as emitted (field paths shown as `results[i].<field>`):

- `name` (service/module identifier) — documented output field. 
- `domain` — used by CLI printing and present in module implementations (even though not in the README’s minimal output snippet). 
- `method` — important for gating (e.g., password recovery vs register/login), aligns to README module table. 
- `frequent_rate_limit` — useful for throttling policies and to bias retries. 
- `exists` — core enrichment (account presence). 
- `rateLimit` — explicit “do not trust this attempt”; treat as utility/telemetry more than enrichment. 
- `emailrecovery`, `phoneNumber` — enrichment/correlation fields; may be null; described as “sometimes partially obfuscated”. 
- `others` — opaque enrichment container; keys are service-specific and unstable (examples the CLI prints specially include `FullName` and `Date, time of the creation`). 
- Optional: `error` — only appears when the orchestrator catches an exception during a module run; handle as utility/telemetry. 

### Null / empty / no-hit behaviour

- Treat `exists==False` as **“no evidence of an account”**, not strong evidence of absence, unless you have corroboration that the module is functioning reliably for that service (module-specific calibration). 
- Treat `rateLimit==True` as **“attempt invalid / incomplete”**; do not write inventory “absence” from these rows. 
- If the orchestrator yields `error==True`, treat it similarly to a failed attempt and do not record absence. 

### Rate limiting, concurrency, and stability

- The CLI launches modules concurrently using `trio.open_nursery()` and `start_soon(...)` for every website function, meaning it can generate a burst of parallel requests. This increases rate limiting and CAPTCHAs risk; Zima should not mirror this behaviour directly. 
- holehe’s own user-facing advice is “Rate limit? Change your IP.”, and the tool exposes `rateLimit` explicitly. In Zima, you’ll want a safer strategy: concurrency caps, exponential backoff, per-domain cooldowns, and IP reputation management. 
- Some modules are known to break as sites change (e.g., Snapchat 405 / endpoint changes discussed in issues). Operationally, treat per-module functionality as non-stationary and expect ongoing maintenance. 

### “Password recovery” modules and side-effect risk

- holehe’s README claims it “does not alert the target email.” Treat this as an aspirational property, not a guarantee for all modules over time. 
- The CLI provides `--no-password-recovery`, and the core code uses it to suppress a small set of password-recovery modules (`adobe`, `mail_ru`, `odnoklassniki`, `samsung`). In Zima, **default to suppression** unless a customer explicitly opts in. 
- Password recovery modules are also the primary source of `emailrecovery`/`phoneNumber` enrichment (e.g., `mail_ru` parses `phones` and `emails` from response JSON; `samsung` attempts to recover masked phone info through reset flows; `odnoklassniki` scrapes masked email/phone and a “FullName” composite in `others`). 

### Deduplication keys / natural identifiers

For inventory storage (not signals), recommended natural keys:

- `(input_email, result.domain)` as the primary identifier for “email has an account on domain” records. (Domain is already the canonical cross-module “service identity” for holehe.) 
- Store `method` and `name` as supporting identifiers (they help explain _how_ existence was inferred, and `name` may differ in case/capitalisation for some modules). 

### What belongs where in Zima

- **Provider client layer**

    - Owns execution: controlled concurrency, timeouts, retries, and safe defaults (e.g., suppress password recovery modules by default).
    - Normalises output to a stable internal structure while preserving original provider fields (especially booleans and masked recovery hints).
    - Must disable/avoid holehe CLI auto-update behaviour (`check_update()`) by not invoking the CLI entry point in production. 
- **Module mapper layer** (`modules/account_inventory/mapper.py`)

    - Converts `results[]` entries into Zima account inventory objects (not signals).
    - Applies “attempt validity”: ignore `rateLimit==True` and `error==True` for negative assertions. 
- **Correlation layer (later modules)**

    - Uses the inventory to drive security decisions (breach correlation, MFA posture checks, suspicious login alerts) rather than emitting “account exists on X” as standalone. This matches holehe’s output nature. 

### Licensing / packaging cautions

- The project is licensed under GNU GPL v3 (copyleft), per both README and PyPI metadata; this can materially affect redistribution and linkage decisions for a commercial platform. 
- The README states “Built for educational purposes only.” Treat this as a usage caution and ensure your product/legal posture is aligned before shipping. 

## Provider Summary and Structured JSON

### Strongest signal types

None. holehe should be treated as **enrichment/utility** for building an email-linked account inventory (and optional masked recovery hint enrichment), not a module that emits independent security incident signals. 

### What the provider should not be used for

- Not a breach/credential exposure detector: holehe does not output plaintext credentials or breach confirmation; it outputs existence checks and sometimes masked recovery hints. 
- Not a stable long-term data source without maintenance: modules can break as third-party sites change. 
- Not appropriate to run via the “online version” in a security product unless you explicitly accept externalising investigated emails to a third party. 

### API/auth/rate-limit/licensing implementation cautions

- No provider auth, but heavy third-party rate limiting risks; avoid CLI default “launch everything concurrently”. 
- Prefer internal orchestration (library usage) to control traffic, reduce CAPTCHAs, and implement backoff. 
- Use `--no-password-recovery` equivalent as default gating to reduce more intrusive flows; the code explicitly supports this pathway. 
- GPLv3 licensing implications are non-trivial for a closed-source SaaS; treat this as a release blocker until cleared. 

### Provider classification for current Zima stage

Treat holehe as **utility_only + enrichment_only** (inventory enrichment), **not signal-producing**, for P1/Core integration. 

### Structured JSON
{
  "provider": "holehe",
  "provider_category": "tools",
  "provider_role": "utility_only",
  "module_mappings": [
    {
      "module": "account_inventory",
      "provider_method": "async per-site module functions: holehe.modules.*.<service>(email, client, out); optional orchestrator: holehe.core.import_submodules + holehe.core.get_functions + holehe.core.launch_module",
      "endpoint_or_artifact": "local python package + module functions (preferred); CLI `holehe` (discouraged for production orchestration)",
      "classification": "enrichment_only",
      "entity_types": ["email"],
      "gating_logic": {
        "email_validation": "holehe.core.is_email(email) must be true",
        "default_password_recovery_modules": "disabled (exclude adobe, mail_ru, odnoklassniki, samsung)",
        "attempt_validity": "do not treat rateLimit==true or error==true results as evidence of non-existence",
        "throttling": "unknown (must be implemented by Zima; do not run all modules concurrently as CLI does)"
      },
      "source_module_name_for_signals": "unknown (no standalone signals recommended)",
      "notes": "Use `exists`/`domain` to build account inventory; store `emailrecovery`/`phoneNumber`/`others` as optional enrichment with careful handling."
    },
    {
      "module": "account_enumeration_risk",
      "provider_method": "same as account_inventory; focus on fields exists/emailrecovery/phoneNumber/method/frequent_rate_limit",
      "endpoint_or_artifact": "local python package + module functions",
      "classification": "utility_only",
      "entity_types": ["email"],
      "gating_logic": {
        "no_signals": "do not emit module-level signals from holehe in current stage",
        "risk_metric_only": "derive internal score from counts of exists==true and presence of recovery hints (emailrecovery/phoneNumber not null); ignore rate-limited/error attempts"
      },
      "source_module_name_for_signals": "unknown (no standalone signals recommended)",
      "notes": "If later turned into signals, treat as low-severity posture/risk signals and require corroboration."
    }
  ],
  "signal_contracts": [],
  "confidence_guidance": [
    {
      "module": "account_inventory",
      "signal_type_or_use_case": "email_to_service_account_presence_enrichment",
      "source_reliability": "module- and target-site-dependent; false negatives likely; trust exists==true more than exists==false; treat rateLimit==true/error==true as invalid attempts",
      "freshness_considerations": "near-real-time but volatile as sites change behaviour; requires ongoing maintenance",
      "corroboration_rules": "re-run subset for confirmation; corroborate with SaaS/IdP inventory and breach/MFA modules",
      "calibration_todo": "collect per-module precision/recall telemetry; add throttling/backoff/caching; create allow/deny lists per tenant"
    },
    {
      "module": "account_enumeration_risk",
      "signal_type_or_use_case": "derived_risk_metric_from_recovery_hints",
      "source_reliability": "masked recovery hints are stronger evidence than bare existence but still module/site dependent",
      "freshness_considerations": "password recovery flows are more likely to be blocked/rate limited; modules can break",
      "corroboration_rules": "use only for correlation and scoring; do not alert without repeated confirmation and/or alternative providers",
      "calibration_todo": "measure which modules actually return emailrecovery/phoneNumber; default-disable password recovery modules; build opt-in controls"
    }
  ]
}
