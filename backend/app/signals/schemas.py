# backend/app/signals/schemas.py
import uuid

from pydantic import BaseModel, Field

from backend.app.core.enums import Confidence, EntityType, Severity


class SignalCreate(BaseModel):
    signal_type: str = Field(..., max_length=100)
    category: str = Field(..., max_length=100)
    entity_type: EntityType
    entity_id: uuid.UUID
    entity_value: str = Field(..., max_length=512)
    user_id: uuid.UUID
    severity: Severity
    confidence: Confidence
    source: str = Field(..., max_length=100)
    provider: str = Field(..., max_length=100)
    summary: str = Field(..., max_length=512)
    details: str | None = Field(None, max_length=4096)
    evidence: dict[str, object] | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    recommended_action: str | None = Field(None, max_length=512)
    # Discriminator for signals that can appear multiple times on the same
    # (user, signal_type, asset) — e.g. breach name, platform name.
    # Included in the dedup hash when present.
    source_ref: str | None = Field(None, max_length=256)
