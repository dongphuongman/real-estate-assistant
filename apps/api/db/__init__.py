"""Database layer for user authentication."""

from db.database import get_db, init_db
from db.models import OAuthAccount, RefreshToken, User
from db.repositories import OAuthAccountRepository, RefreshTokenRepository, UserRepository
from db.schemas import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Database
    "get_db",
    "init_db",
    # Models
    "User",
    "RefreshToken",
    "OAuthAccount",
    # Repositories
    "UserRepository",
    "RefreshTokenRepository",
    "OAuthAccountRepository",
    # Schemas
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserResponse",
    "TokenResponse",
]
