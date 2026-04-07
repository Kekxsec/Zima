# backend/app/providers/actions/simplelogin/client.py
"""
SimpleLoginProvider — creates email aliases via the SimpleLogin API.

Design rules:
- Action provider: creates data, does not read/analyze data.
- API key is passed in at construction time (caller retrieves from UserIntegration).
- No severity/confidence logic — action providers only perform actions.
- API base: https://app.simplelogin.io/api
"""

from __future__ import annotations

from pydantic import BaseModel

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderAuthError, ProviderError


class AliasCreated(BaseModel):
    """Result of a successful alias creation."""

    alias: str
    alias_id: int
    mailbox: str
    note: str | None = None


class SimpleLoginProvider(BaseProviderClient):
    """
    Creates per-service email aliases using the SimpleLogin API.

    Caller is responsible for:
    - Retrieving the api_key from UserIntegration (decrypted).
    - Proposing the alias to the user before calling create_alias.

    Reliability: high (official API).
    """

    name = "simplelogin"

    _BASE_URL = "https://app.simplelogin.io/api"

    def __init__(self, api_key: str, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"Authentication": self._api_key}

    async def create_alias(
        self,
        prefix: str,
        mailbox_id: int,
        note: str | None = None,
    ) -> AliasCreated:
        """
        Create a new alias with the given prefix.

        Parameters
        ----------
        prefix:      Alias prefix (e.g. "github-personal").
        mailbox_id:  The SimpleLogin mailbox ID to receive forwarded mail.
        note:        Optional note attached to the alias.

        Returns AliasCreated on success.
        Raises ProviderAuthError on 401, ProviderError on other failures.
        """
        import httpx

        payload: dict = {"alias_prefix": prefix, "mailbox_id": mailbox_id}
        if note:
            payload["note"] = note

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers=self._auth_headers,
            ) as client:
                resp = await client.post(
                    f"{self._BASE_URL}/v3/alias/custom/new",
                    json=payload,
                )
        except Exception as exc:
            raise ProviderError(
                message=f"simplelogin: request failed: {exc}",
                retryable=True,
            ) from exc

        if resp.status_code == 401:
            raise ProviderAuthError(
                message="simplelogin: invalid API key",
                retryable=False,
            )
        if not resp.is_success:
            raise ProviderError(
                message=f"simplelogin: unexpected status {resp.status_code}: {resp.text[:200]}",
                retryable=resp.status_code >= 500,
            )

        data = resp.json()
        return AliasCreated(
            alias=data["alias"],
            alias_id=data["id"],
            mailbox=data.get("mailbox", {}).get("email", ""),
            note=data.get("note"),
        )

    async def list_mailboxes(self) -> list[dict]:
        """
        Return available mailboxes for the account.
        Callers use this to let the user pick which mailbox receives forwarded mail.
        """
        import httpx

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                headers=self._auth_headers,
            ) as client:
                resp = await client.get(f"{self._BASE_URL}/v2/mailboxes")
        except Exception as exc:
            raise ProviderError(
                message=f"simplelogin: request failed: {exc}",
                retryable=True,
            ) from exc

        if resp.status_code == 401:
            raise ProviderAuthError(
                message="simplelogin: invalid API key",
                retryable=False,
            )
        if not resp.is_success:
            raise ProviderError(
                message=f"simplelogin: unexpected status {resp.status_code}",
                retryable=resp.status_code >= 500,
            )

        return resp.json().get("mailboxes", [])
