"""
Unit tests for RankingConfigService.

Tests configuration management, caching, and weight retrieval.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import RankingConfig
from services.ranking_config_service import (
    DEFAULT_RANKING_CONFIG,
    RankingConfigService,
    RankingWeights,
    get_ranking_config_service,
)


@pytest.fixture
def ranking_config_service(
    db_session: AsyncSession,
) -> RankingConfigService:
    """Create a RankingConfigService instance."""
    return RankingConfigService(db_session)


@pytest.mark.asyncio
async def test_create_config(ranking_config_service: RankingConfigService):
    """Test creating a new ranking configuration."""
    config = await ranking_config_service.create_config(
        name="test_config",
        description="Test configuration",
        alpha=0.8,
        boost_exact_match=2.0,
    )

    assert config.id is not None
    assert config.name == "test_config"
    assert config.description == "Test configuration"
    assert config.alpha == 0.8
    assert config.boost_exact_match == 2.0
    assert config.is_active is False  # New configs start inactive


@pytest.mark.asyncio
async def test_create_config_duplicate_name(
    ranking_config_service: RankingConfigService,
):
    """Test that duplicate names are rejected."""
    await ranking_config_service.create_config(name="duplicate")

    with pytest.raises(ValueError, match="already exists"):
        await ranking_config_service.create_config(name="duplicate")


@pytest.mark.asyncio
async def test_get_config_by_id(ranking_config_service: RankingConfigService):
    """Test retrieving a configuration by ID."""
    created = await ranking_config_service.create_config(name="test")

    retrieved = await ranking_config_service.get_config_by_id(str(created.id))

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == "test"


@pytest.mark.asyncio
async def test_get_config_by_name(ranking_config_service: RankingConfigService):
    """Test retrieving a configuration by name."""
    await ranking_config_service.create_config(name="by_name")

    retrieved = await ranking_config_service.get_config_by_name("by_name")

    assert retrieved is not None
    assert retrieved.name == "by_name"


@pytest.mark.asyncio
async def test_get_active_config_none(
    ranking_config_service: RankingConfigService,
):
    """Test that no config is returned when none is active."""
    # Create inactive config
    await ranking_config_service.create_config(name="inactive")

    active = await ranking_config_service.get_active_config()

    # No active config should be returned
    assert active is None


@pytest.mark.asyncio
async def test_activate_config(ranking_config_service: RankingConfigService):
    """Test activating a configuration."""
    config1 = await ranking_config_service.create_config(name="config1")
    config2 = await ranking_config_service.create_config(name="config2")

    # Activate first config
    activated = await ranking_config_service.activate_config(str(config1.id))

    assert activated is not None
    assert activated.is_active is True

    # Verify it's the active config
    active = await ranking_config_service.get_active_config()
    assert active is not None
    assert active.id == config1.id

    # Activate second config - should deactivate first
    activated2 = await ranking_config_service.activate_config(str(config2.id))
    assert activated2 is not None
    assert activated2.is_active is True

    # Verify only second is active
    active = await ranking_config_service.get_active_config()
    assert active is not None
    assert active.id == config2.id


@pytest.mark.asyncio
async def test_update_config(ranking_config_service: RankingConfigService):
    """Test updating a configuration."""
    config = await ranking_config_service.create_config(
        name="original", alpha=0.7, boost_exact_match=1.5
    )

    updated = await ranking_config_service.update_config(
        str(config.id),
        name="updated",
        alpha=0.8,
    )

    assert updated is not None
    assert updated.name == "updated"
    assert updated.alpha == 0.8
    assert updated.boost_exact_match == 1.5  # Unchanged


@pytest.mark.asyncio
async def test_delete_config(ranking_config_service: RankingConfigService):
    """Test deleting a configuration."""
    config = await ranking_config_service.create_config(name="to_delete")

    deleted = await ranking_config_service.delete_config(str(config.id))

    assert deleted is True

    # Verify it's gone
    retrieved = await ranking_config_service.get_config_by_id(str(config.id))
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_active_config_fails(
    ranking_config_service: RankingConfigService,
):
    """Test that deleting an active configuration fails."""
    config = await ranking_config_service.create_config(name="active")
    await ranking_config_service.activate_config(str(config.id))

    with pytest.raises(ValueError, match="Cannot delete the active"):
        await ranking_config_service.delete_config(str(config.id))


@pytest.mark.asyncio
async def test_get_active_weights(ranking_config_service: RankingConfigService):
    """Test getting active weights returns a dictionary."""
    config = await ranking_config_service.create_config(
        name="weighted", alpha=0.85, boost_exact_match=2.5
    )
    await ranking_config_service.activate_config(str(config.id))

    weights = await ranking_config_service.get_active_weights()

    assert isinstance(weights, dict)
    assert weights["alpha"] == 0.85
    assert weights["boost_exact_match"] == 2.5


@pytest.mark.asyncio
async def test_get_active_weights_default_when_none_active(
    ranking_config_service: RankingConfigService,
):
    """Test that default weights are returned when no config is active."""
    weights = await ranking_config_service.get_active_weights()

    # Should return default values
    assert weights["alpha"] == DEFAULT_RANKING_CONFIG["alpha"]
    assert weights["boost_exact_match"] == DEFAULT_RANKING_CONFIG["boost_exact_match"]


@pytest.mark.asyncio
async def test_list_configs(ranking_config_service: RankingConfigService):
    """Test listing configurations."""
    await ranking_config_service.create_config(name="config1")
    await ranking_config_service.create_config(name="config2")

    # By default, only active configs are returned (none are active)
    active_configs = await ranking_config_service.list_configs()
    assert len(active_configs) == 0  # Only default is returned

    # Include inactive configs
    configs = await ranking_config_service.list_configs(include_inactive=True)
    assert len(configs) == 2


@pytest.mark.asyncio
async def test_list_configs_exclude_inactive(
    ranking_config_service: RankingConfigService,
):
    """Test listing only active configurations."""
    await ranking_config_service.create_config(name="inactive1")
    config2 = await ranking_config_service.create_config(name="active1")
    await ranking_config_service.activate_config(str(config2.id))

    # Only active configs
    configs = await ranking_config_service.list_configs(include_inactive=False)

    assert len(configs) == 1
    assert configs[0].name == "active1"


# Tests for RankingWeights dataclass


def test_ranking_weights_default():
    """Test RankingWeights default values."""
    weights = RankingWeights.default()

    assert weights.alpha == DEFAULT_RANKING_CONFIG["alpha"]
    assert weights.boost_exact_match == DEFAULT_RANKING_CONFIG["boost_exact_match"]
    assert weights.config_id is None
    assert weights.config_name is None


def test_ranking_weights_from_model():
    """Test creating RankingWeights from a model."""
    config = RankingConfig(
        name="test",
        alpha=0.75,
        boost_exact_match=1.8,
        boost_metadata_match=1.4,
        boost_quality_signals=1.3,
        diversity_penalty=0.85,
        weight_recency=0.15,
        weight_price_match=0.2,
        weight_location=0.12,
        personalization_enabled=True,
        personalization_weight=0.25,
    )
    # Manually set ID since it's not persisted
    config.id = "test-id-123"

    weights = RankingWeights.from_model(config)

    assert weights.alpha == 0.75
    assert weights.boost_exact_match == 1.8
    assert weights.config_id == "test-id-123"
    assert weights.config_name == "test"
    assert weights.personalization_enabled is True


def test_ranking_weights_to_dict():
    """Test converting RankingWeights to dictionary."""
    weights = RankingWeights(
        alpha=0.8,
        boost_exact_match=2.0,
        config_id="test-id",
        config_name="test",
    )

    d = weights.to_dict()

    assert d["alpha"] == 0.8
    assert d["boost_exact_match"] == 2.0
    # config_id and config_name should not be in dict
    assert "config_id" not in d
    assert "config_name" not in d


def test_get_ranking_config_service_factory(db_session: AsyncSession):
    """Test the factory function."""
    service = get_ranking_config_service(db_session)

    assert isinstance(service, RankingConfigService)
    assert service.session == db_session
