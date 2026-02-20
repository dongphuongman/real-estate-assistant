"""Pydantic schemas for authentication API."""

import re
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserUpdate(BaseModel):
    """Schema for user profile update."""

    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    role: str = "user"
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Schema for resend verification email request."""

    email: EmailStr


class OAuthAuthorizeResponse(BaseModel):
    """Schema for OAuth authorization response."""

    authorization_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    """Schema for OAuth callback."""

    code: str
    state: str
    provider: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None


# Saved Search Schemas
AlertFrequencyType = Literal["instant", "daily", "weekly", "none"]


class SavedSearchCreate(BaseModel):
    """Schema for creating a saved search."""

    name: str = Field(..., min_length=1, max_length=255, description="Search name")
    description: Optional[str] = Field(None, max_length=1000, description="Search description")
    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Search filters (city, min_price, max_price, etc.)",
    )
    alert_frequency: AlertFrequencyType = Field(default="daily", description="Alert frequency")
    notify_on_new: bool = Field(default=True, description="Notify on new properties")
    notify_on_price_drop: bool = Field(default=True, description="Notify on price drops")


class SavedSearchUpdate(BaseModel):
    """Schema for updating a saved search."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    filters: Optional[dict[str, Any]] = None
    alert_frequency: Optional[AlertFrequencyType] = None
    is_active: Optional[bool] = None
    notify_on_new: Optional[bool] = None
    notify_on_price_drop: Optional[bool] = None


class SavedSearchResponse(BaseModel):
    """Schema for saved search response."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    filters: dict[str, Any]
    alert_frequency: str
    is_active: bool
    notify_on_new: bool
    notify_on_price_drop: bool
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime] = None
    use_count: int = 0

    model_config = {"from_attributes": True}


class SavedSearchListResponse(BaseModel):
    """Schema for list of saved searches."""

    items: list[SavedSearchResponse]
    total: int
