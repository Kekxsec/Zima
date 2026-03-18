# backend/app/assets/schemas.py
from pydantic import BaseModel, Field, field_validator

from backend.app.core.enums import EntityType


class AssetCreate(BaseModel):
    entity_type: EntityType
    value: str = Field(..., min_length=1, max_length=512)

    @field_validator("value")
    @classmethod
    def strip_and_lowercase(cls, v: str) -> str:
        return v.strip().lower()
