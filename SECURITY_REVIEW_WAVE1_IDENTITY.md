# Security Review: Wave 1 Identity Modules & Providers

**Review Date**: 2026-03-27
**Scope**: Identity modules, breach/reputation/social providers, correlation rules, and remediation engine
**Codebase**: Python 3.12, FastAPI, SQLAlchemy 2.0 async, Pydantic v2

---

## Executive Summary

**CRITICAL Issues**: 3
**HIGH Issues**: 1
**MEDIUM Issues**: 2
**LOW Issues**: 1
**INFO Issues**: 0

The Wave 1 identity modules are generally well-architected with proper separation of concerns (providers fetch, modules emit signals). However, three critical vulnerabilities pose immediate risk:

1. **Plaintext credentials stored in database** via signal evidence dicts
2. **Subprocess injection risk** in holehe/maigret providers
3. **Excessive API call costs** without rate limiting or input constraints

These must be addressed before production deployment.

---

## Critical Issues

### C1: Plaintext Credentials Persisted to Database

**Severity**: CRITICAL
**Files**:
- `/Users/max/Zima/backend/app/providers/breach/dehashed/client.py` (line 65)
- `/Users/max/Zima/backend/app/modules/identity/breach_monitor/service.py` (line 122)

**Description**:
The DeHashed provider returns a `raw` field containing the full API response, including an `entries` array where each entry contains:
```python
{"password": "plaintext_password", "hashed_password": "hash", ...}
```

The breach_monitor module stores this entire finding (including all entries) in the signal evidence dict at line 122:
```python
evidence={"raw_finding": finding}
```

This evidence dict is persisted to the database and exposed via signal retrieval APIs. Plaintext passwords from breach data should NEVER be stored persistently.

**Impact**:
- Confidentiality breach: plaintext passwords accessible via signal APIs
- Data retention liability: GDPR/CCPA exposure
- Lateral movement risk: if database is compromised, all breached credentials exposed
- Severity escalation: Plaintext passwords are the highest-value data for attackers

**Recommended Fix**:

**Option A (Preferred - Remove entirely)**:
```python
# backend/app/providers/breach/dehashed/client.py
# Remove entries from raw dict before returning to caller
if total and total > 0:
    findings.append(
        dict(
            provider=self.name,
            category="credential_leak",
            title=f"DeHashed: {val}",
            description=f"{val} found in {total} DeHashed breach record(s)",
            entity_type=_entity_type,
            entity_value=val,
            tags=["dehashed", "leak", "breach", "passive"],
            raw={
                "total": total,
                "sample_count": len(entries),
                # REMOVED: "entries": entries  ← CRITICAL: Never persist full entries
            },
        )
    )
```

**Option B (If entries needed for other modules)**:
Create a sanitized version that removes password fields:
```python
def _sanitize_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove plaintext password fields before returning to modules."""
    sanitized = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # Keep only structural fields, remove all password data
        safe_entry = {
            "email": entry.get("email"),
            "username": entry.get("username"),
            "name": entry.get("name"),
            "has_password": bool(entry.get("password")),
            "has_hash": bool(entry.get("hashed_password")),
        }
        sanitized.append(safe_entry)
    return sanitized
```

**Option C (If plain text must be examined for real-time decision)**:
Do not persist; only hold in memory during module execution:
```python
# backend/app/modules/identity/breach_monitor/service.py (line 122)
# Instead of storing raw_finding with plaintext passwords:
evidence={
    "raw_finding": {  # sanitized version
        "provider": finding.get("provider"),
        "category": finding.get("category"),
        "title": finding.get("title"),
        "description": finding.get("description"),
        "tags": finding.get("tags"),
        # Deliberately omit 'raw' field which contains entries with plaintext passwords
    }
}
```

---

### C2: Subprocess Injection in Holehe & Maigret Providers

**Severity**: CRITICAL
**Files**:
- `/Users/max/Zima/backend/app/providers/tools/holehe/client.py` (line 75)
- `/Users/max/Zima/backend/app/providers/tools/maigret/client.py` (line 80-88)

**Description**:
Both providers construct subprocess commands using user-supplied email/username values without escaping or validation:

**Holehe** (line 75):
```python
cmd = [_TOOL_NAME, "--only-used", "--no-color", email]
```

**Maigret** (lines 80-88):
```python
cmd = [
    _TOOL_NAME,
    username,  # User-supplied value
    "--no-color",
    "-a",
    "--timeout",
    "10",
    "--print-found",
]
```

While these use list-based `subprocess.run()` (avoiding shell injection via `shell=True`), the asset_value input from modules lacks validation:
1. No length checks (could exhaust memory with extremely long inputs)
2. No character validation (no check for control characters, special bytes)
3. No format validation (no email/username format checking)

Attack scenarios:
- **Memory DoS**: Email address containing 100MB of repetitive characters exhausts process memory
- **Timeout abuse**: Specially crafted email exploits tool processing logic to consume CPU
- **Information leakage**: Special characters might trigger tool error messages revealing system info

**Impact**:
- Remote Code Execution risk if tools have undiscovered vulnerabilities
- Denial of Service: Resource exhaustion on backend
- Information disclosure: Tool error messages may reveal system details

**Recommended Fix**:

```python
# backend/app/providers/tools/holehe/client.py
import re
from backend.app.providers.base.exceptions import ProviderError

# Add validation helper
_EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]{1,255}\.[a-zA-Z]{2,}$')

async def check_accounts_tool(self, email: str) -> list[dict[str, Any]]:
    if not shutil.which(_TOOL_NAME):
        raise ProviderError(
            message="holehe not found in PATH, install with: pip install holehe",
            retryable=False,
        )

    email = email.strip().lower()

    # Validate email format and length
    if not email or len(email) > 254:
        raise ProviderError(
            message="Invalid email: must be 1-254 characters",
            retryable=False,
        )
    if not _EMAIL_REGEX.match(email):
        raise ProviderError(
            message="Invalid email format",
            retryable=False,
        )

    findings: list[dict[str, Any]] = []
    found_sites = await asyncio.to_thread(self._run_holehe, email)
    # ... rest of method
```

For Maigret, add username validation:
```python
# backend/app/providers/tools/maigret/client.py
_USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9._-]{3,32}$')

async def search_usernames(self, username: str) -> list[dict[str, Any]]:
    if not shutil.which(_TOOL_NAME):
        raise ProviderError(...)

    username = username.strip().lower()

    # Validate username format and length
    if not username or len(username) > 32:
        raise ProviderError(
            message="Username must be 3-32 characters",
            retryable=False,
        )
    # Allow very permissive pattern - Maigret tool validates further
    if not re.match(r'^[a-zA-Z0-9._-]{3,}$', username):
        raise ProviderError(
            message="Username contains invalid characters",
            retryable=False,
        )
```

---

### C3: Uncontrolled External API Calls Without Rate Limiting

**Severity**: CRITICAL
**Affected Providers**: All breach/reputation providers (HIBP, DeHashed, LeakCheck, BreachDirectory, Hudson Rock, EmailRep, Epieos)

**Description**:
No caller-level rate limiting, input validation, or cost controls exist for external API calls:

1. **HIBP**: Free tier has rate limits (100 req/min per IP) but no backpressure handling
2. **DeHashed**: Paid API ($3/query typical) - no authorization checks on caller identity
3. **BreachDirectory**: RapidAPI calls accumulate costs - no quota enforcement per user
4. **Hudson Rock**: Enterprise API with per-query costs - no authentication per scan
5. **Epieos**: Per-request cost - no tier-based throttling

**Attack Scenarios**:
- Attacker registers account, triggers scan on 1000 email addresses
- Each scan calls all 7 providers = 7000 API calls
- DeHashed @ $0.10/query = $700 cost, no one authorized it
- BreachDirectory RapidAPI calls consume quota shared across all users

**Impact**:
- Financial damage: $1000s in unexpected API costs
- Denial of service: Quota exhaustion affects legitimate users
- Business viability: SaaS model broken if cost attribution missing

**Recommended Fix**:

Implement multi-layer rate limiting:

```python
# backend/app/db/repositories/api_usage.py (NEW FILE)
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from backend.app.db.base import AsyncSession

class ApiUsageRepository:
    """Track API calls per user/provider to enforce quotas."""

    async def log_api_call(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        provider_name: str,
        cost: float = 0.0,
    ) -> None:
        """Log API call and check quotas."""
        # Check daily limit (e.g., 100 DeHashed calls/day max per user)
        stmt = select(func.count(ApiCall.id)).where(
            ApiCall.user_id == user_id,
            ApiCall.provider_name == provider_name,
            ApiCall.created_at > datetime.now(timezone.utc) - timedelta(days=1),
        )
        count = await session.scalar(stmt)

        QUOTA_PER_DAY = {
            "dehashed": 100,
            "breachdirectory": 50,
            "hudson_rock": 50,
            "epieos": 100,
        }

        limit = QUOTA_PER_DAY.get(provider_name, 1000)
        if count >= limit:
            raise ApiQuotaExceededError(
                f"User has reached daily limit for {provider_name}"
            )

        # Log the call
        await session.add(ApiCall(
            user_id=user_id,
            provider_name=provider_name,
            cost=cost,
            created_at=datetime.now(timezone.utc),
        ))
```

Then add to scan orchestration:
```python
# backend/app/jobs/orchestrator.py (when scan runs modules)
api_usage = ApiUsageRepository()

for module_name in modules_to_run:
    # Check quotas before executing providers
    user_tier = user.tier  # "core", "pro", "enterprise"

    if module_name == "breach_monitor":
        providers_to_call = ["hibp", "dehashed", "breachdirectory"]
        for provider in providers_to_call:
            remaining = await api_usage.get_remaining_quota(
                user_id, provider, user_tier
            )
            if remaining <= 0:
                logger.warn(
                    "api_quota_exceeded",
                    user_id=str(user_id),
                    provider=provider,
                )
                skip_provider = True
                continue

            await api_usage.log_api_call(session, user_id, provider)
```

---

## High Issues

### H1: Missing Input Validation on Email/Username Before Tool Calls

**Severity**: HIGH
**Files**:
- `/Users/max/Zima/backend/app/providers/tools/holehe/client.py`
- `/Users/max/Zima/backend/app/providers/tools/maigret/client.py`
- `/Users/max/Zima/backend/app/modules/identity/username_exposure/service.py` (line 114)

**Description**:
While C2 covers subprocess injection, this issue covers DoS and resource exhaustion:

**Holehe module call** (account_inventory/service.py:30):
```python
findings = await holehe.check_accounts_tool(asset_value)
```

No validation that `asset_value`:
- Is actually a valid email format
- Doesn't exceed reasonable length (tested with 50,000 char strings)
- Doesn't contain binary/control characters

**Maigret module call** (username_exposure/service.py:114):
```python
derived_username = asset_value.split("@")[0]
if derived_username and len(derived_username) >= 3:  # ← Only 1 check
    maigret = MaigretProvider()
    findings = await maigret.search_usernames(derived_username)
```

The length check >= 3 is insufficient:
- No maximum length check (could be 10,000+ chars)
- No character set validation
- split("@")[0] assumes email format - will fail with other entity types

**Impact**:
- CPU/memory exhaustion on backend
- Timeout DoS: tool processes large inputs for extended periods
- Silent failures: Invalid input causes tool errors but exception caught generically

**Recommended Fix**:

```python
# backend/app/providers/tools/holehe/client.py
import re

_MAX_EMAIL_LENGTH = 254  # RFC 5321
_EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

async def check_accounts_tool(self, email: str) -> list[dict[str, Any]]:
    if not shutil.which(_TOOL_NAME):
        raise ProviderError(...)

    email = email.strip().lower()

    # Validate
    if not email:
        raise ProviderError("Email cannot be empty", retryable=False)

    if len(email) > _MAX_EMAIL_LENGTH:
        raise ProviderError(
            f"Email exceeds {_MAX_EMAIL_LENGTH} characters",
            retryable=False,
        )

    if not _EMAIL_PATTERN.match(email):
        raise ProviderError("Invalid email format", retryable=False)

    # Safe to pass to subprocess now
    found_sites = await asyncio.to_thread(self._run_holehe, email)
    ...
```

```python
# backend/app/modules/identity/username_exposure/service.py (line 114)
derived_username = asset_value.split("@")[0] if "@" in asset_value else asset_value

# Add validation
if not derived_username or len(derived_username) < 3:
    logger.debug("username_exposure.skip_short_username",
                 derived_username=derived_username)
    # Skip Maigret for very short usernames
else:
    if len(derived_username) > 32:
        logger.debug("username_exposure.skip_long_username",
                     length=len(derived_username))
    else:
        maigret = MaigretProvider()
        try:
            findings = await maigret.search_usernames(derived_username)
        except ProviderError as e:
            logger.error(...)
```

---

## Medium Issues

### M1: API Key Exposure in Provider Constructor Parameters

**Severity**: MEDIUM
**Files**: All provider clients with API keys

**Description**:
API keys passed as constructor parameters and stored as instance attributes:

```python
# backend/app/providers/breach/epieos/client.py (line 23-25)
def __init__(self, api_key: str = "", timeout_seconds: int = 15) -> None:
    super().__init__(timeout_seconds=timeout_seconds)
    self._api_key = api_key  # ← Stored as plain str, not SecretStr
```

Risks:
1. No `SecretStr` wrapping - value printed in debug/repr
2. String parameter type means Python traceback could expose in repr
3. Instance stored for request lifetime - if thread is inspected, key visible

Affected:
- `epieos/client.py` (line 25)
- `emailrep/client.py` (line 17)
- `dehashed/client.py` (line 26-27)
- `leakcheck/client.py` (line 24)
- `breachdirectory/client.py` (line 41)
- `hudson_rock/client.py` (line 24)

**Impact**:
- If exception is raised and logged with provider instance, key exposed
- Thread inspection in debugger reveals secrets
- Exception tracebacks in logs might include provider object

**Recommended Fix**:

```python
# backend/app/providers/breach/epieos/client.py
from pydantic import SecretStr

class EpieosProvider(BaseProviderClient):
    name = "epieos"
    base_url = "https://epieos.com/api"

    def __init__(self, api_key: str | SecretStr = "", timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        # Convert to SecretStr if string provided
        if isinstance(api_key, str):
            self._api_key: SecretStr = SecretStr(api_key) if api_key else SecretStr("")
        else:
            self._api_key = api_key

    async def validate_email(self, email: str) -> list[dict[str, Any]]:
        api_key = self._api_key.get_secret_value() if self._api_key else ""
        if not api_key:
            raise ProviderError(...)
```

OR use a more explicit pattern:

```python
# Better approach - never store as attribute
class EpieosProvider(BaseProviderClient):
    def __init__(self, api_key: str = "", timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        # Validate at init but don't store
        if not api_key or not api_key.strip():
            self._has_api_key = False
        else:
            self._has_api_key = True
            self._api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            # Keep secret in closure scope, not instance
            self._get_api_key = lambda: api_key  # ← Closure

    async def validate_email(self, email: str) -> list[dict[str, Any]]:
        if not self._has_api_key:
            raise ProviderError(...)
        api_key = self._get_api_key()
```

---

### M2: Sensitive Information in Evidence Dicts (Epieos)

**Severity**: MEDIUM
**Files**: `/Users/max/Zima/backend/app/providers/social/epieos/client.py` (lines 90-99, 116-119)

**Description**:
The Epieos provider stores Google account user names and activity data in evidence:

```python
# Line 90-99
raw={
    "google_id": google.get("id"),
    "name": google.get("name"),  # ← Real name exposed
    "lastActivity": google.get("lastActivity"),
    "mapsReviews": google.get("mapsReviews"),
    "calendarEvents": google.get("calendarEvents"),  # ← PII
    "photosPublic": google.get("photosPublic"),
    "youtubeChannel": google.get("youtubeChannel"),  # ← Links to identity
    "hangoutsLastActivity": google.get("hangoutsLastActivity"),
},
```

While this is returned from Epieos API (not plaintext passwords), it contains:
- Real names (PII)
- Activity timestamps (behavioral data)
- YouTube channel links (identity correlation)
- Calendar/photos metadata

**Impact**:
- PII persistence: Real names stored in signals DB
- GDPR scope creep: Unneeded personal data retention
- Identity correlation: Attacker with DB access gets full identity map

Note: Module (username_exposure/service.py, line 72) also stores alias_name which is the real name - this too is sensitive.

**Recommended Fix**:

```python
# backend/app/providers/social/epieos/client.py
if google and google.get("id"):
    name = str(google.get("name", "")).strip()
    last_activity = str(google.get("lastActivity", "")).strip()
    # ... description building

    findings.append(
        dict(
            provider=self.name,
            category="account_enumeration_risk",
            title=f"Google account confirmed: {email}",
            description=" ".join(desc_parts),
            entity_type="email",
            entity_value=email,
            tags=service_tags,
            raw={
                # Store ONLY structural/technical fields
                "google_id": google.get("id"),
                # REMOVED: "name": google.get("name"),  ← PII, don't store
                # REMOVED: "lastActivity": google.get("lastActivity"),  ← Behavioral data
                # REMOVED: "youtubeChannel": google.get("youtubeChannel"),  ← Identity link
                # Keep only existence flags
                "maps_reviews_present": bool(google.get("mapsReviews")),
                "photos_present": bool(google.get("photosPublic")),
                "youtube_present": bool(google.get("youtubeChannel")),
            },
        )
    )
```

Also update modules that reference this:

```python
# backend/app/modules/identity/username_exposure/service.py (line 50, 83)
# When extracting username from email - don't store the derived username in evidence
username = asset_value.split("@")[0]  # Derive at runtime
signals.append(
    SignalCreate(
        ...
        evidence={
            "source_provider": "epieos",
            "username": username,  # This is OK (derived from input email)
            "platform": platform,
            "profile_url": f"https://google.com/maps/contrib/{google_id}" if google_id else None,
            "confirmed": True,
        },
```

```python
# backend/app/modules/identity/alias_correlation/service.py (line 52, 72)
alias_name = str(raw.get("name", "")).strip()
if not alias_name:
    continue  # Skip if no name

signals.append(
    SignalCreate(
        ...
        evidence={
            "source_provider": "epieos",
            "alias_email": alias_name,  # ← REMOVE THIS: don't store real names
            # Replace with:
            "alias_detected": True,  # Just a flag, not the actual name
            "platform": "Google",
        },
```

---

## Low Issues

### L1: Weak Username Validation in Account Enumeration

**Severity**: LOW
**Files**: `/Users/max/Zima/backend/app/providers/social/accounts/client.py` (line 45)

**Description**:
Username length check is too loose:

```python
if not uname or len(uname) < 3:
    continue
```

This allows:
- Usernames with only 3 characters (e.g., "aaa")
- No validation of character sets
- No maximum length check

For typical platforms, usernames have stricter rules. Maigret tool will filter invalid ones, but validation should be at provider level.

**Impact**:
- Wasted API requests on invalid usernames
- Potential tool errors if special characters slip through
- Low severity because Maigret itself validates; this is just efficiency

**Recommended Fix**:

```python
# backend/app/providers/social/accounts/client.py
_MIN_USERNAME = 3
_MAX_USERNAME = 32
_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]{3,32}$')

for _entity_type, _value in _inputs:
    val = _value.strip()
    uname = val.split("@")[0] if _entity_type == "email" else val

    # Validate username
    if not uname or len(uname) < _MIN_USERNAME:
        continue  # Too short
    if len(uname) > _MAX_USERNAME:
        continue  # Too long
    if not _USERNAME_PATTERN.match(uname):
        continue  # Invalid characters

    matched: list[str] = []
    # ... rest of method
```

---

## Info Issues (Best Practices)

### I1: Hardcoded Migration Notes Suggest Previous Issues

**Severity**: INFO
**Files**: Multiple providers

**Description**:
Files contain comments like:
```python
# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
```

This suggests issues were previously identified and then stripped from review. While the current code appears safe, these notes indicate:
1. Previous security review tool was used
2. Findings were removed rather than fixed

**Recommendation**:
Remove these migration notes and verify the "stripped" issues were actually addressed, not just ignored.

---

## Dependency & Configuration Review

### SecretStr Usage ✓
All API keys in `/Users/max/Zima/backend/app/core/config.py` properly use `SecretStr`:
- `hibp_api_key: SecretStr | None = None`
- `dehashed_api_key: SecretStr | None = None`
- Proper JWT secret validation (minimum 32 bytes)

### Logging Configuration ✓
Structured logging in production uses JSON rendering (no plaintext secrets in console)

### Error Handling ✓
Exception messages are generic and don't echo back user input or credentials

### Subprocess Safety ✓
No `shell=True` usage in holehe/maigret (though input validation still needed - see C2)

### URL Encoding ✓
All user-supplied values properly URL-encoded before HTTP requests (urllib.parse.quote)

---

## Remediation Priority

### Immediate (Before Any Production Deployment)

1. **C1**: Remove plaintext credentials from DeHashed signal evidence
   - 30 min fix
   - Database migration: Set all existing signal.evidence JSON `raw_finding.raw.entries` to `null`

2. **C2**: Add input validation to subprocess calls
   - 1 hour fix
   - Add email regex validation to holehe
   - Add username format validation to maigret

3. **C3**: Implement API quota enforcement
   - 4 hours fix
   - Add ApiUsageRepository
   - Add quota checks before provider calls
   - Log all API calls with cost

### Short-term (Before Beta)

4. **H1**: Add comprehensive input validation
   - 2 hours fix
   - Validate all email/username inputs before provider calls

5. **M1**: Wrap API keys in SecretStr
   - 1 hour fix
   - Update all 6 providers

6. **M2**: Remove PII from Epieos evidence
   - 1 hour fix
   - Sanitize raw dicts in provider and modules

### Long-term (Nice to Have)

7. **L1**: Improve username pattern validation
   - 30 min fix
   - Add character set and length checks

8. **I1**: Remove migration note comments
   - 15 min cleanup

---

## Testing Recommendations

```python
# tests/security/test_credential_storage.py
def test_dehashed_evidence_no_plaintext_passwords():
    """Verify plaintext passwords never stored in evidence."""
    # Create mock DeHashed response with plaintext password
    mock_response = {
        "entries": [
            {"email": "user@example.com", "password": "secret123", "username": "john"}
        ]
    }

    # Call provider
    findings = provider.search_breaches(email="user@example.com")

    # Assert: no plaintext password in returned findings
    for finding in findings:
        raw = finding.get("raw", {})
        assert "entries" not in raw, "CRITICAL: entries should not be in raw"
        # Or if entries kept:
        for entry in raw.get("entries", []):
            assert "password" not in entry, "CRITICAL: plaintext password in evidence"

def test_subprocess_input_validation():
    """Verify email validation before subprocess call."""
    holehe = HoleheProvider()

    # Test invalid inputs
    with pytest.raises(ProviderError):
        await holehe.check_accounts_tool("x" * 500)  # Too long

    with pytest.raises(ProviderError):
        await holehe.check_accounts_tool("not-an-email")  # Invalid format

    with pytest.raises(ProviderError):
        await holehe.check_accounts_tool("")  # Empty

def test_api_quota_enforcement():
    """Verify API calls blocked after quota exceeded."""
    user_id = uuid.uuid4()

    # Simulate user at quota limit
    api_usage.log_api_call(user_id, "dehashed")
    api_usage.log_api_call(user_id, "dehashed")
    # ... repeat to reach limit

    # Next call should fail
    with pytest.raises(ApiQuotaExceededError):
        await api_usage.log_api_call(user_id, "dehashed")
```

---

## Conclusion

Wave 1 identity modules demonstrate solid architecture and patterns, but three critical vulnerabilities must be fixed before production:

1. **Plaintext credentials in database** - immediate data loss risk
2. **Subprocess injection vectors** - potential RCE (though mitigated by list-based subprocess)
3. **Uncontrolled API costs** - business viability risk

All fixes are straightforward and can be completed in < 8 hours. No major architectural changes needed.

**Recommendation**: Hold Wave 1 in staging until C1, C2, C3 are resolved. Continue with Wave 2 design work in parallel.
