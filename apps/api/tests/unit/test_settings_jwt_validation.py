"""
Tests for JWT secret validation in production environments.

This module tests the JWT secret validation logic that ensures:
- JWT secret is set when JWT auth is enabled in production
- JWT secret is not empty or whitespace-only
- JWT secret is not a known weak value
- Warnings are issued for short secrets
- Development environment does not enforce these rules
"""

import pytest

from config.settings import AppSettings


class TestJWTSecretValidation:
    """Test JWT secret validation in production."""

    def test_jwt_secret_not_required_in_development(self):
        """JWT secret can be unset in development environments."""
        s = AppSettings(
            environment="development",
            auth_jwt_enabled=True,
            jwt_secret_key=None,
        )
        assert s.jwt_secret_key is None

    def test_jwt_secret_not_required_when_jwt_disabled(self):
        """JWT secret can be unset when JWT auth is disabled."""
        s = AppSettings(
            environment="production",
            auth_jwt_enabled=False,
            jwt_secret_key=None,
        )
        assert s.jwt_secret_key is None

    def test_jwt_secret_required_in_production_with_jwt_enabled(self):
        """JWT secret must be set in production when JWT auth is enabled."""
        with pytest.raises(ValueError) as exc_info:
            AppSettings(
                environment="production",
                auth_jwt_enabled=True,
                jwt_secret_key=None,
            )
        assert "JWT_SECRET_KEY must be set" in str(exc_info.value)

    def test_jwt_secret_cannot_be_empty_in_production(self):
        """JWT secret cannot be empty string in production."""
        with pytest.raises(ValueError) as exc_info:
            AppSettings(
                environment="production",
                auth_jwt_enabled=True,
                jwt_secret_key="",
            )
        assert "JWT_SECRET_KEY cannot be empty string" in str(exc_info.value)

    def test_jwt_secret_cannot_be_whitespace_only_in_production(self):
        """JWT secret cannot be only whitespace in production."""
        with pytest.raises(ValueError) as exc_info:
            AppSettings(
                environment="production",
                auth_jwt_enabled=True,
                jwt_secret_key="   ",
            )
        assert "JWT_SECRET_KEY cannot be whitespace-only" in str(exc_info.value)

    def test_jwt_secret_rejects_known_weak_values(self):
        """JWT secret cannot be known weak values in production."""
        weak_secrets = [
            "secret",
            "jwt-secret",
            "jwtsecret",
            "changeme",
            "change-me",
            "password",
            "test",
            "dev",
            "development",
            "default",
            "123456",
            "abcdef",
        ]

        for weak_secret in weak_secrets:
            with pytest.raises(ValueError) as exc_info:
                AppSettings(
                    environment="production",
                    auth_jwt_enabled=True,
                    jwt_secret_key=weak_secret,
                )
            assert "known weak value" in str(exc_info.value)
            assert weak_secret in str(exc_info.value)

    def test_jwt_secret_accepts_strong_value_in_production(self):
        """Strong JWT secrets are accepted in production."""
        strong_secret = "a" * 32  # 32 character strong secret
        s = AppSettings(
            environment="production",
            auth_jwt_enabled=True,
            jwt_secret_key=strong_secret,
            cors_allow_origins=["https://example.com"],
        )
        assert s.jwt_secret_key == strong_secret

    def test_jwt_secret_case_insensitive_weak_check(self):
        """Weak secret check is case-insensitive."""
        with pytest.raises(ValueError) as exc_info:
            AppSettings(
                environment="production",
                auth_jwt_enabled=True,
                jwt_secret_key="SECRET",  # uppercase version of weak value
            )
        assert "known weak value" in str(exc_info.value)

    def test_jwt_secret_whitespace_trimmed_before_validation(self):
        """JWT secret is trimmed before weak value check."""
        with pytest.raises(ValueError) as exc_info:
            AppSettings(
                environment="production",
                auth_jwt_enabled=True,
                jwt_secret_key="  secret  ",  # weak value with whitespace
            )
        assert "known weak value" in str(exc_info.value)

    def test_jwt_secret_accepts_31_char_secret_with_warning(self):
        """JWT secrets shorter than 32 chars are accepted with a warning."""
        import warnings

        short_secret = "a" * 31  # 31 characters (below recommended)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            s = AppSettings(
                environment="production",
                auth_jwt_enabled=True,
                jwt_secret_key=short_secret,
                cors_allow_origins=["https://example.com"],
            )
            assert s.jwt_secret_key == short_secret
            assert len(w) == 1
            assert "shorter than recommended" in str(w[0].message)
            assert "31 chars" in str(w[0].message)

    def test_jwt_secret_no_warning_for_32_plus_char_secret(self):
        """JWT secrets of 32+ chars do not trigger a warning."""
        import warnings

        strong_secret = "a" * 32  # Exactly 32 characters
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            s = AppSettings(
                environment="production",
                auth_jwt_enabled=True,
                jwt_secret_key=strong_secret,
                cors_allow_origins=["https://example.com"],
            )
            assert s.jwt_secret_key == strong_secret
            # No warning should be issued
            assert len(w) == 0

    def test_jwt_secret_accepts_very_long_secret(self):
        """Very long JWT secrets are accepted."""
        long_secret = "a" * 100  # 100 characters
        s = AppSettings(
            environment="production",
            auth_jwt_enabled=True,
            jwt_secret_key=long_secret,
            cors_allow_origins=["https://example.com"],
        )
        assert s.jwt_secret_key == long_secret

    def test_jwt_secret_validation_environment_variations(self):
        """Check various environment names are treated as production."""
        production_envs = ["production", "PRODUCTION", "Production"]

        for env in production_envs:
            with pytest.raises(ValueError):
                AppSettings(
                    environment=env,
                    auth_jwt_enabled=True,
                    jwt_secret_key=None,
                )

    def test_jwt_secret_non_production_environments_allowed(self):
        """Non-production environments do not enforce JWT secret validation."""
        non_prod_envs = ["development", "staging", "test", "local"]

        for env in non_prod_envs:
            s = AppSettings(
                environment=env,
                auth_jwt_enabled=True,
                jwt_secret_key=None,
            )
            assert s.jwt_secret_key is None
