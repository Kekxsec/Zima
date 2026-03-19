# backend/app/core/config.py
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    secret_key: SecretStr

    # Database
    database_url: str
    database_url_sync: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # CORS — loaded from environment, never hardcoded
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, v: SecretStr) -> SecretStr:
        """Enforce minimum entropy — HS256 requires at least 32 bytes.
        Generate: python -c "import secrets; print(secrets.token_hex(32))"
        """
        if len(v.get_secret_value()) < 32:
            raise ValueError(
                "jwt_secret_key must be at least 32 characters. "
                "Generate: python -c "
                '"import secrets; print(secrets.token_hex(32))"'
            )
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Guard against unsafe defaults reaching production."""
        if self.app_env == "production":
            for origin in self.cors_allowed_origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(
                        f"CORS origin '{origin}' contains localhost which is not "
                        "permitted in production. Set CORS_ALLOWED_ORIGINS to your "
                        "production frontend URL(s)."
                    )
        return self

    # Email
    resend_api_key: SecretStr | None = None
    email_from_address: str = "noreply@yourdomain.com"
    email_from_name: str = "Zima"

    # Stripe
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_shield_monthly: str | None = None
    stripe_price_pro_monthly: str | None = None

    # Providers
    hibp_api_key: SecretStr | None = None

    # Tier
    default_tier: str = "core"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


settings = Settings()  # type: ignore[call-arg]  # required fields loaded from env at runtime
