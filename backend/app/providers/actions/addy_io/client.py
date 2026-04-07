# backend/app/providers/actions/addy_io/client.py
"""
AddyIoProvider — creates email aliases via the addy.io (AnonAddy) API.

Design rules:
- Action provider: creates data, does not read/analyze data.
- API key is passed in at construction time (caller retrieves from UserIntegration).
- No severity/confidence logic.
- API base: https://app.addy.io/api/v1
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderAuthError, ProviderError


class AliasCreated(BaseModel):
    """Result of a successful alias creation."""

    alias: str
    alias_id: str
    local_part: str
    domain: str
    description: str | None = None


class AddyIoProvider(BaseProviderClient):
    """
    Creates per-service email aliases using the addy.io API.

    Caller is responsible for:
    - Retrieving the api_key from UserIntegration (decrypted).
    - Proposing the alias to the user before calling create_alias.

    Reliability: high (official API).
    """

    name = "addy_io"

    _BASE_URL = "https://app.addy.io/api/v1"

    def __init__(self, api_key: str, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }

    async def create_alias(
        self,
        domain: str,
        description: str | None = None,
        local_part: str | None = None,
    ) -> AliasCreated:
        """
        Create a new alias.

        Parameters
        ----------
        domain:       The addy.io domain to create the alias under
                      (e.g. "anonaddy.me", or a custom domain).
        description:  Optional human-readable description (e.g. "GitHub alias").
        local_part:   Optional specific local part (e.g. "github-personal").
                      If omitted, addy.io generates a random UUID alias.

        Returns AliasCreated on success.
        Raises ProviderAuthError on 401, ProviderError on other failures.
        """
        import httpx

        payload: dict = {"domain": domain}
        if description:
            payload["description"] = description
        if local_part:
            payload["local_part"] = local_part

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers=self._auth_headers,
            ) as client:
                resp = await client.post(
                    f"{self._BASE_URL}/aliases",
                    json=payload,
                )
        except Exception as exc:
            raise ProviderError(
                message=f"addy_io: request failed: {exc}",
                retryable=True,
            ) from exc

        if resp.status_code == 401:
            raise ProviderAuthError(
                message="addy_io: invalid API key",
                retryable=False,
            )
        if not resp.is_success:
            raise ProviderError(
                message=f"addy_io: unexpected status {resp.status_code}: {resp.text[:200]}",
                retryable=resp.status_code >= 500,
            )

        data = resp.json().get("data", {})
        return AliasCreated(
            alias=data["email"],
            alias_id=data["id"],
            local_part=data.get("local_part", ""),
            domain=data.get("domain", domain),
            description=data.get("description"),
        )

    async def get_account_details(self) -> dict:
        """Return account details (username, default recipient, etc.)."""
        import httpx

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers=self._auth_headers,
            ) as client:
                resp = await client.get(f"{self._BASE_URL}/account-details")
        except Exception as exc:
            raise ProviderError(
                message=f"addy_io: request failed: {exc}",
                retryable=True,
            ) from exc

        if resp.status_code == 401:
            raise ProviderAuthError(
                message="addy_io: invalid API key",
                retryable=False,
            )
        if not resp.is_success:
            raise ProviderError(
                message=f"addy_io: unexpected status {resp.status_code}",
                retryable=resp.status_code >= 500,
            )

        return resp.json().get("data", {})
