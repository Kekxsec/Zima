# backend/app/findings/schemas.py
from pydantic import BaseModel, Field


class SuppressRequest(BaseModel):
    reason: str | None = Field(None, max_length=256)
