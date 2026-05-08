"""Tests for api.deps.auth module."""

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException

from api.deps.auth import (
    AuthCredentials,
    _extract_token,
    _get_user_from_token,
    get_auth_credentials,
    get_current_active_user,
    get_current_user,
    get_current_user_optional,
    get_current_verified_user,
    get_optional_user,
    require_permission,
    require_role,
    require_roles,
)
from api.rbac import Permission, Role


def _make_user(user_id="user-1", email="test@test.com", is_active=True, is_verified=True):
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.is_active = is_active
    user.is_verified = is_verified
    return user


def _make_request(headers=None, cookies=None):
    request = MagicMock()
    request.headers = headers or {}
    request.cookies = cookies or {}
    return request


class TestAuthCredentials:
    def test_default_roles(self):
        user = _make_user()
        payload = {}
        creds = AuthCredentials(user, payload)
        assert Role.USER in creds.roles

    def test_admin_role(self):
        user = _make_user()
        payload = {"roles": ["admin"]}
        creds = AuthCredentials(user, payload)
        assert Role.ADMIN in creds.roles

    def test_multiple_roles(self):
        user = _make_user()
        payload = {"roles": ["admin", "user"]}
        creds = AuthCredentials(user, payload)
        assert Role.ADMIN in creds.roles
        assert Role.USER in creds.roles

    def test_unknown_role_maps_to_user(self):
        user = _make_user()
        payload = {"roles": ["unknown_role"]}
        creds = AuthCredentials(user, payload)
        assert Role.USER in creds.roles

    def test_read_only_role(self):
        user = _make_user()
        payload = {"roles": ["read_only"]}
        creds = AuthCredentials(user, payload)
        assert Role.READ_ONLY in creds.roles

    def test_api_client_role(self):
        user = _make_user()
        payload = {"roles": ["api_client"]}
        creds = AuthCredentials(user, payload)
        assert Role.API_CLIENT in creds.roles

    def test_case_insensitive_roles(self):
        user = _make_user()
        payload = {"roles": ["ADMIN", "User"]}
        creds = AuthCredentials(user, payload)
        assert Role.ADMIN in creds.roles
        assert Role.USER in creds.roles

    def test_has_role(self):
        user = _make_user()
        payload = {"roles": ["admin"]}
        creds = AuthCredentials(user, payload)
        assert creds.has_role(Role.ADMIN) is True
        assert creds.has_role(Role.USER) is False

    def test_has_permission(self):
        user = _make_user()
        payload = {"roles": ["admin"]}
        creds = AuthCredentials(user, payload)
        assert creds.is_admin() is True

    def test_is_admin(self):
        user = _make_user()
        payload = {"roles": ["admin"]}
        creds = AuthCredentials(user, payload)
        assert creds.is_admin() is True

    def test_is_not_admin(self):
        user = _make_user()
        payload = {"roles": ["user"]}
        creds = AuthCredentials(user, payload)
        assert creds.is_admin() is False

    def test_permissions_populated(self):
        user = _make_user()
        payload = {"roles": ["user"]}
        creds = AuthCredentials(user, payload)
        assert len(creds.permissions) > 0

    def test_user_id(self):
        user = _make_user(user_id="specific-id")
        payload = {}
        creds = AuthCredentials(user, payload)
        assert creds.user_id == "specific-id"

    def test_email(self):
        user = _make_user(email="a@b.com")
        payload = {}
        creds = AuthCredentials(user, payload)
        assert creds.email == "a@b.com"


class TestGetUserFromToken:
    @pytest.mark.asyncio
    async def test_expired_token(self):
        session = AsyncMock()
        with patch("api.deps.auth.verify_access_token") as mock_verify:
            mock_verify.side_effect = jwt.ExpiredSignatureError()
            with pytest.raises(HTTPException) as exc_info:
                await _get_user_from_token("expired-token", session)
            assert exc_info.value.status_code == 401
            assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        session = AsyncMock()
        with patch("api.deps.auth.verify_access_token") as mock_verify:
            mock_verify.side_effect = jwt.InvalidTokenError("bad token")
            with pytest.raises(HTTPException) as exc_info:
                await _get_user_from_token("bad-token", session)
            assert exc_info.value.status_code == 401
            assert "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_no_sub_in_payload(self):
        session = AsyncMock()
        with patch("api.deps.auth.verify_access_token") as mock_verify:
            mock_verify.return_value = {"no_sub": "here"}
            with pytest.raises(HTTPException) as exc_info:
                await _get_user_from_token("token", session)
            assert exc_info.value.status_code == 401
            assert "payload" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        session = AsyncMock()
        with (
            patch("api.deps.auth.verify_access_token") as mock_verify,
            patch("api.deps.auth.UserRepository") as mock_repo_cls,
        ):
            mock_verify.return_value = {"sub": "nonexistent"}
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=None)
            mock_repo_cls.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                await _get_user_from_token("token", session)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_success(self):
        session = AsyncMock()
        user = _make_user()
        with (
            patch("api.deps.auth.verify_access_token") as mock_verify,
            patch("api.deps.auth.UserRepository") as mock_repo_cls,
        ):
            mock_verify.return_value = {"sub": "user-1"}
            mock_repo = MagicMock()
            mock_repo.get_by_id = AsyncMock(return_value=user)
            mock_repo_cls.return_value = mock_repo

            result_user, result_payload = await _get_user_from_token("token", session)
            assert result_user == user
            assert result_payload["sub"] == "user-1"


class TestExtractToken:
    @pytest.mark.asyncio
    async def test_no_token(self):
        request = _make_request()
        result = await _extract_token(request, None, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_from_cookie(self):
        request = _make_request()
        result = await _extract_token(request, "cookie-token", None)
        assert result == "cookie-token"

    @pytest.mark.asyncio
    async def test_from_header_priority(self):
        request = _make_request()
        creds = MagicMock()
        creds.credentials = "bearer-token"
        result = await _extract_token(request, "cookie-token", creds)
        assert result == "bearer-token"


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_no_token_raises_401(self):
        request = _make_request()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, None, None, AsyncMock())
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        user = _make_user()
        request = _make_request()
        creds = MagicMock()
        creds.credentials = "valid-token"
        session = AsyncMock()
        with patch("api.deps.auth._get_user_from_token") as mock_get:
            mock_get.return_value = (user, {"sub": "user-1"})
            result = await get_current_user(request, None, creds, session)
            assert result == user


class TestGetCurrentUserOptional:
    @pytest.mark.asyncio
    async def test_no_token_returns_none(self):
        request = _make_request()
        result = await get_current_user_optional(request, None, None, AsyncMock())
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        user = _make_user()
        request = _make_request()
        creds = MagicMock()
        creds.credentials = "valid-token"
        session = AsyncMock()
        with patch("api.deps.auth._get_user_from_token") as mock_get:
            mock_get.return_value = (user, {"sub": "user-1"})
            result = await get_current_user_optional(request, None, creds, session)
            assert result == user


class TestGetCurrentActiveUser:
    @pytest.mark.asyncio
    async def test_active_user(self):
        user = _make_user(is_active=True)
        result = await get_current_active_user(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self):
        user = _make_user(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(user)
        assert exc_info.value.status_code == 403


class TestGetCurrentVerifiedUser:
    @pytest.mark.asyncio
    async def test_verified_user(self):
        user = _make_user(is_verified=True)
        with patch("api.deps.auth.get_settings") as mock_settings:
            mock_settings.return_value.auth_email_verification_required = True
            result = await get_current_verified_user(user)
            assert result == user

    @pytest.mark.asyncio
    async def test_unverified_user_raises_403(self):
        user = _make_user(is_verified=False)
        with patch("api.deps.auth.get_settings") as mock_settings:
            mock_settings.return_value.auth_email_verification_required = True
            with pytest.raises(HTTPException) as exc_info:
                await get_current_verified_user(user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_skip_verification_when_disabled(self):
        user = _make_user(is_verified=False)
        with patch("api.deps.auth.get_settings") as mock_settings:
            mock_settings.return_value.auth_email_verification_required = False
            result = await get_current_verified_user(user)
            assert result == user


class TestGetOptionalUser:
    @pytest.mark.asyncio
    async def test_no_token_returns_none(self):
        request = _make_request()
        result = await get_optional_user(request, None, None, AsyncMock())
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        user = _make_user()
        request = _make_request()
        creds = MagicMock()
        creds.credentials = "valid-token"
        session = AsyncMock()
        with patch("api.deps.auth._get_user_from_token") as mock_get:
            mock_get.return_value = (user, {"sub": "user-1"})
            result = await get_optional_user(request, None, creds, session)
            assert result == user

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        request = _make_request()
        creds = MagicMock()
        creds.credentials = "invalid-token"
        session = AsyncMock()
        with patch("api.deps.auth._get_user_from_token") as mock_get:
            mock_get.side_effect = HTTPException(status_code=401)
            result = await get_optional_user(request, None, creds, session)
            assert result is None


class TestGetAuthCredentials:
    @pytest.mark.asyncio
    async def test_no_token_raises_401(self):
        request = _make_request()
        with pytest.raises(HTTPException) as exc_info:
            await get_auth_credentials(request, None, None, AsyncMock())
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self):
        user = _make_user(is_active=False)
        request = _make_request()
        creds = MagicMock()
        creds.credentials = "token"
        session = AsyncMock()
        with patch("api.deps.auth._get_user_from_token") as mock_get:
            mock_get.return_value = (user, {"sub": "user-1"})
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_credentials(request, None, creds, session)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_active_user_returns_credentials(self):
        user = _make_user(is_active=True)
        request = _make_request()
        creds = MagicMock()
        creds.credentials = "token"
        session = AsyncMock()
        with patch("api.deps.auth._get_user_from_token") as mock_get:
            mock_get.return_value = (user, {"sub": "user-1", "roles": ["admin"]})
            result = await get_auth_credentials(request, None, creds, session)
            assert isinstance(result, AuthCredentials)
            assert result.is_admin()


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_has_required_role(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["admin"]})
        checker = require_role("admin")
        with patch("api.deps.auth.get_auth_credentials") as mock_get:
            mock_get.return_value = creds
            # Need to call the checker with the dependency
            # Since it uses Depends, we call it directly
            result = await checker(creds)
            assert result == creds

    @pytest.mark.asyncio
    async def test_missing_role_but_is_admin(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["admin"]})
        checker = require_role("moderator")
        result = await checker(creds)
        assert result == creds

    @pytest.mark.asyncio
    async def test_missing_role_raises_403(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["user"]})
        checker = require_role("admin")
        with pytest.raises(HTTPException) as exc_info:
            await checker(creds)
        assert exc_info.value.status_code == 403


class TestRequireRoles:
    @pytest.mark.asyncio
    async def test_has_one_of_roles(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["user"]})
        checker = require_roles(["admin", "user"])
        result = await checker(creds)
        assert result == creds

    @pytest.mark.asyncio
    async def test_admin_bypasses(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["admin"]})
        checker = require_roles(["moderator"])
        result = await checker(creds)
        assert result == creds

    @pytest.mark.asyncio
    async def test_no_matching_roles_raises_403(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["user"]})
        checker = require_roles(["admin", "moderator"])
        with pytest.raises(HTTPException) as exc_info:
            await checker(creds)
        assert exc_info.value.status_code == 403


class TestRequirePermission:
    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["admin"]})
        checker = require_permission(Permission.DATA_DELETE)
        result = await checker(creds)
        assert result == creds

    @pytest.mark.asyncio
    async def test_user_without_permission_raises_403(self):
        user = _make_user()
        creds = AuthCredentials(user, {"roles": ["read_only"]})
        checker = require_permission(Permission.DATA_DELETE)
        with pytest.raises(HTTPException) as exc_info:
            await checker(creds)
        assert exc_info.value.status_code == 403
