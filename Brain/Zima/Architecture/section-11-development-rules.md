← [[../Zima|Home]] · [[section-10-dependency-flow|← §10 Dependency Flow]] · [[section-12-example-module-definition|§12 Example Module →]]

# Section 11 — Development Rules

These rules apply to all contributors and all layers of the platform. They encode the core architectural decisions and must be respected throughout implementation.

---

## Rules

**Keep providers simple**
No business logic, no user-facing messaging, no severity assignment. Providers fetch, parse, and normalize. Nothing more.

**Keep modules focused**
One module, one security capability. If a module is doing two distinct things, it should be two modules.

**Normalize everything**
All module outputs become standardized signals. No ad-hoc data structures passing between layers.

**Isolate correlation logic**
Composite risks belong exclusively in the correlation layer. Modules must not combine their own signals with signals from other modules.

**Version scoring logic**
Score models must be reproducible. Changes to weights or calculators must be versioned so historical scores remain explainable.

**Decouple tiers**
Modules do not know which tier enabled them. Tier awareness lives only in the tier configuration and the module runner. Never branch on tier inside a module.

**Avoid cross-module calls**
Modules must not call other modules directly. If a risk requires inputs from two domains, surface them both as signals and handle the relationship in the correlation layer.

**Automation is not a module domain**
The automation layer is a backend peer of correlation, scoring, and remediation. Do not place automation capabilities inside `modules/`. Automation workflows live in `backend/app/automation/workflows/`.

**Scoring lives in the scoring layer**
Score calculation logic, weighting, and trend analysis belong in `backend/app/scoring/`. Do not place scoring logic inside modules or correlation rules.

**Test thoroughly**
Every provider, module, correlation rule, and scoring calculator needs unit test coverage. Negative cases — timeouts, auth failures, malformed data, 429s — are first-class test requirements.

**Use the repository pattern for persistence**
No layer above `db/` issues raw queries. All database access goes through repository classes.

---

**See also:** [[CLAUDE-CODE-BRIEFING|Implementation Reference (canonical code)]] · [[section-10-dependency-flow|§10 Dependency Flow]] · [[../Architecture/Design Principles|Design Principles (summary)]] · [[section-15-testing-strategy|§15 Testing Strategy]]
