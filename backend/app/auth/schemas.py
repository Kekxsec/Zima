# backend/app/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field


class OTPRequest(BaseModel):
    email: EmailStr
    privacy_policy_accepted: bool = False


class OTPVerify(BaseModel):
    email: EmailStr
    # Exactly 6 numeric digits. Rejects non-numeric and wrong-length codes
    # before any database query runs.
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105
