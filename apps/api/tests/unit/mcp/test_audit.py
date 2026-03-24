"""
Unit tests for MCP Audit Logging (Task #69).

Tests for:
- MCPAuditLogger core functionality
- PII redaction rules
- Request ID context management
- Log retention policy
"""

import csv
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from mcp.audit import (
    MCPAuditEvent,
    MCPAuditEventType,
    MCPAuditLevel,
    MCPAuditLogger,
    get_mcp_audit_logger,
    log_mcp_audit,
)
from mcp.context import (
    MCPRequestContext,
    generate_request_id,
    get_request_id,
    set_request_id,
)
from mcp.redaction import (
    redact_for_audit,
    redact_params,
    redact_result,
    sanitize_error_message,
)
from mcp.retention import (
    MCPAuditRetention,
    get_retention_manager,
)


class TestMCPAuditEvent:
    """Tests for MCPAuditEvent model."""

    def test_create_event_with_defaults(self):
        """Test creating an event with minimal required fields."""
        event = MCPAuditEvent(
            event_type=MCPAuditEventType.CONNECTOR_EXECUTE,
            level=MCPAuditLevel.MEDIUM,
            connector_name="test_connector",
            status="success",
        )

        assert event.event_type == MCPAuditEventType.CONNECTOR_EXECUTE
        assert event.level == MCPAuditLevel.MEDIUM
        assert event.connector_name == "test_connector"
        assert event.status == "success"
        assert event.timestamp is not None
        assert event.params_meta == {}
        assert event.result_meta == {}

    def test_create_event_with_all_fields(self):
        """Test creating an event with all fields."""
        event = MCPAuditEvent(
            event_type=MCPAuditEventType.CONNECTOR_ERROR,
            level=MCPAuditLevel.HIGH,
            connector_name="error_connector",
            operation="search",
            status="error",
            duration_ms=150,
            request_id="req-123",
            params_meta={"query": "test"},
            result_meta={"count": 0},
            error_message="Connection failed",
            metadata={"retry_count": 3},
        )

        assert event.event_type == MCPAuditEventType.CONNECTOR_ERROR
        assert event.connector_name == "error_connector"
        assert event.operation == "search"
        assert event.duration_ms == 150
        assert event.request_id == "req-123"
        assert event.error_message == "Connection failed"


class TestMCPAuditLogger:
    """Tests for MCPAuditLogger class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def audit_logger(self, temp_log_dir):
        """Create an audit logger with temp directory."""
        return MCPAuditLogger(log_dir=temp_log_dir, enabled=True)

    def test_logger_initialization(self, audit_logger, temp_log_dir):
        """Test logger initializes correctly."""
        assert audit_logger._enabled is True
        assert audit_logger._log_dir == temp_log_dir
        assert audit_logger._retention_days == 30
        assert audit_logger._log_file.name.startswith("mcp_audit_")

    def test_log_connector_call(self, audit_logger, temp_log_dir):
        """Test logging a connector call."""
        audit_logger.log_connector_call(
            connector_name="test_connector",
            operation="search",
            params_meta={"query": "berlin"},
            result_meta={"count": 5},
            duration_ms=100,
            status="success",
        )

        # Verify log file was created
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = temp_log_dir / f"mcp_audit_{today}.csv"
        assert log_file.exists()

        # Verify content
        with open(log_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            assert row["connector_name"] == "test_connector"
            assert row["operation"] == "search"
            assert row["status"] == "success"
            assert row["duration_ms"] == "100"

    def test_log_lifecycle_event(self, audit_logger):
        """Test logging connector lifecycle events."""
        audit_logger.log_connector_lifecycle(
            connector_name="test_connector",
            lifecycle_event="connect",
            status="success",
        )

        # Verify in log
        with open(audit_logger._log_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1

    def test_log_allowlist_violation(self, audit_logger):
        """Test logging allowlist violations."""
        audit_logger.log_allowlist_violation(
            connector_name="restricted_connector",
            edition="community",
            metadata={"attempted_by": "user123"},
        )

        # Verify high severity for violations
        with open(audit_logger._log_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
            event_type = "mcp.connector.allowlist_violation"
            assert row["event_type"] == event_type
            assert row["level"] == "HIGH"

    def test_query_audit_logs(self, audit_logger):
        """Test querying audit logs."""
        # Add some test entries
        for i in range(3):
            audit_logger.log_connector_call(
                connector_name=f"connector_{i}",
                operation="search",
                params_meta={},
                result_meta={},
                duration_ms=100,
                status="success",
            )

        # Query by connector name
        results = audit_logger.query(connector_name="connector_1")
        assert len(results) == 1
        assert results[0]["connector_name"] == "connector_1"

        # Query with limit
        results = audit_logger.query(limit=2)
        assert len(results) == 2

    def test_disabled_logger(self, temp_log_dir):
        """Test that disabled logger doesn't write."""
        logger = MCPAuditLogger(log_dir=temp_log_dir, enabled=False)
        assert not logger._enabled

        logger.log_connector_call(
            connector_name="test",
            operation="search",
            params_meta={},
            result_meta={},
            duration_ms=100,
            status="success",
        )

        # No log file should be created for disabled logger
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = temp_log_dir / f"mcp_audit_{today}.csv"
        # File was created during init, but no content should be added
        # Check the file has only headers
        with open(log_file, "r", newline="", encoding="utf-8") as f:
            lines = f.readlines()
            # Only header line should exist
            assert len(lines) == 1


class TestMCPAuditContext:
    """Tests for MCP request context management."""

    def test_set_and_get_request_id(self):
        """Test setting and getting request ID."""
        set_request_id("test-123")
        assert get_request_id() == "test-123"

        set_request_id(None)
        assert get_request_id() is None

    def test_generate_request_id(self):
        """Test generating unique request IDs."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2
        assert len(id1) == 32  # UUID hex
        assert len(id2) == 32

    def test_context_manager(self):
        """Test MCPRequestContext context manager."""
        with MCPRequestContext(request_id="ctx-123") as ctx:
            assert ctx.request_id == "ctx-123"
            # Inside context, request_id should be accessible
            assert get_request_id() == "ctx-123"

        # Outside context, should be None or previous value

    def test_context_manager_auto_generate(self):
        """Test that context manager auto-generates ID if not provided."""
        with MCPRequestContext() as ctx:
            assert ctx.request_id is not None
            assert len(ctx.request_id) == 32


class TestMCPRedaction:
    """Tests for MCP redaction rules."""

    def test_redact_string_with_email(self):
        """Test that emails are redacted in strings."""
        result = redact_for_audit("Contact user@example.com for details")
        # Email should be redacted
        assert result["_type"] == "str"
        assert "example.com" not in str(result.get("_value", ""))

    def test_redact_string_with_api_key(self):
        """Test that API keys are redacted in strings."""
        result = redact_for_audit("API key: sk-1234567890abcdef")
        assert result["_redacted"] is True

    def test_redact_dict_with_sensitive_key(self):
        """Test that sensitive keys are redacted in dicts."""
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "sk-abcdef",
        }
        result = redact_for_audit(data)
        # Password should be redacted
        assert result["password"]["_redacted"] is True
        # API key should be redacted
        assert result["api_key"]["_redacted"] is True
        # Username is not sensitive
        assert result["username"]["_type"] == "str"
        assert result["username"]["_value"] == "john"

    def test_redact_params(self):
        """Test redacting connector parameters."""
        params = {
            "query": "Berlin apartments",
            "api_key": "sk-secret",
            "limit": 10,
        }
        result = redact_params(params)
        assert result["_param_count"] == 3
        assert "api_key" in result["_param_types"]
        assert result["_param_types"]["api_key"] == "REDACTED"
        assert result["_param_types"]["query"] == "str"
        assert result["_param_types"]["limit"] == "int"

    def test_redact_result(self):
        """Test redacting connector results."""
        # Mock result object
        class MockResult:
            success = True
            execution_time_ms = 50
            data = {"results": [1, 2, 3]}
            errors = None

        result = redact_result(MockResult())
        assert result["_type"] == "MCPConnectorResult"
        assert result["success"] is True
        assert result["execution_time_ms"] == 50

    def test_sanitize_error_message(self):
        """Test sanitizing error messages."""
        error = "Connection failed with key sk-123456"
        sanitized = sanitize_error_message(error)
        assert "sk-123456" not in sanitized
        assert "***" in sanitized

    def test_sanitize_error_truncation(self):
        """Test that long errors are truncated."""
        error = "x" * 300  # Very long error
        sanitized = sanitize_error_message(error, max_length=50)
        assert len(sanitized) <= 53  # 50 + "..."
        assert sanitized.endswith("...")


class TestMCPAuditRetention:
    """Tests for MCP audit log retention policy."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory for logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def retention(self, temp_log_dir):
        """Create retention manager with temp directory."""
        return MCPAuditRetention(log_dir=temp_log_dir, retention_days=7)

    def test_retention_initialization(self, retention, temp_log_dir):
        """Test retention manager initializes correctly."""
        assert retention.retention_days == 7
        assert retention._log_dir == temp_log_dir

    def test_get_expired_files(self, retention, temp_log_dir):
        """Test identifying expired log files."""
        # Create some log files with different dates
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Create old file (10 days ago)
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
            "%Y-%m-%d"
        )
        old_file = temp_log_dir / f"mcp_audit_{old_date}.csv"
        old_file.touch()

        # Create recent file
        recent_file = temp_log_dir / f"mcp_audit_{today}.csv"
        recent_file.touch()

        expired = retention.get_expired_files()
        assert len(expired) == 1
        assert old_file in expired
        assert recent_file not in expired

    def test_cleanup_dry_run(self, retention, temp_log_dir):
        """Test cleanup in dry-run mode (no deletion)."""
        # Create an old file
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
            "%Y-%m-%d"
        )
        old_file = temp_log_dir / f"mcp_audit_{old_date}.csv"
        old_file.touch()

        result = retention.cleanup(dry_run=True)
        assert result["dry_run"] is True
        assert result["files_found"] == 1
        assert result["files_removed"] == 0
        assert old_file.exists()

    def test_cleanup_actual(self, retention, temp_log_dir):
        """Test actual cleanup (files deleted)."""
        # Create an old file
        old_date = (datetime.now(timezone.utc) - timedelta(days=10)).strftime(
            "%Y-%m-%d"
        )
        old_file = temp_log_dir / f"mcp_audit_{old_date}.csv"
        old_file.write_text("old log content")

        result = retention.cleanup(dry_run=False)
        assert result["dry_run"] is False
        assert result["files_found"] == 1
        assert result["files_removed"] == 1
        assert not old_file.exists()

    def test_storage_metrics(self, retention, temp_log_dir):
        """Test getting storage metrics."""
        # Create some test files
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = temp_log_dir / f"mcp_audit_{today}.csv"
        log_file.write_text("content\n")

        metrics = retention.get_storage_metrics()
        assert metrics["file_count"] >= 1
        assert metrics["retention_days"] == 7
        assert "total_size_bytes" in metrics


class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_mcp_audit_logger_singleton(self):
        """Test that get_mcp_audit_logger returns singleton."""
        logger1 = get_mcp_audit_logger()
        logger2 = get_mcp_audit_logger()
        assert logger1 is logger2

    def test_log_mcp_audit_convenience(self):
        """Test log_mcp_audit convenience function."""
        # Just verify it doesn't raise
        log_mcp_audit(
            connector_name="test",
            operation="search",
            params_meta={},
            result_meta={},
            duration_ms=100,
            status="success",
        )

    def test_get_retention_manager_singleton(self):
        """Test that get_retention_manager returns singleton."""
        manager1 = get_retention_manager()
        manager2 = get_retention_manager()
        assert manager1 is manager2
