# tests/unit/providers/test_vault_export_providers.py
import io
import json
import zipfile

from backend.app.providers.tools.bitwarden_export.client import BitwardenExportProvider
from backend.app.providers.tools.onepassword_export.client import (
    OnePasswordExportProvider,
)
from backend.app.providers.tools.proton_pass_export.client import (
    ProtonPassExportProvider,
)


def test_bitwarden_provider_parses_login_items() -> None:
    provider = BitwardenExportProvider()
    payload = {
        "encrypted": False,
        "items": [
            {
                "type": 1,
                "name": "GitHub",
                "notes": "Primary developer account",
                "login": {
                    "username": "user@example.com",
                    "uris": [{"uri": "https://github.com/login"}],
                },
            },
            {
                "type": 2,
                "name": "Secure note",
            },
        ],
    }

    entries = provider.parse(json.dumps(payload).encode())

    assert len(entries) == 1
    assert entries[0].service_name == "GitHub"
    assert entries[0].username == "user@example.com"
    assert entries[0].login_url == "https://github.com/login"
    assert entries[0].notes == "Primary developer account"


def test_bitwarden_provider_rejects_encrypted_export() -> None:
    provider = BitwardenExportProvider()

    entries = provider.parse(json.dumps({"encrypted": True, "items": []}).encode())

    assert entries == []


def test_proton_pass_provider_parses_active_login_items() -> None:
    provider = ProtonPassExportProvider()
    payload = {
        "vaults": {
            "primary": {
                "items": [
                    {
                        "state": 1,
                        "data": {
                            "type": "login",
                            "metadata": {
                                "name": "Linear",
                                "note": "Workspace login",
                            },
                            "content": {
                                "itemEmail": "user@example.com",
                                "urls": ["https://linear.app/login"],
                            },
                        },
                    },
                    {
                        "state": 2,
                        "data": {"type": "login", "metadata": {"name": "Old App"}},
                    },
                ]
            }
        }
    }

    entries = provider.parse(json.dumps(payload).encode())

    assert len(entries) == 1
    assert entries[0].service_name == "Linear"
    assert entries[0].username == "user@example.com"
    assert entries[0].login_url == "https://linear.app/login"
    assert entries[0].notes == "Workspace login"


def test_proton_pass_provider_returns_empty_for_invalid_json() -> None:
    provider = ProtonPassExportProvider()

    entries = provider.parse(b"{not-json")

    assert entries == []


def test_onepassword_provider_parses_1pux_export() -> None:
    provider = OnePasswordExportProvider()
    export_data = {
        "accounts": [
            {
                "vaults": [
                    {
                        "items": [
                            {
                                "categoryUuid": "001",
                                "state": "active",
                                "overview": {
                                    "title": "Figma",
                                    "urls": [{"u": "https://www.figma.com/login"}],
                                },
                                "details": {
                                    "loginFields": [
                                        {
                                            "designation": "username",
                                            "value": "designer@example.com",
                                        }
                                    ],
                                    "notesPlain": "Design workspace",
                                },
                            }
                        ]
                    }
                ]
            }
        ]
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("export.data", json.dumps(export_data))

    entries = provider.parse(buffer.getvalue())

    assert len(entries) == 1
    assert entries[0].service_name == "Figma"
    assert entries[0].username == "designer@example.com"
    assert entries[0].login_url == "https://www.figma.com/login"
    assert entries[0].notes == "Design workspace"


def test_onepassword_provider_rejects_missing_export_data() -> None:
    provider = OnePasswordExportProvider()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("wrong.json", "{}")

    entries = provider.parse(buffer.getvalue())

    assert entries == []
