"""OAuth integration module."""

from core.oauth.base import OAuthError, OAuthProvider, OAuthUserInfo
from core.oauth.google import GoogleOAuthProvider

__all__ = [
    "OAuthError",
    "OAuthProvider",
    "OAuthUserInfo",
    "GoogleOAuthProvider",
]
