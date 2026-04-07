# backend/app/providers/tools/bitwarden_export/models.py
from __future__ import annotations

from pydantic import BaseModel


class VaultEntry(BaseModel):
    """
    Minimal account metadata extracted from a single password manager vault item.
    Raw passwords are NEVER stored — only service metadata and the login identity.
    """

    service_name: str
    username: str | None = None
    login_url: str | None = None
    notes: str | None = None
