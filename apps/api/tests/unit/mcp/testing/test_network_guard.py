"""Tests for NetworkGuard."""

import socket

import pytest

from mcp.testing.network_guard import NetworkGuard, NetworkIsolationError, assert_no_network_calls


class TestNetworkGuard:
    """Tests for NetworkGuard."""

    def test_not_active_by_default(self) -> None:
        """Test network guard is not active by default."""
        assert NetworkGuard.is_active() is False

    def test_enabled_context_manager(self) -> None:
        """Test enabling network guard."""
        with NetworkGuard.enabled():
            assert NetworkGuard.is_active() is True

        assert NetworkGuard.is_active() is False

    def test_disabled_context_manager(self) -> None:
        """Test disabled context manager."""
        with NetworkGuard.disabled():
            assert NetworkGuard.is_active() is False

    def test_verify_isolation(self) -> None:
        """Test verify_isolation method."""
        with NetworkGuard.enabled() as guard:
            assert guard.verify_isolation() is True

    def test_verify_isolation_not_active(self) -> None:
        """Test verify_isolation raises when not active."""
        guard = NetworkGuard()
        with pytest.raises(RuntimeError, match="not active"):
            guard.verify_isolation()


class TestNetworkGuardBlocking:
    """Tests for network call blocking."""

    def test_blocks_socket_creation(self) -> None:
        """Test that socket creation is blocked."""
        with NetworkGuard.enabled():
            with pytest.raises(NetworkIsolationError, match="Network call"):
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def test_blocks_socket_connect(self) -> None:
        """Test that socket connect is blocked."""
        with NetworkGuard.enabled():
            with pytest.raises(NetworkIsolationError):
                # This will fail at socket creation
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def test_allows_after_context(self) -> None:
        """Test that network is allowed after context."""
        with NetworkGuard.enabled():
            pass  # Network blocked here

        # Should be able to check network after (if available)
        # Note: This test doesn't actually make a network call
        assert NetworkGuard.is_active() is False


class TestNetworkIsolationError:
    """Tests for NetworkIsolationError."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = NetworkIsolationError("Test message")
        assert "Test message" in str(error)

    def test_error_inheritance(self) -> None:
        """Test error inherits from Exception."""
        error = NetworkIsolationError("test")
        assert isinstance(error, Exception)


class TestAssertNoNetworkCalls:
    """Tests for assert_no_network_calls decorator."""

    def test_sync_function(self) -> None:
        """Test decorator with sync function."""

        @assert_no_network_calls
        def sync_func():
            return "success"

        result = sync_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_function(self) -> None:
        """Test decorator with async function."""

        @assert_no_network_calls
        async def async_func():
            return "async_success"

        result = await async_func()
        assert result == "async_success"

    def test_function_raises_on_network(self) -> None:
        """Test decorator raises on network call."""

        @assert_no_network_calls
        def network_func():
            # This will raise NetworkIsolationError
            socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        with pytest.raises(NetworkIsolationError):
            network_func()


class TestCheckNetworkAvailable:
    """Tests for check_network_available static method."""

    def test_method_exists(self) -> None:
        """Test method exists and is callable."""
        # Just verify it's callable, don't actually make network call
        assert hasattr(NetworkGuard, "check_network_available")
        assert callable(NetworkGuard.check_network_available)
