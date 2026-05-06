"""Automated sensitive data detection in log output (Task #98).

Validates that no log messages contain sensitive patterns
(password, api_key, secret, token, authorization, cookie).
"""

import io
import json
import logging

from utils.json_logging import JsonFormatter


class TestSensitiveDataScan:
    """Scan log output for sensitive data patterns."""

    def _capture_log(self, message: str, **extra) -> dict:
        """Capture a single log entry as parsed JSON."""
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        test_logger = logging.getLogger(f"sensitive_test.{id(self)}")
        test_logger.handlers.clear()
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)
        test_logger.info(message, extra=extra)
        output = stream.getvalue().strip()
        if output:
            result: dict = json.loads(output)
            return result
        return {}

    def test_clean_message_passes(self):
        matches = JsonFormatter.check_sensitive_data("User search completed in 150ms")
        assert matches == []

    def test_password_detected(self):
        matches = JsonFormatter.check_sensitive_data("Login with password=secret123")
        assert "password" in matches

    def test_api_key_detected(self):
        matches = JsonFormatter.check_sensitive_data("Using api_key=sk-xxx")
        assert "api_key" in matches

    def test_token_detected(self):
        matches = JsonFormatter.check_sensitive_data("Bearer token eyJhbG...")
        assert "token" in matches

    def test_secret_detected(self):
        matches = JsonFormatter.check_sensitive_data("client_secret=abc123")
        assert "secret" in matches

    def test_authorization_detected(self):
        matches = JsonFormatter.check_sensitive_data("authorization header present")
        assert "authorization" in matches

    def test_cookie_detected(self):
        matches = JsonFormatter.check_sensitive_data("Set cookie session=xyz")
        assert "cookie" in matches

    def test_json_output_has_service_field(self):
        entry = self._capture_log("test message")
        assert "service" in entry
        assert entry["service"] == "ai-real-estate-api"

    def test_json_output_has_timestamp(self):
        entry = self._capture_log("test message")
        assert "ts" in entry
        assert isinstance(entry["ts"], int)

    def test_json_output_has_level(self):
        entry = self._capture_log("test message")
        assert "level" in entry
        assert entry["level"] == "INFO"

    def test_json_output_preserves_extra_fields(self):
        entry = self._capture_log("with extra", request_id="req-123")
        assert entry.get("request_id") == "req-123"

    def test_exception_info_in_output(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        test_logger = logging.getLogger(f"exc_test.{id(self)}")
        test_logger.handlers.clear()
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.ERROR)

        try:
            raise ValueError("test error")
        except ValueError:
            test_logger.exception("operation failed")

        output = stream.getvalue().strip()
        entry = json.loads(output)
        assert "exception" in entry
        assert "ValueError: test error" in entry["exception"]
