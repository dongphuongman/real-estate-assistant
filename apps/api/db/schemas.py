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


# Collection Schemas
class CollectionCreate(BaseModel):
    """Schema for creating a collection."""

    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, max_length=1000, description="Collection description")


class CollectionUpdate(BaseModel):
    """Schema for updating a collection."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class CollectionResponse(BaseModel):
    """Schema for collection response."""

    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
    favorite_count: int = 0  # Computed field

    model_config = {"from_attributes": True}


class CollectionListResponse(BaseModel):
    """Schema for list of collections."""

    items: list[CollectionResponse]
    total: int


# Favorite Schemas
class FavoriteCreate(BaseModel):
    """Schema for creating a favorite."""

    property_id: str = Field(..., min_length=1, max_length=255, description="Property ID")
    collection_id: Optional[str] = Field(None, description="Optional collection ID")
    notes: Optional[str] = Field(None, max_length=2000, description="User notes about property")


class FavoriteUpdate(BaseModel):
    """Schema for updating a favorite."""

    collection_id: Optional[str] = None  # None means "uncategorized"
    notes: Optional[str] = Field(None, max_length=2000)


class FavoriteResponse(BaseModel):
    """Schema for favorite response (without property data)."""

    id: str
    user_id: str
    property_id: str
    collection_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FavoriteWithPropertyResponse(BaseModel):
    """Schema for favorite response with full property data from ChromaDB."""

    id: str
    user_id: str
    property_id: str
    collection_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    property: Optional[dict[str, Any]] = None  # Full property data from ChromaDB
    is_available: bool = True  # False if property no longer exists in ChromaDB

    model_config = {"from_attributes": True}


class FavoriteListResponse(BaseModel):
    """Schema for list of favorites."""

    items: list[FavoriteWithPropertyResponse]
    total: int
    unavailable_count: int = 0  # Count of properties no longer in ChromaDB


class FavoriteCheckResponse(BaseModel):
    """Schema for checking if a property is favorited."""

    is_favorited: bool
    favorite_id: Optional[str] = None
    collection_id: Optional[str] = None
    notes: Optional[str] = None


# Price Snapshot Schemas (Task #38: Price History & Trends)
TrendDirectionType = Literal["increasing", "decreasing", "stable", "insufficient_data"]
MarketTrendType = Literal["rising", "falling", "stable"]
ConfidenceType = Literal["high", "medium", "low"]
IntervalType = Literal["month", "quarter", "year"]


class PriceSnapshotResponse(BaseModel):
    """Schema for a single price snapshot."""

    id: str
    property_id: str
    price: float
    price_per_sqm: Optional[float] = None
    currency: Optional[str] = None
    source: Optional[str] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class PriceHistoryResponse(BaseModel):
    """Schema for property price history."""

    property_id: str
    snapshots: list[PriceSnapshotResponse]
    total: int
    current_price: Optional[float] = None
    first_recorded: Optional[datetime] = None
    last_recorded: Optional[datetime] = None
    price_change_percent: Optional[float] = None  # From first to last
    trend: TrendDirectionType


class MarketTrendPoint(BaseModel):
    """Schema for a single point in market trend data."""

    period: str  # e.g., "2024-01", "2024-Q1"
    start_date: datetime
    end_date: datetime
    average_price: float
    median_price: float
    volume: int
    avg_price_per_sqm: Optional[float] = None


class MarketTrendsResponse(BaseModel):
    """Schema for market trend data."""

    city: Optional[str] = None
    district: Optional[str] = None
    interval: IntervalType
    data_points: list[MarketTrendPoint]
    trend_direction: TrendDirectionType
    change_percent: Optional[float] = None
    confidence: ConfidenceType


class MarketIndicatorsResponse(BaseModel):
    """Schema for market indicators."""

    city: Optional[str] = None
    overall_trend: MarketTrendType
    avg_price_change_1m: Optional[float] = None
    avg_price_change_3m: Optional[float] = None
    avg_price_change_6m: Optional[float] = None
    avg_price_change_1y: Optional[float] = None
    total_listings: int
    new_listings_7d: int
    price_drops_7d: int
    hottest_districts: list[dict[str, Any]]  # Top 5 districts by activity
    coldest_districts: list[dict[str, Any]]  # Bottom 5 districts
