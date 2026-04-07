# backend/app/api/v1/integrations.py
"""
User integration management endpoints.

GET    /integrations                      — List connected providers
PUT    /integrations/{provider}           — Connect or update an integration
DELETE /integrations/{provider}           — Disconnect an integration
GET    /integrations/simplelogin/mailboxes — List SimpleLogin mailboxes
GET    /integrations/addy_io/account      — Get Addy.io account details
POST   /integrations/{provider}/verify    — Verify API key is valid
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.core.crypto import CryptoError, decrypt_field, encrypt_field
from backend.app.db.models.integrations import IntegrationProvider
from backend.app.db.repositories.user_integrations import UserIntegrationRepository
from backend.app.providers.actions.addy_io.client import AddyIoProvider
from backend.app.providers.actions.simplelogin.client import SimpleLoginProvider
from backend.app.providers.base.exceptions import ProviderAuthError, ProviderError

router = APIRouter(prefix="/integrations", tags=["integrations"])

_VALID_PROVIDERS: frozenset[str] = frozenset(
    {IntegrationProvider.SIMPLELOGIN, IntegrationProvider.ADDY_IO}
)


class ConnectIntegrationRequest(BaseModel):
    api_key: str


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get("", status_code=200)
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Return which providers the current user has connected (no key material)."""
    repo = UserIntegrationRepository(db)
    connected: list[dict[str, object]] = []

    for provider in sorted(_VALID_PROVIDERS):
        record = await repo.get(user_id=current_user.id, provider=provider)
        connected.append(
            {
                "provider": provider,
                "connected": record is not None,
                "connected_at": (
                    record.created_at.isoformat() if record is not None else None
                ),
            }
        )

    return {"integrations": connected}


# ---------------------------------------------------------------------------
# Connect / update
# ---------------------------------------------------------------------------


@router.put("/{provider}", status_code=200)
async def connect_integration(
    provider: str,
    body: ConnectIntegrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Connect or update an integration.

    The API key is encrypted at rest using AES-256-GCM before storage.
    The plaintext key is never persisted.
    """
    _validate_provider(provider)

    api_key = body.api_key.strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key must not be empty.",
        )

    try:
        ciphertext = encrypt_field(api_key)
    except CryptoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Encryption service unavailable. Contact support.",
        ) from exc

    repo = UserIntegrationRepository(db)
    await repo.upsert(
        user_id=current_user.id,
        provider=provider,
        api_key_ciphertext=ciphertext,
    )
    await db.commit()

    return {"provider": provider, "connected": True}


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------


@router.delete("/{provider}", status_code=200)
async def disconnect_integration(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """Remove the stored API key for a provider."""
    _validate_provider(provider)

    repo = UserIntegrationRepository(db)
    record = await repo.get(user_id=current_user.id, provider=provider)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider} integration found.",
        )

    await repo.delete(user_id=current_user.id, provider=provider)
    await db.commit()

    return {"provider": provider, "connected": False}


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


@router.post("/{provider}/verify", status_code=200)
async def verify_integration(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Verify the stored API key is still valid by making a lightweight API call.

    Returns {"valid": true/false, "detail": "..."}.
    """
    _validate_provider(provider)

    api_key = await _get_decrypted_key(provider, current_user.id, db)

    try:
        if provider == IntegrationProvider.SIMPLELOGIN:
            sl = SimpleLoginProvider(api_key=api_key)
            await sl.list_mailboxes()
        elif provider == IntegrationProvider.ADDY_IO:
            addy = AddyIoProvider(api_key=api_key)
            await addy.get_account_details()
    except ProviderAuthError:
        return {"valid": False, "detail": "API key was rejected by the provider."}
    except ProviderError as exc:
        return {
            "valid": False,
            "detail": f"Provider request failed: {exc.message}",
        }

    return {"valid": True, "detail": "API key is valid."}


# ---------------------------------------------------------------------------
# SimpleLogin — list mailboxes
# ---------------------------------------------------------------------------


@router.get("/simplelogin/mailboxes", status_code=200)
async def list_simplelogin_mailboxes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Return the SimpleLogin mailboxes available to the user.

    Requires a connected SimpleLogin integration.
    """
    api_key = await _get_decrypted_key(
        IntegrationProvider.SIMPLELOGIN, current_user.id, db
    )

    try:
        sl = SimpleLoginProvider(api_key=api_key)
        mailboxes = await sl.list_mailboxes()
    except ProviderAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SimpleLogin API key is invalid or expired.",
        ) from exc
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SimpleLogin request failed: {exc.message}",
        ) from exc

    return {"mailboxes": mailboxes}


# ---------------------------------------------------------------------------
# Addy.io — account details
# ---------------------------------------------------------------------------


@router.get("/addy_io/account", status_code=200)
async def get_addy_io_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    """
    Return addy.io account details (username, default recipient, bandwidth).

    Requires a connected addy_io integration.
    """
    api_key = await _get_decrypted_key(IntegrationProvider.ADDY_IO, current_user.id, db)

    try:
        addy = AddyIoProvider(api_key=api_key)
        details = await addy.get_account_details()
    except ProviderAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Addy.io API key is invalid or expired.",
        ) from exc
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Addy.io request failed: {exc.message}",
        ) from exc

    return {"account": details}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_provider(provider: str) -> None:
    if provider not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unknown provider '{provider}'. "
                f"Valid values: {', '.join(sorted(_VALID_PROVIDERS))}."
            ),
        )


async def _get_decrypted_key(
    provider: str,
    user_id: object,
    db: AsyncSession,
) -> str:
    """Retrieve and decrypt the API key for a provider, or raise 404."""

    repo = UserIntegrationRepository(db)
    record = await repo.get(user_id=user_id, provider=provider)  # type: ignore[arg-type]
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No {provider} integration found. "
                f"Connect it first via PUT /integrations/{provider}."
            ),
        )

    try:
        return decrypt_field(record.api_key_ciphertext)
    except CryptoError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt stored API key.",
        ) from exc
