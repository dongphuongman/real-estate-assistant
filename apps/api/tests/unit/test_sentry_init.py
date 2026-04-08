"""
Unit tests for Sentry initialization and PII filtering (Task #56).
"""

from api.sentry_init import _PII_FIELDS, _before_send


class TestPIIRedaction:
    """Verify PII is properly redacted from Sentry events."""

    def test_redact_email_header(self):
        event = {"request": {"headers": {"Email": "user@example.com"}}}
        result = _before_send(event, {})
        assert result["request"]["headers"]["Email"] == "[Redacted]"

    def test_redact_authorization_header(self):
        event = {"request": {"headers": {"Authorization": "Bearer secret-token"}}}
        result = _before_send(event, {})
        assert result["request"]["headers"]["Authorization"] == "[Redacted]"

    def test_redact_api_key_header(self):
        event = {"request": {"headers": {"X-API-Key": "super-secret-key"}}}
        result = _before_send(event, {})
        assert result["request"]["headers"]["X-API-Key"] == "[Redacted]"

    def test_preserve_non_pii_header(self):
        event = {"request": {"headers": {"Content-Type": "application/json"}}}
        result = _before_send(event, {})
        assert result["request"]["headers"]["Content-Type"] == "application/json"

    def test_redact_request_body_query(self):
        event = {"request": {"data": {"query": "my search query", "top_k": 5}}}
        result = _before_send(event, {})
        assert result["request"]["data"]["query"] == "[Redacted]"
        assert result["request"]["data"]["top_k"] == 5

    def test_redact_request_body_message(self):
        event = {"request": {"data": {"message": "hello", "session_id": "abc"}}}
        result = _before_send(event, {})
        assert result["request"]["data"]["message"] == "[Redacted]"

    def test_redact_extra_context(self):
        event = {"extra": {"email": "user@test.com", "task": "search"}}
        result = _before_send(event, {})
        assert result["extra"]["email"] == "[Redacted]"
        assert result["extra"]["task"] == "search"

    def test_no_request_returns_event(self):
        event = {"message": "test error"}
        result = _before_send(event, {})
        assert result == event

    def test_empty_event(self):
        event = {}
        result = _before_send(event, {})
        assert result == {}


class TestSentryInit:
    """Test Sentry initialization logic."""

    def test_init_without_dsn_returns_false(self):
        from api.sentry_init import init_sentry

        result = init_sentry()
        assert result is False

    def test_pii_fields_defined(self):
        assert "email" in _PII_FIELDS
        assert "password" in _PII_FIELDS
        assert "query" in _PII_FIELDS
        assert "message" in _PII_FIELDS
        assert "token" in _PII_FIELDS


class TestSentryHelpers:
    """Test helper functions."""

    def test_add_llm_breadcrumb_no_error(self):
        """Breadcrumb should not raise when Sentry is not initialized."""
        from api.sentry_init import add_llm_breadcrumb

        # Should not raise
        add_llm_breadcrumb(provider="openai", model="gpt-4")

    def test_set_user_context_no_error(self):
        """Setting user context should not raise when Sentry is not initialized."""
        from api.sentry_init import set_user_context

        # Should not raise
        set_user_context(user_id="test-user-123")
        set_user_context(user_id="test-user-123", email="test@example.com")
        set_user_context(user_id=None)
