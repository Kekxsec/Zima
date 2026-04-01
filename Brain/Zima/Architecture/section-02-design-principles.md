← [[../Zima|Home]] · [[section-01-overview|← §1 Overview]] · [[section-03-repository-structure|§3 Repository Structure →]]

# Section 2 — Core Design Principles

---

## 2.1 Separation of Concerns

| Layer       | Responsibility                                                                                                                    |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Providers   | Connect to external or local sources, handle authentication, requests, pagination, rate limits, and return normalized source data |
| Modules     | Interpret provider data, map it to security risks, assign severity and confidence, and emit standardized signals                  |
| Signals     | Standard data structure for findings, used uniformly across all modules                                                           |
| Correlation | Combine signals into higher-level findings and risk patterns                                                                      |
| Scoring     | Convert signals and findings into numerical or categorical scores                                                                 |
| Remediation | Provide practical fixes, step-by-step instructions, and estimated effort                                                          |
| Automation  | Execute selected remediation steps with approvals, audit logs, and rollback                                                       |

---

## 2.2 The Key Rule

Providers answer **how do I get the data?**
Modules answer **what does the data mean?**

Do not mix these roles. This boundary is non-negotiable.

- Providers never assign severity
- Providers never produce user-facing outputs
- Modules never manage authentication or raw API request logic
- Modules never call other modules directly

---

## 2.3 Tier Model

Tiers are defined externally as configuration. They enumerate which module domains are enabled for each plan. Modules have no awareness of which tier has activated them.

```
Core → Plus → Pro → Business
```

Tiers control:

- which module domains run
- which signals and scores are surfaced to the user
- which automation tasks are available

All pipeline infrastructure remains unchanged across tiers. Granularity is defined at the **domain level** in configuration, with individual module overrides available where finer control is needed.

---

## 2.4 Dependency Direction

All dependencies flow in one direction only:

```
core → providers → modules → correlation → scoring → remediation → automation → api
```

Lower layers must never import higher layers. This rule prevents circular dependencies, keeps each layer independently testable, and makes the system easier to reason about.

---

## 2.5 Automation as a Backend Layer

Automation is a **top-level backend layer**, not a module domain. It is a peer of correlation, scoring, and remediation in the pipeline. It consumes remediation output and executes approved workflows.

Automation workflows are not security detection capabilities and do not emit security signals in the same sense as module outputs. They emit operational results such as `automation_completed` or `automation_failed`, which are audit records rather than risk signals.

Do not model automation as a module domain. Keep it in `backend/app/automation/`.

---

## 2.6 Scoring as a Backend Layer

Similarly, scoring is a **top-level backend layer** with its own calculators, weights, and policies. It is not a module domain. Score logic belongs in `backend/app/scoring/`, not in `modules/`.

If scoring requires auxiliary data (e.g. trend analysis, weighting inputs), that logic lives in `scoring/` directly.

---

**See also:** [[section-10-dependency-flow|§10 Dependency Flow]] · [[section-11-development-rules|§11 Dev Rules]] · [[CLAUDE-CODE-BRIEFING|Implementation Reference]] · [[../Architecture/Design Principles|Design Principles (summary)]]
