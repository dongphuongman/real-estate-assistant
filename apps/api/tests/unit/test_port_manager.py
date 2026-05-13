"""Unit tests for Port Manager module."""

import json

# Add scripts directory to path for imports
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts"))

from port.port_manager import PortManager  # noqa: E402  # noqa: E402


@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Create temporary project root with registry directory."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def port_manager(temp_project_root: Path) -> PortManager:
    """Create PortManager instance with temporary project root."""
    return PortManager(temp_project_root)


class TestPortManagerRegistry:
    """Tests for registry management."""

    def test_load_or_create_registry_creates_new(self, port_manager: PortManager) -> None:
        """Test registry creation when none exists."""
        registry = port_manager.registry
        assert registry["version"] == "1.0.0"
        assert "frontend" in registry["ranges"]
        assert "backend" in registry["ranges"]

    def test_registry_has_correct_ranges(self, port_manager: PortManager) -> None:
        """Test registry has correct port ranges."""
        registry = port_manager.registry
        assert registry["ranges"]["frontend"]["start"] == 3800
        assert registry["ranges"]["frontend"]["end"] == 3899
        assert registry["ranges"]["backend"]["start"] == 8000
        assert registry["ranges"]["backend"]["end"] == 8099

    def test_save_registry_creates_file(self, port_manager: PortManager) -> None:
        """Test saving registry creates the file."""
        port_manager._save_registry()
        registry_path = port_manager.registry_path
        assert registry_path.exists()

        with open(registry_path) as f:
            saved = json.load(f)
        assert saved["version"] == "1.0.0"


class TestPortManagerAllocation:
    """Tests for port allocation."""

    def test_find_available_port_default(self, port_manager: PortManager) -> None:
        """Test finding available port uses default first."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            port = port_manager.find_available_port("backend")
            assert port == 8000  # Default

    def test_find_available_port_skips_used(self, port_manager: PortManager) -> None:
        """Test finding available port skips system-used ports."""

        def mock_system_check(port: int) -> bool:
            return port == 8000  # 8000 is in use

        with patch.object(port_manager, "_is_port_in_use_system", side_effect=mock_system_check):
            port = port_manager.find_available_port("backend")
            assert port == 8001  # Next available

    def test_find_available_port_respects_preferred(self, port_manager: PortManager) -> None:
        """Test finding available port with preferred port."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            port = port_manager.find_available_port("backend", preferred=8050)
            assert port == 8050

    def test_find_available_port_ignores_out_of_range_preferred(
        self, port_manager: PortManager
    ) -> None:
        """Test that out-of-range preferred port is ignored."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            # 9999 is out of backend range (8000-8099)
            port = port_manager.find_available_port("backend", preferred=9999)
            assert port == 8000  # Falls back to default

    def test_allocate_port_creates_allocation(self, port_manager: PortManager) -> None:
        """Test port allocation creates registry entry."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            port = port_manager.allocate_port("backend", "test-service")
            assert port == 8000

            # Verify allocation in registry
            alloc = port_manager.get_allocation("test-service")
            assert alloc is not None
            assert alloc["port"] == 8000
            assert alloc["status"] == "active"

    def test_allocate_port_updates_existing(self, port_manager: PortManager) -> None:
        """Test allocating for same service updates existing entry."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            # First allocation
            port1 = port_manager.allocate_port("backend", "test-service")
            assert port1 == 8000

            # Second allocation should update
            port2 = port_manager.allocate_port("backend", "test-service")
            assert (
                port2 == 8001
            )  # First alloc occupies 8000 in registry, second gets next available

            # Should still have only one allocation for this service
            allocations = [
                a
                for a in port_manager.registry["allocations"]
                if a["serviceName"] == "test-service"
            ]
            assert len(allocations) == 1

    def test_release_port_marks_inactive(self, port_manager: PortManager) -> None:
        """Test releasing port marks allocation as inactive."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            port = port_manager.allocate_port("backend", "test-service")
            result = port_manager.release_port(port)

            assert result is True
            alloc = port_manager.get_allocation("test-service")
            assert (
                alloc is None
            )  # get_allocation filters by status="active", so released alloc returns None

    def test_release_unknown_port_returns_false(self, port_manager: PortManager) -> None:
        """Test releasing unknown port returns False."""
        result = port_manager.release_port(99999)
        assert result is False


class TestPortManagerSystemCheck:
    """Tests for system-level port checking."""

    def test_is_port_in_use_free_port(self, port_manager: PortManager) -> None:
        """Test checking a free port returns False."""
        # Port 59999 should not be in use
        result = port_manager._is_port_in_use_system(59999)
        assert result is False

    def test_is_port_in_use_check_works(self, port_manager: PortManager) -> None:
        """Test that port checking mechanism works."""
        # This test verifies the mechanism works without assuming specific ports
        # Just check that the method doesn't raise an exception
        try:
            port_manager._is_port_in_use_system(8000)
        except Exception as e:
            pytest.fail(f"_is_port_in_use_system raised exception: {e}")


class TestPortManagerParentIntegration:
    """Tests for parent registry integration."""

    def test_get_parent_registry_ports_empty_when_no_parent(
        self, port_manager: PortManager
    ) -> None:
        """Test parent registry returns empty when no parent exists."""
        # The temp project root has no parent registry
        used = port_manager._get_parent_registry_ports("backend")
        assert used == set()

    def test_get_registry_ports_returns_allocated(self, port_manager: PortManager) -> None:
        """Test getting registry ports returns allocated ports."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            port_manager.allocate_port("backend", "service1")
            port_manager.allocate_port("frontend", "service2")

            backend_ports = port_manager._get_registry_ports("backend")
            frontend_ports = port_manager._get_registry_ports("frontend")

            assert 8000 in backend_ports
            assert 3800 in frontend_ports


class TestPortManagerCrossPlatform:
    """Tests for cross-platform process management."""

    def test_kill_process_on_unused_port(self, port_manager: PortManager) -> None:
        """Test kill port on unused port returns False gracefully."""
        result = port_manager.kill_process_on_port(59999, force=False)
        # Should not raise, returns False if no process found
        assert result is False

    def test_kill_process_on_unused_port_force(self, port_manager: PortManager) -> None:
        """Test force kill port on unused port returns False gracefully."""
        result = port_manager.kill_process_on_port(59998, force=True)
        assert result is False


class TestPortManagerGetters:
    """Tests for getter methods."""

    def test_get_allocation_none_when_not_found(self, port_manager: PortManager) -> None:
        """Test get_allocation returns None for unknown service."""
        alloc = port_manager.get_allocation("nonexistent-service")
        assert alloc is None

    def test_get_all_allocated_ports(self, port_manager: PortManager) -> None:
        """Test getting all allocated ports."""
        with patch.object(port_manager, "_is_port_in_use_system", return_value=False):
            port_manager.allocate_port("backend", "backend-svc")
            port_manager.allocate_port("frontend", "frontend-svc")

            ports = port_manager.get_all_allocated_ports()

            assert ports["backend"] == 8000
            assert ports["frontend"] == 3800


class TestPortManagerErrorHandling:
    """Tests for error handling."""

    def test_no_available_ports_raises(self, port_manager: PortManager) -> None:
        """Test error when no ports available."""
        # Mock all ports in use
        with patch.object(port_manager, "_is_port_in_use_system", return_value=True):
            with patch.object(port_manager, "_get_registry_ports", return_value=set()):
                with patch.object(port_manager, "_get_parent_registry_ports", return_value=set()):
                    with pytest.raises(RuntimeError, match="No available ports"):
                        port_manager.find_available_port("backend")

    def test_invalid_category_raises_value_error(self, port_manager: PortManager) -> None:
        """Test invalid category raises ValueError."""
        with pytest.raises(ValueError, match="Unknown category"):
            port_manager.find_available_port("invalid_category")
