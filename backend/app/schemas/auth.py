from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def bcrypt_length(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 UTF-8 bytes")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

    _bcrypt_length = field_validator("password")(RegisterRequest.bcrypt_length.__func__)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="access token lifetime in seconds")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    created_at: datetime
