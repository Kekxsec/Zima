# backend/app/core/config.py
from typing import Literal
from urllib.parse import urlparse

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
    jwt_algorithm: Literal["HS256", "HS512"] = "HS256"
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
            if self.debug:
                raise ValueError(
                    "DEBUG must be False in production. "
                    "Set APP_ENV=production only when DEBUG is not set or is false."
                )

            for origin in self.cors_allowed_origins:
                if "localhost" in origin or "127.0.0.1" in origin:
                    raise ValueError(
                        f"CORS origin '{origin}' contains localhost which is not "
                        "permitted in production. Set CORS_ALLOWED_ORIGINS to your "
                        "production frontend URL(s)."
                    )

            # TLS enforcement — fail closed in production.
            if self.require_tls_postgres and "sslmode=" not in self.database_url:
                raise ValueError(
                    "Production database_url must include sslmode= parameter "
                    "(e.g. sslmode=require). Set REQUIRE_TLS_POSTGRES=false only "
                    "for trusted private networks with documented risk acceptance."
                )
            if self.require_tls_redis and not self.redis_url.startswith("rediss://"):
                raise ValueError(
                    "Production redis_url must use rediss:// (TLS). "
                    "Set REQUIRE_TLS_REDIS=false only for trusted private networks "
                    "with documented risk acceptance."
                )

            # Field encryption should be configured in production.
            if self.field_encryption_key is None:
                raise ValueError(
                    "FIELD_ENCRYPTION_KEY must be set in production. "
                    'Generate: python -c "import secrets; print(secrets.token_hex(32))"'
                )
        return self

    # Frontend
    frontend_base_url: str = "http://localhost:3000"

    # Email
    resend_api_key: SecretStr | None = None
    email_from_address: str = "noreply@yourdomain.com"
    email_from_name: str = "Zima"

    # Stripe
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_shield_monthly: str | None = None
    stripe_price_pro_monthly: str | None = None

    # Providers — threat intelligence
    virustotal_api_key: SecretStr | None = None

    # Providers — Wave 0
    hibp_api_key: SecretStr | None = None

    # Providers — Wave 1 identity
    dehashed_email: str | None = None
    dehashed_api_key: SecretStr | None = None
    leakcheck_api_key: SecretStr | None = None
    breachdirectory_rapidapi_key: SecretStr | None = None
    hudson_rock_api_key: SecretStr | None = None
    emailrep_api_key: SecretStr | None = None

    # Providers — identity enrichment (Wave 2)
    emailcrawlr_api_key: SecretStr | None = None
    gravatar_api_key: SecretStr | None = None
    emailformat_api_key: SecretStr | None = None

    # Providers — dark web intelligence
    intelx_api_key: SecretStr | None = None

    # Providers — infrastructure intelligence
    leakix_api_key: SecretStr | None = None
    whoisxmlapi_api_key: SecretStr | None = None

    # Providers — phone intelligence
    numverify_api_key: SecretStr | None = None
    twilio_account_sid: SecretStr | None = None
    twilio_auth_token: SecretStr | None = None

    # Field-level encryption (envelope encryption with AES-256-GCM)
    # Generate: python -c "import secrets; print(secrets.token_hex(32))"
    field_encryption_key: SecretStr | None = None

    # TLS enforcement — production requires encrypted transport by default.
    # Set to False only for local development without TLS-enabled services.
    require_tls_postgres: bool = True
    require_tls_redis: bool = True

    # Tier
    default_tier: str = "core"

    # Scan staleness — how long a running scan may stay in "running" state
    # before it is automatically marked stale on the next status poll.
    stale_scan_after_minutes: int = 30

    # Uploads
    mailbox_upload_max_mb: int = 1024

    # Companion
    companion_setup_token_expire_minutes: int = 15
    companion_token_expire_days: int = 7

    # Browser Extension
    extension_setup_token_expire_minutes: int = 15
    extension_token_expire_minutes: int = 60
    extension_setup_token_rate_limit: str = "10/hour"  # noqa: S105
    extension_register_rate_limit: str = "10/hour"  # noqa: S105
    extension_refresh_rate_limit: str = "120/hour"  # noqa: S105

    # Local AI — Ollama
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    # Keep local-by-default to avoid accidental metadata exfiltration.
    # Set true only for explicitly trusted remote Ollama deployments.
    ollama_allow_non_local: bool = False
    ollama_model: str = "gemma2:2b"
    ollama_timeout_seconds: int = 30
    ollama_mode: Literal["off", "shadow", "assist", "enforce"] = "off"
    ollama_min_confidence: int = 70
    # Optional safeguard: only apply Ollama suggestions when the suggested
    # service appears aligned with the sender domain tokens.
    ollama_require_domain_alignment: bool = False
    ollama_max_candidates_per_batch: int = 10
    # Dedicated cap for post-import full-list identity review scans.
    # Keeps latency bounded and avoids long Ollama queues on large uploads.
    ollama_post_import_max_candidates: int = 25
    # Set true only after installing fastembed: pip install fastembed
    ollama_embed_enabled: bool = False

    @model_validator(mode="after")
    def validate_ollama_settings(self) -> "Settings":
        """Enforce local-only Ollama by default unless explicitly overridden."""
        if not self.ollama_enabled or self.ollama_allow_non_local:
            return self

        host = (urlparse(self.ollama_base_url).hostname or "").lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError(
                "ollama_base_url must point to localhost/loopback when "
                "ollama_enabled=true. Set OLLAMA_ALLOW_NON_LOCAL=true to "
                "explicitly allow remote endpoints."
            )
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


settings = Settings()  # type: ignore[call-arg]  # required fields loaded from env at runtime
