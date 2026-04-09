# Zima Companion — Browser Baselines

Baselines are versioned JSON rule sets that describe the desired state for each browser. The companion reads these during a snapshot and (in a future phase) can apply fixes.

## Location

```
companion/baselines/
├── chrome-v1.json
├── brave-v1.json
└── firefox-v1.json
```

## Rule schema

```json
{
  "browser": "chrome",
  "baseline_version": "1",
  "rules": [
    {
      "id": "chrome-dns-over-https",
      "title": "DNS-over-HTTPS enabled",
      "setting_key": "dns_over_https.mode",
      "desired_value": "automatic",
      "audit_method": "read_preference",
      "apply_method": "write_preference",
      "verify_method": "read_preference",
      "requires_admin": false,
      "risk_if_skipped": "DNS queries sent in plaintext...",
      "rollback_support": true,
      "reference": "https://..."
    }
  ]
}
```

## Field reference

| Field | Description |
|-------|-------------|
| `id` | Unique rule ID (kebab-case, browser-prefixed) |
| `title` | Human-readable rule name shown in the UI |
| `setting_key` | Browser-specific preference key path |
| `desired_value` | Value that must be set for the rule to pass |
| `audit_method` | How the companion reads the current value |
| `apply_method` | How the companion would apply the fix (Phase 2) |
| `verify_method` | How to confirm the fix took effect |
| `requires_admin` | Whether applying the fix needs elevated privileges |
| `risk_if_skipped` | Short description of the security risk |
| `rollback_support` | Whether the companion can undo the change |
| `reference` | Link to official browser documentation |

## Audit methods

| Method | Description |
|--------|-------------|
| `read_user_pref` | Read Firefox `prefs.js` / `user.js` preference file |
| `read_preference` | Read Chromium `Preferences` JSON file in the profile dir |

## Current baselines

### Chrome v1 (5 rules)
- `chrome-dns-over-https` — DNS-over-HTTPS mode set to "automatic"
- `chrome-safe-browsing` — Safe Browsing enabled
- `chrome-https-only` — Always use HTTPS mode enabled
- `chrome-extension-auto-update` — Extension auto-update enabled
- `chrome-site-isolation` — Site isolation / strict origin isolation enabled

### Brave v1 (5 rules)
- `brave-shields-enabled` — Brave Shields enabled globally
- `brave-https-everywhere` — HTTPS Everywhere / upgrade insecure requests (strict)
- `brave-safe-browsing` — Safe Browsing enabled
- `brave-fingerprinting-protection` — Fingerprinting protection (strict)
- `brave-extension-auto-update` — Extension auto-update enabled

### Firefox v1 (5 rules)
- `firefox-dns-over-https` — DNS-over-HTTPS (`network.trr.mode = 2`)
- `firefox-https-only-mode` — HTTPS-only mode (`dom.security.https_only_mode = true`)
- `firefox-safe-browsing` — Safe Browsing (`browser.safebrowsing.malware.enabled = true`)
- `firefox-tracking-protection` — Enhanced Tracking Protection set to strict
- `firefox-extension-auto-update` — Extension auto-update enabled

## Adding a new baseline

1. Create `companion/baselines/<browser>-v<N>.json` following the schema above.
2. Add a unit test in `companion/src/` that deserialises the file and validates all required fields are present.
3. Bump `baseline_version` when rules change in a breaking way; keep the old file for rollback.
4. Rules should only use `audit_method` values that the companion's `collectors/browser.rs` already supports.
