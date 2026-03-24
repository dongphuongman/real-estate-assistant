"""Tests for StubRegistry."""

import pytest

from mcp.stubs import EchoStubConnector
from mcp.testing.stub_registry import StubRegistry


class TestStubRegistry:
    """Tests for StubRegistry."""

    def test_create_registry(self) -> None:
        """Test creating a registry."""
        registry = StubRegistry()

        assert len(registry) == 0
        assert registry._enforce_network_isolation is True

    def test_register_stub(self) -> None:
        """Test registering a stub."""
        registry = StubRegistry()
        stub = registry.register(EchoStubConnector)

        assert len(registry) == 1
        assert "echo_stub" in registry
        assert registry.get("echo_stub") is stub

    def test_register_with_name_override(self) -> None:
        """Test registering with custom name."""
        registry = StubRegistry()
        registry.register(EchoStubConnector, name="custom_echo")

        assert "custom_echo" in registry
        assert "echo_stub" not in registry

    def test_register_with_kwargs(self) -> None:
        """Test registering with constructor kwargs."""
        registry = StubRegistry()
        stub = registry.register(EchoStubConnector, latency_ms=100)

        assert stub._latency_ms == 100

    def test_get_stub(self) -> None:
        """Test getting a registered stub."""
        registry = StubRegistry()
        registry.register(EchoStubConnector)

        stub = registry.get("echo_stub")
        assert isinstance(stub, EchoStubConnector)

    def test_get_stub_not_found(self) -> None:
        """Test getting non-existent stub."""
        registry = StubRegistry()

        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")

    def test_get_all(self) -> None:
        """Test getting all stubs."""
        registry = StubRegistry()
        registry.register(EchoStubConnector)
        registry.register(EchoStubConnector, name="echo2")

        all_stubs = registry.get_all()

        assert len(all_stubs) == 2
        assert "echo_stub" in all_stubs
        assert "echo2" in all_stubs

    def test_contains(self) -> None:
        """Test __contains__ method."""
        registry = StubRegistry()
        registry.register(EchoStubConnector)

        assert "echo_stub" in registry
        assert "nonexistent" not in registry

    def test_len(self) -> None:
        """Test __len__ method."""
        registry = StubRegistry()
        assert len(registry) == 0

        registry.register(EchoStubConnector)
        assert len(registry) == 1

    def test_repr(self) -> None:
        """Test __repr__ method."""
        registry = StubRegistry()
        registry.register(EchoStubConnector)

        repr_str = repr(registry)
        assert "StubRegistry" in repr_str
        assert "echo_stub" in repr_str


class TestStubRegistryCalls:
    """Tests for call tracking in StubRegistry."""

    @pytest.mark.asyncio
    async def test_get_all_calls(self) -> None:
        """Test getting all call histories."""
        registry = StubRegistry()
        stub = registry.register(EchoStubConnector)

        await stub.execute("op1", {"param": "value"})

        calls = registry.get_all_calls()
        assert "echo_stub" in calls
        assert len(calls["echo_stub"]) == 1


class TestStubRegistryVerification:
    """Tests for verification methods."""

    def test_verify_no_network_calls(self) -> None:
        """Test network call verification."""
        registry = StubRegistry()
        registry.register(EchoStubConnector)

        # Should pass - stubs never make network calls
        assert registry.verify_no_network_calls() is True

    def test_verify_with_network_flag(self) -> None:
        """Test verification detects network flag."""
        registry = StubRegistry()
        stub = registry.register(EchoStubConnector)

        # Simulate network call detection (shouldn't happen with real stubs)
        stub._network_call_detected = True

        with pytest.raises(RuntimeError, match="network call"):
            registry.verify_no_network_calls()


class TestStubRegistryReset:
    """Tests for reset and clear methods."""

    @pytest.mark.asyncio
    async def test_reset_all(self) -> None:
        """Test resetting all stubs."""
        registry = StubRegistry()
        stub = registry.register(EchoStubConnector)

        await stub.execute("test", {})
        assert stub.call_count == 1

        registry.reset_all()

        assert stub.call_count == 0

    def test_clear(self) -> None:
        """Test clearing all stubs."""
        registry = StubRegistry()
        registry.register(EchoStubConnector)

        registry.clear()

        assert len(registry) == 0
