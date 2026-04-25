# backend/app/api/v1/extension.py
"""
Browser extension API — hardening and telemetry endpoints:

  POST /extension/setup-token   User browser → generate short-lived setup token
  POST /extension/register      Extension → exchange token for JWT
  POST /extension/refresh       Extension → rotate JWT before expiry
  POST /extension/heartbeat     Extension → keep connection alive
  POST /extension/snapshot      Extension → submit browser config snapshot
  POST /extension/guide-event   Extension → record guide step completion
  GET  /extension/status        User browser → check connection state
"""

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_current_user,
    get_db_session,
    get_extension_user,
)
from backend.app.auth.models import AuthToken, User
from backend.app.auth.service import match_token
from backend.app.auth.utils import create_extension_token
from backend.app.core.config import settings
from backend.app.core.crypto import (
    CryptoError,
    decrypt_field,
    encrypt_field,
    is_encryption_configured,
)
from backend.app.core.logging import get_logger
from backend.app.core.rate_limit import get_real_ip, limiter
from backend.app.db.models.audit import AuditEventType
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.extension import ExtensionRepository

router = APIRouter(prefix="/extension", tags=["extension"])
logger = get_logger(__name__)

_VALID_BROWSERS = {"chrome", "brave", "firefox", "edge"}
_VALID_PROVIDERS = {"gmail", "outlook", "yahoo", "proton", "fastmail", "apple"}
_RELEVANCE_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
_SNAPSHOT_ENCRYPTED_PAYLOAD_KEY = "__zima_encrypted_snapshot_v1"
_CONNECT_AUDIT_EVENTS = {
    AuditEventType.EXTENSION_SETUP_TOKEN_ISSUED,
    AuditEventType.EXTENSION_REGISTER_SUCCEEDED,
    AuditEventType.EXTENSION_REGISTER_FAILED,
}

_PRIVACY_SETTING_CATALOG: list[dict[str, Any]] = [
    {
        "key": "thirdPartyCookiesAllowed",
        "label": "Third-party cookies",
        "category": "tracking",
        "relevance": "high",
        "rationale": "Blocks cross-site tracking and reduces token leakage across domains.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "doNotTrackEnabled",
        "label": "Do Not Track",
        "category": "tracking",
        "relevance": "medium",
        "rationale": "Advisory signal to sites that tracking should be limited.",
        "recommended": True,
        "hardened": True,
    },
    {
        "key": "hyperlinkAuditingEnabled",
        "label": "Hyperlink auditing (ping)",
        "category": "tracking",
        "relevance": "high",
        "rationale": "Disables hidden ping requests sent when links are clicked.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "referrersEnabled",
        "label": "Referrer headers",
        "category": "network",
        "relevance": "medium",
        "rationale": "Controls whether page URLs are shared to downstream sites.",
        "recommended": True,
        "hardened": False,
    },
    {
        "key": "networkPredictionEnabled",
        "label": "Network prediction",
        "category": "network",
        "relevance": "medium",
        "rationale": "Preconnect and DNS prediction improves speed but increases background requests.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "webRTCIPHandlingPolicy",
        "label": "WebRTC IP handling policy",
        "category": "network",
        "relevance": "high",
        "rationale": "Limits local/public IP exposure in WebRTC sessions.",
        "recommended": "default_public_interface_only",
        "hardened": "disable_non_proxied_udp",
    },
    {
        "key": "passwordSavingEnabled",
        "label": "Built-in password saving",
        "category": "credentials",
        "relevance": "high",
        "rationale": "Disabling favors dedicated password manager workflows.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "autofillAddressEnabled",
        "label": "Address autofill",
        "category": "credentials",
        "relevance": "low",
        "rationale": "Convenience feature that may leak profile data on hostile forms.",
        "recommended": True,
        "hardened": False,
    },
    {
        "key": "autofillCreditCardEnabled",
        "label": "Credit card autofill",
        "category": "credentials",
        "relevance": "high",
        "rationale": "Reduces accidental card-data autofill on lookalike sites.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "safeBrowsingEnabled",
        "label": "Safe Browsing",
        "category": "safe_browsing",
        "relevance": "high",
        "rationale": "Primary phishing and malware URL protection control.",
        "recommended": True,
        "hardened": True,
    },
    {
        "key": "safeBrowsingExtendedReportingEnabled",
        "label": "Safe Browsing extended reporting",
        "category": "safe_browsing",
        "relevance": "low",
        "rationale": "Shares extra telemetry for improved detection but increases data sharing.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "searchSuggestEnabled",
        "label": "Search suggestions",
        "category": "privacy",
        "relevance": "low",
        "rationale": "Can leak partial queries to search provider before submit.",
        "recommended": True,
        "hardened": False,
    },
    {
        "key": "spellingServiceEnabled",
        "label": "Enhanced spell check service",
        "category": "privacy",
        "relevance": "low",
        "rationale": "Cloud spell-check may send typed text snippets to external service.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "translationServiceEnabled",
        "label": "Page translation service",
        "category": "privacy",
        "relevance": "low",
        "rationale": "Translating pages can share page contents with translation provider.",
        "recommended": True,
        "hardened": False,
    },
    {
        "key": "alternateErrorPagesEnabled",
        "label": "Alternate error pages",
        "category": "privacy",
        "relevance": "low",
        "rationale": "Uses web service for navigation error assistance.",
        "recommended": True,
        "hardened": False,
    },
    {
        "key": "adMeasurementEnabled",
        "label": "Privacy Sandbox ad measurement",
        "category": "privacy_sandbox",
        "relevance": "medium",
        "rationale": "Controls browser-level ad conversion measurement features.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "fledgeEnabled",
        "label": "Privacy Sandbox interest groups (FLEDGE)",
        "category": "privacy_sandbox",
        "relevance": "medium",
        "rationale": "Controls browser-managed interest-group ad features.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "relatedWebsiteSetsEnabled",
        "label": "Related Website Sets",
        "category": "privacy_sandbox",
        "relevance": "medium",
        "rationale": "Allows approved cross-site relationships for storage and cookies.",
        "recommended": False,
        "hardened": False,
    },
    {
        "key": "topicsEnabled",
        "label": "Privacy Sandbox Topics API",
        "category": "privacy_sandbox",
        "relevance": "medium",
        "rationale": "Controls sharing of coarse browser interest topics with sites.",
        "recommended": False,
        "hardened": False,
    },
]


# ─── Schemas ─────────────────────────────────────────────────────────────────


class SetupTokenResponse(BaseModel):
    setup_token: str
    expires_in: int  # seconds
    user_id: str


class RegisterRequest(BaseModel):
    setup_token: str
    user_id: uuid.UUID
    browser: str  # "chrome" | "brave" | "firefox" | "edge"
    version: str  # semver e.g. "1.0.0"


class RegisterResponse(BaseModel):
    extension_token: str
    expires_in: int
    expires_at: str


class RefreshResponse(BaseModel):
    extension_token: str
    expires_in: int
    expires_at: str


class SnapshotRequest(BaseModel):
    raw_snapshot: dict[str, object]


class GuideEventRequest(BaseModel):
    provider: str  # "gmail" | "outlook" | "yahoo" | "proton" | "fastmail" | "apple"
    step: str  # "started" | "step_1" | ... | "mbox_downloaded"


class ExtensionStatusResponse(BaseModel):
    connected: bool
    last_seen_at: str | None
    browser: str | None
    version: str | None
    latest_snapshot_at: str | None
    snapshot_encrypted: bool
    installed_extension_count: int
    guide_completions: dict[str, bool]
    installed_extensions: list["InstalledExtensionSummary"]
    privacy_settings: dict[str, Any]
    privacy_settings_mapped: list["PrivacySettingMapped"]
    recent_guide_events: list["GuideEventSummary"]
    recent_connect_attempts: list["ConnectAttemptSummary"]


class InstalledExtensionSummary(BaseModel):
    id: str
    name: str
    version: str
    enabled: bool


class GuideEventSummary(BaseModel):
    provider: str
    step: str
    created_at: str


class ConnectAttemptSummary(BaseModel):
    event_type: str
    outcome: str
    reason: str | None
    browser: str | None
    extension_version: str | None
    ip_address: str | None
    created_at: str


class PrivacySettingMapped(BaseModel):
    key: str
    label: str
    category: str
    relevance: str
    rationale: str
    recommended_value: Any | None
    hardened_value: Any | None
    current_value: Any | None
    level_of_control: str | None
    available: bool
    error: str | None


ExtensionStatusResponse.model_rebuild()


async def _log_extension_audit(
    db: AsyncSession,
    event_type: str,
    *,
    request: Request | None = None,
    user_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Best-effort audit logging for extension connect/setup activity.
    Never raises so security logging cannot break user-facing flows.
    """
    try:
        audit_repo = AuditRepository(db)
        event_metadata = dict(metadata or {})
        if request is not None:
            user_agent = request.headers.get("user-agent")
            if user_agent:
                event_metadata["user_agent"] = user_agent[:512]
        await audit_repo.log(
            event_type=event_type,
            user_id=user_id,
            ip_address=get_real_ip(request) if request is not None else None,
            metadata=event_metadata,
        )
    except Exception as exc:
        logger.warning(
            "extension.audit_log_failed",
            event_type=event_type,
            error=str(exc),
        )


def _snapshot_is_encrypted(raw_snapshot: dict[str, Any]) -> bool:
    encrypted_payload = raw_snapshot.get(_SNAPSHOT_ENCRYPTED_PAYLOAD_KEY)
    return isinstance(encrypted_payload, str) and bool(encrypted_payload)


def _serialize_snapshot_for_storage(raw_snapshot: dict[str, object]) -> dict[str, Any]:
    """
    Encrypt snapshot payload when field encryption is configured.
    Falls back to plaintext JSON in development/test when no key is configured.
    """
    if not is_encryption_configured():
        return dict(raw_snapshot)

    serialized = json.dumps(raw_snapshot, separators=(",", ":"), sort_keys=True)
    encrypted = encrypt_field(serialized)
    return {_SNAPSHOT_ENCRYPTED_PAYLOAD_KEY: encrypted}


def _deserialize_snapshot_from_storage(raw_snapshot: dict[str, Any]) -> dict[str, Any]:
    if not _snapshot_is_encrypted(raw_snapshot):
        return raw_snapshot

    encrypted_payload = raw_snapshot.get(_SNAPSHOT_ENCRYPTED_PAYLOAD_KEY)
    if not isinstance(encrypted_payload, str) or not encrypted_payload:
        return {}

    try:
        decrypted = decrypt_field(encrypted_payload)
        decoded = json.loads(decrypted)
    except (CryptoError, ValueError, TypeError) as exc:
        logger.warning("extension.snapshot_decrypt_failed", error=str(exc))
        return {}

    if not isinstance(decoded, dict):
        return {}
    return {str(key): value for key, value in decoded.items()}


def _map_connect_attempt(
    event_type: str, metadata: dict[str, Any]
) -> tuple[str, str | None]:
    if event_type == AuditEventType.EXTENSION_SETUP_TOKEN_ISSUED:
        return "issued", None
    if event_type == AuditEventType.EXTENSION_REGISTER_SUCCEEDED:
        return "success", None
    reason = metadata.get("reason")
    if isinstance(reason, str):
        return "failed", reason
    return "failed", None


def _extract_installed_extensions(
    raw_snapshot: dict[str, Any],
) -> list[InstalledExtensionSummary]:
    raw_extensions = raw_snapshot.get("extensions")
    if not isinstance(raw_extensions, list):
        return []

    extensions: list[InstalledExtensionSummary] = []
    for item in raw_extensions:
        if not isinstance(item, dict):
            continue
        ext_id = item.get("id")
        name = item.get("name")
        version = item.get("version")
        enabled = item.get("enabled")
        if not isinstance(ext_id, str) or not isinstance(name, str):
            continue
        if not isinstance(version, str) or not isinstance(enabled, bool):
            continue
        extensions.append(
            InstalledExtensionSummary(
                id=ext_id,
                name=name,
                version=version,
                enabled=enabled,
            )
        )
    return extensions


def _extract_privacy_settings(raw_snapshot: dict[str, Any]) -> dict[str, Any]:
    raw_privacy = raw_snapshot.get("privacySettings")
    if not isinstance(raw_privacy, dict):
        raw_privacy = raw_snapshot.get("privacy_settings")
    if not isinstance(raw_privacy, dict):
        return {}
    # Keep keys stable and JSON-safe for frontend display.
    return {str(key): value for key, value in raw_privacy.items()}


def _extract_setting_state(
    raw_privacy: dict[str, Any], key: str
) -> tuple[Any | None, str | None, bool, str | None]:
    if key not in raw_privacy:
        return None, None, False, None

    raw_entry = raw_privacy.get(key)
    if isinstance(raw_entry, dict):
        value = raw_entry.get("value")
        level = raw_entry.get("levelOfControl")
        error = raw_entry.get("error")
        return (
            value,
            level if isinstance(level, str) else None,
            "value" in raw_entry or "error" in raw_entry,
            error if isinstance(error, str) else None,
        )

    return raw_entry, None, True, None


def _map_privacy_settings(raw_privacy: dict[str, Any]) -> list[PrivacySettingMapped]:
    mapped: list[PrivacySettingMapped] = []
    for entry in _PRIVACY_SETTING_CATALOG:
        key = str(entry["key"])
        value, level, available, error = _extract_setting_state(raw_privacy, key)
        mapped.append(
            PrivacySettingMapped(
                key=key,
                label=str(entry["label"]),
                category=str(entry["category"]),
                relevance=str(entry["relevance"]),
                rationale=str(entry["rationale"]),
                recommended_value=entry.get("recommended"),
                hardened_value=entry.get("hardened"),
                current_value=value,
                level_of_control=level,
                available=available,
                error=error,
            )
        )
    mapped.sort(
        key=lambda item: (
            _RELEVANCE_ORDER.get(item.relevance, 99),
            item.category,
            item.label,
        )
    )
    return mapped


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/setup-token", response_model=SetupTokenResponse)
@limiter.limit(settings.extension_setup_token_rate_limit)
async def create_setup_token(
    request: Request,  # required by slowapi
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SetupTokenResponse:
    """
    Generates a one-time setup token for the browser extension.
    The extension exchanges this token for a long-lived JWT on first install.
    Token expires in 15 minutes.
    """
    raw_token = secrets.token_urlsafe(32)
    code_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    key = f"extension_setup:{current_user.id}"
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.extension_setup_token_expire_minutes
    )

    token_repo = AuthTokenRepository(db)
    token = AuthToken(
        email=key,
        code_hash=code_hash,
        expires_at=expires_at,
    )
    await token_repo.create(token)
    await _log_extension_audit(
        db,
        AuditEventType.EXTENSION_SETUP_TOKEN_ISSUED,
        request=request,
        user_id=current_user.id,
        metadata={
            "expires_in_seconds": settings.extension_setup_token_expire_minutes * 60,
        },
    )
    await db.commit()

    return SetupTokenResponse(
        setup_token=raw_token,
        expires_in=settings.extension_setup_token_expire_minutes * 60,
        user_id=str(current_user.id),
    )


@router.post("/register", response_model=RegisterResponse)
@limiter.limit(settings.extension_register_rate_limit)
async def register_extension(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RegisterResponse:
    """
    Exchanges a setup token for a long-lived extension JWT.
    Called once by the extension on first install / reconnect.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired setup token.",
    )

    if body.browser not in _VALID_BROWSERS:
        await _log_extension_audit(
            db,
            AuditEventType.EXTENSION_REGISTER_FAILED,
            request=request,
            user_id=body.user_id,
            metadata={
                "browser": body.browser,
                "extension_version": body.version,
                "reason": "invalid_browser",
            },
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"browser must be one of: {', '.join(sorted(_VALID_BROWSERS))}",
        )

    key = f"extension_setup:{body.user_id}"
    incoming_hash = hashlib.sha256(body.setup_token.encode()).hexdigest()

    token_repo = AuthTokenRepository(db)
    active_tokens = await token_repo.list_active_for_email(key)
    auth_token = match_token(active_tokens, incoming_hash)
    if auth_token is None:
        await _log_extension_audit(
            db,
            AuditEventType.EXTENSION_REGISTER_FAILED,
            request=request,
            user_id=body.user_id,
            metadata={
                "browser": body.browser,
                "extension_version": body.version,
                "reason": "invalid_or_expired_setup_token",
            },
        )
        await db.commit()
        raise credentials_exception

    # Timing-safe comparison against the stored hash
    if not hmac.compare_digest(auth_token.code_hash, incoming_hash):
        await _log_extension_audit(
            db,
            AuditEventType.EXTENSION_REGISTER_FAILED,
            request=request,
            user_id=body.user_id,
            metadata={
                "browser": body.browser,
                "extension_version": body.version,
                "reason": "setup_token_hash_mismatch",
            },
        )
        await db.commit()
        raise credentials_exception

    # Atomic replay protection — reject if already consumed
    if auth_token.used_at is not None:
        await _log_extension_audit(
            db,
            AuditEventType.EXTENSION_REGISTER_FAILED,
            request=request,
            user_id=body.user_id,
            metadata={
                "browser": body.browser,
                "extension_version": body.version,
                "reason": "setup_token_already_used",
            },
        )
        await db.commit()
        raise credentials_exception
    auth_token.used_at = datetime.now(UTC)

    jti = str(uuid.uuid4())
    extension_repo = ExtensionRepository(db)
    session = await extension_repo.upsert_session(
        user_id=body.user_id,
        browser=body.browser,
        version=body.version,
        jti=jti,
    )
    await _log_extension_audit(
        db,
        AuditEventType.EXTENSION_REGISTER_SUCCEEDED,
        request=request,
        user_id=body.user_id,
        metadata={
            "browser": body.browser,
            "extension_version": body.version,
        },
    )
    await db.commit()

    expires_in = settings.extension_token_expire_minutes * 60
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    extension_token = create_extension_token(
        user_id=str(body.user_id),
        session_id=str(session.id),
        jti=jti,
        expire_minutes=settings.extension_token_expire_minutes,
    )

    return RegisterResponse(
        extension_token=extension_token,
        expires_in=expires_in,
        expires_at=expires_at.isoformat(),
    )


@router.post("/refresh", response_model=RefreshResponse)
@limiter.limit(settings.extension_refresh_rate_limit)
async def refresh_extension_token(
    request: Request,  # required by slowapi
    current_user: User = Depends(get_extension_user),
    db: AsyncSession = Depends(get_db_session),
) -> RefreshResponse:
    """
    Rotates extension JWT before expiry.
    Requires a currently valid extension token.
    """
    extension_repo = ExtensionRepository(db)
    session = await extension_repo.get_session_by_user(current_user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extension session found for this user.",
        )

    jti = str(uuid.uuid4())
    await extension_repo.rotate_session_jti(session.id, jti)
    await db.commit()

    expires_in = settings.extension_token_expire_minutes * 60
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)
    extension_token = create_extension_token(
        user_id=str(current_user.id),
        session_id=str(session.id),
        jti=jti,
        expire_minutes=settings.extension_token_expire_minutes,
    )
    return RefreshResponse(
        extension_token=extension_token,
        expires_in=expires_in,
        expires_at=expires_at.isoformat(),
    )


@router.post("/heartbeat", status_code=202)
async def post_heartbeat(
    current_user: User = Depends(get_extension_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Lightweight keepalive so /extension/status can detect stale disconnects.
    """
    extension_repo = ExtensionRepository(db)
    session = await extension_repo.get_session_by_user(current_user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extension session found for this user.",
        )

    await extension_repo.update_last_seen(session.id)
    await db.commit()
    return {"status": "accepted"}


@router.post("/snapshot", status_code=202)
async def post_snapshot(
    body: SnapshotRequest,
    current_user: User = Depends(get_extension_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Accepts a browser config snapshot from the extension.
    Payload is unstructured JSONB — schema evolves with the extension version.
    """
    extension_repo = ExtensionRepository(db)
    session = await extension_repo.get_session_by_user(current_user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extension session found for this user.",
        )

    await extension_repo.update_last_seen(session.id)
    snapshot_for_storage = _serialize_snapshot_for_storage(body.raw_snapshot)
    await extension_repo.insert_snapshot(
        user_id=current_user.id,
        session_id=session.id,
        raw=snapshot_for_storage,
    )
    await db.commit()

    return {"status": "accepted"}


@router.post("/guide-event", status_code=202)
async def post_guide_event(
    body: GuideEventRequest,
    current_user: User = Depends(get_extension_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Records a step in an in-extension mbox export guide.
    The frontend polls /extension/status to detect when 'mbox_downloaded' is reached.
    """
    if body.provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"provider must be one of: {', '.join(sorted(_VALID_PROVIDERS))}",
        )

    extension_repo = ExtensionRepository(db)
    session = await extension_repo.get_session_by_user(current_user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No extension session found for this user.",
        )

    await extension_repo.insert_guidance_event(
        user_id=current_user.id,
        session_id=session.id,
        provider=body.provider,
        step=body.step,
    )
    await db.commit()

    return {"status": "accepted"}


@router.get("/status", response_model=ExtensionStatusResponse)
async def get_extension_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ExtensionStatusResponse:
    """
    Returns connection state and guide completion status.
    Polled by the frontend. A session is stale if last_seen_at > 10 minutes ago.
    """
    extension_repo = ExtensionRepository(db)
    session = await extension_repo.get_session_by_user(current_user.id)

    if session is None:
        return ExtensionStatusResponse(
            connected=False,
            last_seen_at=None,
            browser=None,
            version=None,
            latest_snapshot_at=None,
            snapshot_encrypted=False,
            installed_extension_count=0,
            guide_completions=dict.fromkeys(_VALID_PROVIDERS, False),
            installed_extensions=[],
            privacy_settings={},
            privacy_settings_mapped=[],
            recent_guide_events=[],
            recent_connect_attempts=[],
        )

    stale_threshold = timedelta(minutes=10)
    is_stale = (datetime.now(UTC) - session.last_seen_at) > stale_threshold

    snapshot = await extension_repo.get_latest_snapshot(current_user.id)
    installed_extensions: list[InstalledExtensionSummary] = []
    privacy_settings: dict[str, Any] = {}
    latest_snapshot_at: str | None = None
    snapshot_encrypted = False
    if snapshot is not None:
        raw = snapshot.raw_snapshot or {}
        snapshot_encrypted = _snapshot_is_encrypted(raw)
        raw = _deserialize_snapshot_from_storage(raw)
        installed_extensions = _extract_installed_extensions(raw)
        privacy_settings = _extract_privacy_settings(raw)
        latest_snapshot_at = snapshot.created_at.isoformat()

    installed_extension_count = len(installed_extensions)
    privacy_settings_mapped = _map_privacy_settings(privacy_settings)

    guide_completions = {
        provider: await extension_repo.get_guide_completion(current_user.id, provider)
        for provider in _VALID_PROVIDERS
    }
    recent_events = await extension_repo.list_recent_guidance_events(
        current_user.id, limit=50
    )
    recent_guide_events = [
        GuideEventSummary(
            provider=event.provider,
            step=event.step,
            created_at=event.created_at.isoformat(),
        )
        for event in recent_events
    ]
    audit_repo = AuditRepository(db)
    connect_events = await audit_repo.get_for_user_by_event_types(
        current_user.id,
        event_types=sorted(_CONNECT_AUDIT_EVENTS),
        limit=20,
    )
    recent_connect_attempts = []
    for event in connect_events:
        metadata = (
            event.event_metadata if isinstance(event.event_metadata, dict) else {}
        )
        outcome, reason = _map_connect_attempt(event.event_type, metadata)
        browser = metadata.get("browser")
        version = metadata.get("extension_version")
        recent_connect_attempts.append(
            ConnectAttemptSummary(
                event_type=event.event_type,
                outcome=outcome,
                reason=reason,
                browser=browser if isinstance(browser, str) else None,
                extension_version=version if isinstance(version, str) else None,
                ip_address=event.ip_address,
                created_at=event.created_at.isoformat(),
            )
        )

    return ExtensionStatusResponse(
        connected=not is_stale,
        last_seen_at=session.last_seen_at.isoformat(),
        browser=session.browser,
        version=session.extension_version,
        latest_snapshot_at=latest_snapshot_at,
        snapshot_encrypted=snapshot_encrypted,
        installed_extension_count=installed_extension_count,
        guide_completions=guide_completions,
        installed_extensions=installed_extensions,
        privacy_settings=privacy_settings,
        privacy_settings_mapped=privacy_settings_mapped,
        recent_guide_events=recent_guide_events,
        recent_connect_attempts=recent_connect_attempts,
    )
