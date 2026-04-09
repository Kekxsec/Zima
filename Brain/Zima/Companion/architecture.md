# Zima Companion — Architecture

## Overview

The Zima Companion is a signed native binary that runs on the user's machine. It collects browser and OS state, then POSTs structured snapshots to the Zima backend via authenticated API calls. Phase 1 is visibility-only — no automated remediation.

```
[User Machine]                         [Zima Backend]
  zima-companion daemon
    ├── collectors/browser.rs  ──────▶  POST /api/v1/companion/snapshot
    ├── collectors/os.rs                GET  /api/v1/companion/status
    └── auth.rs (OS keychain)
```

---

## Authentication Flow

```
1. User clicks "Generate setup token" on the browser page
   → POST /api/v1/companion/setup-token (user JWT)
   ← { setup_token: "...", expires_in: 900 }  (15-minute one-time token)

2. User runs: zima-companion setup --token <setup_token>
   → POST /api/v1/companion/register (no auth, rate-limited 10/hour)
     body: { setup_token, user_id, machine_id, platform, version }
   ← { companion_token: "..." }  (7-day companion JWT, type="companion")

3. Companion stores token in OS keychain (keyring crate, service "zima-companion")

4. Daemon loop (every 15 min):
   → POST /api/v1/companion/snapshot  (Bearer companion_token)
     body: { raw_snapshot: { browser_profiles, os_info } }
```

---

## JWT Claims

Companion JWTs are distinct from user JWTs:

| Claim | User JWT | Companion JWT |
|-------|----------|---------------|
| `type` | `"access"` | `"companion"` |
| `sub` | user_id | user_id |
| `jti` | — | companion_session_id |
| `exp` | short (15 min) | 7 days |

`get_companion_user()` in `backend/app/api/dependencies.py` accepts Bearer-only (no cookie) and validates `type == "companion"`.

---

## Database Schema

### `companion_sessions`
One row per user (unique constraint on `user_id`). Upserted on each register.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID FK | unique — one session per user |
| `machine_id` | String(512) | SHA-256 of hardware ID, AES-256-GCM encrypted |
| `platform` | String(20) | "darwin" / "linux" / "windows" |
| `companion_version` | String(32) | semver string |
| `companion_jti` | String(64) | links session to JWT |
| `last_seen_at` | DateTime | updated on each snapshot |

### `browser_snapshots`
Append-only snapshot log. JSONB column for raw_snapshot.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | PK |
| `user_id` | UUID FK | — |
| `companion_session_id` | UUID FK | → companion_sessions |
| `raw_snapshot` | JSONB | full collector output |
| `created_at` | DateTime | indexed with user_id |

---

## Setup Token

Stored in `auth_tokens` table (no schema change) with key `companion_setup:{user_id}`. Value is a cryptographically random hex token. Expires in 15 minutes. Consumed on first use.

---

## Snapshot Format

```json
{
  "browser_profiles": [
    {
      "browser": "chrome",
      "profile_path": "/Users/alice/Library/Application Support/Google/Chrome/Default",
      "extensions": [
        { "id": "cjpalhdlnbpafiamejdnhcphjbkeiagm", "name": "uBlock Origin", "version": "1.55.0", "description": "..." }
      ]
    }
  ],
  "os_info": {
    "platform": "darwin",
    "hostname": "alice-mbp",
    "os_version": "macOS 14.4",
    "filevault_enabled": true,
    "sip_enabled": true,
    "firewall_enabled": true
  }
}
```

---

## Architecture Boundary (Rule 11)

- The companion binary MUST NOT write directly to the database.
- All companion → backend communication is via the HTTP API only.
- The backend treats the companion as an untrusted client: validates the JWT, rate-limits registration, and stores only structured data.
- Phase 1 is read-only visibility. The companion does NOT modify browser settings or OS configuration.
