"""
StubRegistry for managing MCP test stubs.

Provides centralized stub management with call verification
and network isolation enforcement.
"""

from typing import Any, Dict, List, Optional, Type

from mcp.stubs.base_stub import MCPStub


class StubRegistry:
    """
    Registry for managing test stubs in unit tests.

    Provides centralized stub management with:
    - Automatic registration
    - Call verification
    - Network isolation enforcement

    Usage:
        registry = StubRegistry()
        registry.register(PropertyListingStub, properties=[...])
        stub = registry.get("property_listing_stub")
        # ... run tests ...
        registry.verify_no_network_calls()
        registry.reset_all()

    Attributes:
        stubs: Dictionary mapping stub names to instances
        enforce_network_isolation: Whether to verify no network calls
    """

    def __init__(self, enforce_network_isolation: bool = True) -> None:
        """
        Initialize the registry.

        Args:
            enforce_network_isolation: If True, verify stubs make no network calls
        """
        self._stubs: Dict[str, MCPStub[Any]] = {}
        self._enforce_network_isolation = enforce_network_isolation

    def register(
        self,
        stub_class: Type[MCPStub[Any]],
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> MCPStub[Any]:
        """
        Register a stub instance.

        Args:
            stub_class: The stub class to instantiate
            name: Optional name override (uses class.name by default)
            **kwargs: Arguments to pass to stub constructor

        Returns:
            The created stub instance
        """
        stub = stub_class(**kwargs)
        stub_name = name or stub.name
        self._stubs[stub_name] = stub
        return stub

    def get(self, name: str) -> MCPStub[Any]:
        """
        Get a registered stub by name.

        Args:
            name: The stub name

        Returns:
            The stub instance

        Raises:
            KeyError: If stub not found
        """
        if name not in self._stubs:
            available = list(self._stubs.keys())
            raise KeyError(f"Stub '{name}' not found. Available: {available}")
        return self._stubs[name]

    def get_all(self) -> Dict[str, MCPStub[Any]]:
        """
        Get all registered stubs.

        Returns:
            Dictionary of stub name to instance
        """
        return self._stubs.copy()

    def get_all_calls(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get call history for all stubs.

        Returns:
            Dictionary mapping stub names to their call histories
        """
        result = {}
        for name, stub in self._stubs.items():
            result[name] = stub.get_call_history()
        return result

    def verify_no_network_calls(self) -> bool:
        """
        Verify that no stubs made network calls.

        Since stubs are designed to never make network calls,
        this always returns True if using proper stub classes.

        Returns:
            True if no network calls detected

        Raises:
            RuntimeError: If network calls were detected (shouldn't happen with stubs)
        """
        for name, stub in self._stubs.items():
            # Stubs should never make network calls by design
            if hasattr(stub, "_network_call_detected"):
                raise RuntimeError(
                    f"Stub '{name}' made a network call. Stubs should never access the network."
                )
        return True

    def reset_all(self) -> None:
        """
        Reset all registered stubs.

        Clears call history and resets state for all stubs.
        """
        for stub in self._stubs.values():
            stub.reset()

    def clear(self) -> None:
        """
        Clear all registered stubs.

        Removes all stubs from the registry.
        """
        self._stubs.clear()

    def __contains__(self, name: str) -> bool:
        """Check if a stub is registered."""
        return name in self._stubs

    def __len__(self) -> int:
        """Return number of registered stubs."""
        return len(self._stubs)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"StubRegistry(stubs={list(self._stubs.keys())})"
