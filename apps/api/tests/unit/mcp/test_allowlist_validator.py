"""Tests for MCP AllowlistValidator (Task #68)."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from mcp.allowlist_validator import (
    AllowlistConfig,
    AllowlistEntry,
    AllowlistValidator,
    get_allowlist_validator,
    reset_allowlist_validator,
)
from mcp.config import MCPEdition
from mcp.exceptions import MCPConfigError


class TestAllowlistEntry:
    """Tests for AllowlistEntry dataclass."""

    def test_create_entry_defaults(self) -> None:
        """Test creating entry with default values."""
        entry = AllowlistEntry(
            name="test_connector",
            display_name="Test Connector",
        )

        assert entry.name == "test_connector"
        assert entry.display_name == "Test Connector"
        assert entry.description == ""
        assert entry.enabled is True
        assert entry.edition == MCPEdition.COMMUNITY
        assert entry.added_by == "system"

    def test_create_entry_full(self) -> None:
        """Test creating entry with all values."""
        now = datetime.utcnow()
        entry = AllowlistEntry(
            name="full_connector",
            display_name="Full Connector",
            description="A full connector",
            enabled=False,
            edition=MCPEdition.PRO,
            added_at=now,
            added_by="admin",
        )

        assert entry.name == "full_connector"
        assert entry.display_name == "Full Connector"
        assert entry.description == "A full connector"
        assert entry.enabled is False
        assert entry.edition == MCPEdition.PRO
        assert entry.added_at == now
        assert entry.added_by == "admin"

    def test_entry_to_dict(self) -> None:
        """Test converting entry to dictionary."""
        entry = AllowlistEntry(
            name="dict_connector",
            display_name="Dict Connector",
            description="Test",
            edition=MCPEdition.ENTERPRISE,
        )

        result = entry.to_dict()

        assert result["name"] == "dict_connector"
        assert result["display_name"] == "Dict Connector"
        assert result["description"] == "Test"
        assert result["enabled"] is True
        assert result["edition"] == "enterprise"
        assert "added_at" in result
        assert result["added_by"] == "system"


class TestAllowlistConfig:
    """Tests for AllowlistConfig dataclass."""

    def test_create_config_defaults(self) -> None:
        """Test creating config with defaults."""
        config = AllowlistConfig()

        assert config.edition == MCPEdition.COMMUNITY
        assert config.allowlist == []
        assert config.restricted == []
        assert config.metadata == {}

    def test_get_allowlist_names(self) -> None:
        """Test getting allowlist names."""
        config = AllowlistConfig(
            allowlist=[
                AllowlistEntry(name="conn1", display_name="C1", enabled=True),
                AllowlistEntry(name="conn2", display_name="C2", enabled=False),
                AllowlistEntry(name="conn3", display_name="C3", enabled=True),
            ]
        )

        names = config.get_allowlist_names()

        assert "conn1" in names
        assert "conn2" not in names  # disabled
        assert "conn3" in names

    def test_is_allowlisted(self) -> None:
        """Test checking if connector is allowlisted."""
        config = AllowlistConfig(
            allowlist=[
                AllowlistEntry(name="allowed", display_name="A", enabled=True),
                AllowlistEntry(name="disabled", display_name="D", enabled=False),
            ]
        )

        assert config.is_allowlisted("allowed") is True
        assert config.is_allowlisted("disabled") is False
        assert config.is_allowlisted("unknown") is False

    def test_get_entry(self) -> None:
        """Test getting entry by name."""
        entry1 = AllowlistEntry(name="conn1", display_name="C1")
        entry2 = AllowlistEntry(name="conn2", display_name="C2")
        config = AllowlistConfig(allowlist=[entry1, entry2])

        result = config.get_entry("conn1")

        assert result is entry1

    def test_get_entry_not_found(self) -> None:
        """Test getting entry that doesn't exist."""
        config = AllowlistConfig()

        result = config.get_entry("nonexistent")

        assert result is None

    def test_config_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config = AllowlistConfig(
            edition=MCPEdition.PRO,
            allowlist=[
                AllowlistEntry(name="conn1", display_name="C1"),
            ],
            restricted=[
                AllowlistEntry(name="rest1", display_name="R1"),
            ],
            metadata={"version": "1.0"},
        )

        result = config.to_dict()

        assert result["edition"] == "pro"
        assert len(result["allowlist"]) == 1
        assert len(result["restricted"]) == 1
        assert result["metadata"]["version"] == "1.0"


class TestAllowlistValidator:
    """Tests for AllowlistValidator class."""

    def setup_method(self) -> None:
        """Reset validator before each test."""
        reset_allowlist_validator()

    def teardown_method(self) -> None:
        """Reset validator after each test."""
        reset_allowlist_validator()

    def test_create_validator_default_path(self) -> None:
        """Test creating validator with default path."""
        validator = AllowlistValidator()

        assert validator.config_path == AllowlistValidator.DEFAULT_CONFIG_PATH

    def test_create_validator_custom_path(self) -> None:
        """Test creating validator with custom path."""
        custom_path = Path("/custom/path.yaml")
        validator = AllowlistValidator(config_path=custom_path)

        assert validator.config_path == custom_path

    def test_load_config_file_not_found(self) -> None:
        """Test loading config when file doesn't exist."""
        validator = AllowlistValidator(config_path=Path("/nonexistent.yaml"))

        config = validator.load_config()

        # Should return default config
        assert config.edition == MCPEdition.COMMUNITY
        assert len(config.allowlist) >= 1  # At least echo_stub

    def test_load_config_from_yaml(self) -> None:
        """Test loading config from YAML file."""
        yaml_content = """
edition: pro
allowlist:
  - name: test_conn
    display_name: Test Connector
    description: A test connector
    enabled: true
    edition: community

restricted:
  - name: premium_conn
    display_name: Premium Connector
    min_edition: enterprise

metadata:
  version: "1.0.0"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            validator = AllowlistValidator(config_path=temp_path)
            config = validator.load_config()

            assert config.edition == MCPEdition.PRO
            assert len(config.allowlist) == 1
            assert config.allowlist[0].name == "test_conn"
            assert len(config.restricted) == 1
            assert config.restricted[0].name == "premium_conn"
            assert config.metadata["version"] == "1.0.0"
        finally:
            temp_path.unlink(missing_ok=True)

    def test_load_config_invalid_yaml(self) -> None:
        """Test loading config with invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            f.flush()
            temp_path = Path(f.name)

        try:
            validator = AllowlistValidator(config_path=temp_path)

            with pytest.raises(MCPConfigError):
                validator.load_config()
        finally:
            temp_path.unlink(missing_ok=True)

    def test_config_property_lazy_load(self) -> None:
        """Test that config property lazy loads."""
        validator = AllowlistValidator(config_path=Path("/nonexistent.yaml"))

        # Access config property
        config1 = validator.config
        config2 = validator.config

        assert config1 is config2  # Should be cached

    def test_validate_connector_ce_allowlisted(self) -> None:
        """Test validation in CE for allowlisted connector."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(
            edition=MCPEdition.COMMUNITY,
            allowlist=[
                AllowlistEntry(name="allowed", display_name="A", enabled=True),
            ],
        )

        result = validator.validate_connector("allowed", MCPEdition.COMMUNITY)

        assert result is True

    def test_validate_connector_ce_not_allowlisted(self) -> None:
        """Test validation in CE for non-allowlisted connector."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(
            edition=MCPEdition.COMMUNITY,
            allowlist=[
                AllowlistEntry(name="allowed", display_name="A"),
            ],
        )

        result = validator.validate_connector("not_allowed", MCPEdition.COMMUNITY)

        assert result is False

    def test_validate_connector_ce_disabled_entry(self) -> None:
        """Test validation in CE for disabled allowlist entry."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(
            edition=MCPEdition.COMMUNITY,
            allowlist=[
                AllowlistEntry(name="disabled", display_name="D", enabled=False),
            ],
        )

        result = validator.validate_connector("disabled", MCPEdition.COMMUNITY)

        assert result is False

    def test_validate_connector_pro_allows_all(self) -> None:
        """Test validation in PRO allows all connectors."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(
            edition=MCPEdition.PRO,
            allowlist=[],  # Empty allowlist
        )

        # Should allow any connector in PRO
        result = validator.validate_connector("any_connector", MCPEdition.PRO)

        assert result is True

    def test_validate_connector_enterprise_allows_all(self) -> None:
        """Test validation in Enterprise allows all connectors."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(edition=MCPEdition.ENTERPRISE)

        result = validator.validate_connector("any_connector", MCPEdition.ENTERPRISE)

        assert result is True

    def test_log_violation(self) -> None:
        """Test logging violations."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(edition=MCPEdition.COMMUNITY)

        validator.log_violation(
            connector_name="blocked_conn",
            operation="get_connector",
            context={"user": "test_user"},
        )

        violations = validator.get_violations()

        assert len(violations) == 1
        assert violations[0]["connector"] == "blocked_conn"
        assert violations[0]["operation"] == "get_connector"
        assert violations[0]["context"]["user"] == "test_user"

    def test_clear_violations(self) -> None:
        """Test clearing violations."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig()

        validator.log_violation("conn1", "op1")
        validator.log_violation("conn2", "op2")

        assert len(validator.get_violations()) == 2

        validator.clear_violations()

        assert len(validator.get_violations()) == 0

    def test_add_connector(self) -> None:
        """Test adding connector to allowlist."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig()

        entry = validator.add_connector(
            name="new_conn",
            display_name="New Connector",
            description="Test",
            edition=MCPEdition.COMMUNITY,
            added_by="test",
        )

        assert entry.name == "new_conn"
        assert entry.display_name == "New Connector"
        assert validator.config.is_allowlisted("new_conn")

    def test_add_connector_existing_updates(self) -> None:
        """Test adding existing connector updates it."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(
            allowlist=[
                AllowlistEntry(name="existing", display_name="Old Name"),
            ]
        )

        validator.add_connector(
            name="existing",
            display_name="New Name",
            description="Updated",
            added_by="test",
        )

        entry = validator.config.get_entry("existing")
        assert entry is not None
        assert entry.display_name == "New Name"
        assert entry.description == "Updated"

    def test_remove_connector(self) -> None:
        """Test removing connector from allowlist."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig(
            allowlist=[
                AllowlistEntry(name="to_remove", display_name="To Remove"),
                AllowlistEntry(name="to_keep", display_name="To Keep"),
            ]
        )

        result = validator.remove_connector("to_remove")

        assert result is True
        assert not validator.config.is_allowlisted("to_remove")
        assert validator.config.is_allowlisted("to_keep")

    def test_remove_connector_not_found(self) -> None:
        """Test removing non-existent connector."""
        validator = AllowlistValidator()
        validator._config = AllowlistConfig()

        result = validator.remove_connector("nonexistent")

        assert result is False

    def test_reload_config(self) -> None:
        """Test reloading configuration."""
        yaml_content = """
edition: community
allowlist:
  - name: reloaded_conn
    display_name: Reloaded Connector
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)

        try:
            validator = AllowlistValidator(config_path=temp_path)
            config1 = validator.config

            # Modify file
            new_content = """
edition: pro
allowlist:
  - name: new_conn
    display_name: New Connector
"""
            with open(temp_path, "w") as f:
                f.write(new_content)

            config2 = validator.reload_config()

            assert config2.edition == MCPEdition.PRO
            assert config1 is not config2
        finally:
            temp_path.unlink(missing_ok=True)


class TestGetAllowlistValidator:
    """Tests for module-level validator functions."""

    def setup_method(self) -> None:
        """Reset validator before each test."""
        reset_allowlist_validator()

    def teardown_method(self) -> None:
        """Reset validator after each test."""
        reset_allowlist_validator()

    def test_get_validator_singleton(self) -> None:
        """Test that get_allowlist_validator returns singleton."""
        validator1 = get_allowlist_validator()
        validator2 = get_allowlist_validator()

        assert validator1 is validator2

    def test_reset_creates_new_instance(self) -> None:
        """Test that reset creates new instance."""
        validator1 = get_allowlist_validator()
        reset_allowlist_validator()
        validator2 = get_allowlist_validator()

        assert validator1 is not validator2
