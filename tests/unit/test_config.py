import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings


def _required_settings() -> dict[str, str]:
    return {
        "secret_key": "a" * 64,
        "database_url": "postgresql+asyncpg://user:pass@localhost:5432/zima",
        "database_url_sync": "postgresql+psycopg://user:pass@localhost:5432/zima",
        "jwt_secret_key": "b" * 64,
    }


def test_ollama_localhost_allowed_by_default() -> None:
    settings = Settings(
        **_required_settings(),
        ollama_enabled=True,
        ollama_base_url="http://localhost:11434",
    )
    assert settings.ollama_base_url == "http://localhost:11434"


def test_ollama_remote_disallowed_by_default() -> None:
    with pytest.raises(
        ValidationError, match="ollama_base_url must point to localhost"
    ):
        Settings(
            **_required_settings(),
            ollama_enabled=True,
            ollama_allow_non_local=False,
            ollama_base_url="http://10.0.0.5:11434",
        )


def test_ollama_remote_allowed_with_explicit_override() -> None:
    settings = Settings(
        **_required_settings(),
        ollama_enabled=True,
        ollama_allow_non_local=True,
        ollama_base_url="http://10.0.0.5:11434",
    )
    assert settings.ollama_allow_non_local is True
