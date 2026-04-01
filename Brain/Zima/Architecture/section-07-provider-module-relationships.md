← [[../Zima|Home]] · [[section-06-module-architecture|← §6 Module Architecture]] · [[section-08-signal-model|§8 Signal Model →]]

# Section 7 — Provider ↔ Module Relationship Patterns

Providers and modules interact in three patterns depending on the nature of the data source and the security capability being implemented.

---

## Pattern A — One Module → One Provider

```text
breach_monitor → hibp
```

Use when one source cleanly and completely supports one security capability. The simplest and most independently testable arrangement. Prefer this pattern where possible.

---

## Pattern B — One Module → Multiple Providers

```text
domain_security
  → securitytrails
  → crtsh
  → openphish
```

Use when a capability needs multiple data sources to produce a complete picture. The module aggregates and reconciles provider outputs before emitting signals. Signal confidence may be elevated when corroborated by multiple providers.

---

## Pattern C — Multiple Modules → One Provider

```text
google_workspace
  → mfa_posture
  → mailbox_security
  → saas_inventory
```

Use when one rich API exposes multiple distinct security surfaces, each belonging to a different module domain. Each consuming module focuses on its own domain and emits its own signals. The provider remains generic and serves all of them.

---

## Guidance

- **Prefer Pattern A** for testability and clarity.
- **Use Pattern B** when signal quality meaningfully improves from multiple sources, or when provider coverage is partial.
- **Pattern C is inevitable** for rich API providers such as Google Workspace and Microsoft 365. Keep providers generic — interpretation belongs in the modules.
- In all patterns, providers never know which modules consume them. The coupling is always one-directional: module → provider.
