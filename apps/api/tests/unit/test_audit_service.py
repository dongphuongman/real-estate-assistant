"""Tests for the audit service.

Tests the AuditService using a mock repository to verify
log creation and query delegation without database access.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.audit_service import AuditService


@pytest.fixture
def mock_repo():
    """Create a mock AuditLogRepository."""
    repo = MagicMock()
    repo.append = AsyncMock()
    repo.query = AsyncMock(return_value=([], 0))
    repo.verify_chain = AsyncMock(return_value={"valid": True, "checked": 0})
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def audit_service(mock_session, mock_repo):
    """Create an AuditService with mocked dependencies."""
    with patch("services.audit_service.AuditLogRepository", return_value=mock_repo):
        svc = AuditService(mock_session)
        svc.repo = mock_repo
        return svc


class TestAuditLog:
    """Tests for audit log creation."""

    @pytest.mark.asyncio
    async def test_log_creates_entry(self, audit_service, mock_repo):
        await audit_service.log(
            action="user.login",
            actor_id="user-123",
            actor_email="test@example.com",
        )
        mock_repo.append.assert_called_once()
        call_kwargs = mock_repo.append.call_args[1]
        assert call_kwargs["action"] == "user.login"
        assert call_kwargs["actor_id"] == "user-123"
        assert call_kwargs["actor_email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_log_commits(self, audit_service, mock_session):
        await audit_service.log(action="test.action")
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_rollback_on_error(self, audit_service, mock_repo, mock_session):
        mock_repo.append.side_effect = Exception("DB error")
        await audit_service.log(action="fail.action")
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_with_details(self, audit_service, mock_repo):
        details = {"before": "old_value", "after": "new_value"}
        await audit_service.log(
            action="resource.update",
            resource="property/123",
            details=details,
        )
        call_kwargs = mock_repo.append.call_args[1]
        assert call_kwargs["details"] == details
        assert call_kwargs["resource"] == "property/123"


class TestAuditQuery:
    """Tests for audit log querying."""

    @pytest.mark.asyncio
    async def test_query_by_action(self, audit_service, mock_repo):
        await audit_service.query(action="user.login")
        mock_repo.query.assert_called_once()
        call_kwargs = mock_repo.query.call_args[1]
        assert call_kwargs["action"] == "user.login"

    @pytest.mark.asyncio
    async def test_query_by_actor(self, audit_service, mock_repo):
        await audit_service.query(actor_id="user-123")
        call_kwargs = mock_repo.query.call_args[1]
        assert call_kwargs["actor_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_query_returns_tuple(self, audit_service):
        result = await audit_service.query(action="test")
        assert isinstance(result, tuple)
        assert len(result) == 2  # (entries, total)

    @pytest.mark.asyncio
    async def test_query_with_pagination(self, audit_service, mock_repo):
        await audit_service.query(limit=50, offset=100)
        call_kwargs = mock_repo.query.call_args[1]
        assert call_kwargs["limit"] == 50
        assert call_kwargs["offset"] == 100


class TestAuditChainVerification:
    """Tests for hash chain verification."""

    @pytest.mark.asyncio
    async def test_verify_chain_delegates(self, audit_service, mock_repo):
        mock_repo.verify_chain.return_value = {"valid": True, "checked": 10}
        result = await audit_service.verify_chain(limit=100)
        mock_repo.verify_chain.assert_called_once_with(limit=100)
        assert result["valid"] is True
        assert result["checked"] == 10
