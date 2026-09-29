from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserRegister(BaseModel):
    """Payload for registering a new user account."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (minimum 6 characters)")
    full_name: Optional[str] = Field(None, max_length=255, description="Optional user full name")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, clean):
            raise ValueError("Invalid email format.")
        return clean

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v

class UserLogin(BaseModel):
    """Payload for authenticating an existing user."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    @model_validator(mode="before")
    @classmethod
    def normalize_login_payload(cls, data: object) -> object:
        if isinstance(data, dict):
            if "username" in data and "email" not in data:
                data["email"] = data["username"]
        return data

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    """Safe public representation of a user entity."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime


class TokenResponse(BaseModel):
    """Authentication token response payload."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
