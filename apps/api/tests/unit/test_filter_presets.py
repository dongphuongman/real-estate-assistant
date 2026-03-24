"""Unit tests for Filter Presets feature (Task #75)."""

from datetime import UTC, datetime

import pytest

from db.models import User
from db.repositories import FilterPresetRepository
from db.schemas import FilterPresetCreate, FilterPresetUpdate


class TestFilterPresetRepository:
    """Tests for FilterPresetRepository."""

    @pytest.mark.asyncio
    async def test_create_preset(self, db_session):
        """Test creating a filter preset."""
        repo = FilterPresetRepository(db_session)

        # Create user first
        user = User(
            id="test-user-1",
            email="test1@example.com",
            hashed_password="hashed",
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        preset = await repo.create(
            user_id=user.id,
            name="Budget Apartments",
            filters={"city": "Krakow", "max_price": 1000},
            description="Cheap apartments in Krakow",
        )

        assert preset.id is not None
        assert preset.name == "Budget Apartments"
        assert preset.filters == {"city": "Krakow", "max_price": 1000}
        assert preset.is_default is False
        assert preset.use_count == 0

    @pytest.mark.asyncio
    async def test_get_by_id_scoped_to_user(self, db_session):
        """Test that get_by_id only returns presets for the correct user."""
        repo = FilterPresetRepository(db_session)

        # Create two users
        user1 = User(
            id="user-1",
            email="user1@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        user2 = User(
            id="user-2",
            email="user2@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add_all([user1, user2])
        await db_session.flush()

        # Create preset for user1
        preset1 = await repo.create(
            user_id=user1.id,
            name="User 1 Preset",
            filters={"city": "Warsaw"},
        )

        # User1 can access their preset
        found = await repo.get_by_id(preset1.id, user1.id)
        assert found is not None
        assert found.name == "User 1 Preset"

        # User2 cannot access user1's preset
        not_found = await repo.get_by_id(preset1.id, user2.id)
        assert not_found is None

    @pytest.mark.asyncio
    async def test_get_by_user_ordered_correctly(self, db_session):
        """Test that presets are returned in correct order."""
        repo = FilterPresetRepository(db_session)

        user = User(
            id="test-user",
            email="test@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create multiple presets
        p1 = await repo.create(
            user_id=user.id,
            name="Preset A",
            filters={"city": "A"},
        )
        p2 = await repo.create(
            user_id=user.id,
            name="Preset B",
            filters={"city": "B"},
            is_default=True,
        )
        p3 = await repo.create(
            user_id=user.id,
            name="Preset C",
            filters={"city": "C"},
        )

        # Increment usage on p3
        p3.use_count = 5
        await db_session.flush()

        presets = await repo.get_by_user(user.id)

        # Default first, then by use_count, then by created_at
        assert len(presets) == 3
        assert presets[0].id == p2.id  # Default first
        # p3 has higher use_count, so it should be second
        assert presets[1].id == p3.id
        assert presets[2].id == p1.id

    @pytest.mark.asyncio
    async def test_count_by_user(self, db_session):
        """Test counting presets per user."""
        repo = FilterPresetRepository(db_session)

        user = User(
            id="count-user",
            email="count@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        count = await repo.count_by_user(user.id)
        assert count == 0

        await repo.create(user_id=user.id, name="P1", filters={})
        await repo.create(user_id=user.id, name="P2", filters={})

        count = await repo.count_by_user(user.id)
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_default(self, db_session):
        """Test getting user's default preset."""
        repo = FilterPresetRepository(db_session)

        user = User(
            id="default-user",
            email="default@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # No default initially
        default = await repo.get_default(user.id)
        assert default is None

        # Create a default preset
        await repo.create(
            user_id=user.id,
            name="My Default",
            filters={"city": "Krakow"},
            is_default=True,
        )

        default = await repo.get_default(user.id)
        assert default is not None
        assert default.name == "My Default"

    @pytest.mark.asyncio
    async def test_set_default_unsets_others(self, db_session):
        """Test that setting default unsets other defaults."""
        repo = FilterPresetRepository(db_session)

        user = User(
            id="set-default-user",
            email="setdefault@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        # Create multiple presets, first as default
        p1 = await repo.create(
            user_id=user.id,
            name="First Default",
            filters={"city": "A"},
            is_default=True,
        )
        p2 = await repo.create(
            user_id=user.id,
            name="Second",
            filters={"city": "B"},
        )

        # Verify p1 is default
        assert p1.is_default is True
        assert p2.is_default is False

        # Set p2 as default
        await repo.set_default(p2, user.id)

        # Refresh from db
        await db_session.refresh(p1)
        await db_session.refresh(p2)

        assert p1.is_default is False
        assert p2.is_default is True

    @pytest.mark.asyncio
    async def test_increment_usage(self, db_session):
        """Test incrementing usage count and updating last_used_at."""
        repo = FilterPresetRepository(db_session)

        user = User(
            id="usage-user",
            email="usage@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        preset = await repo.create(
            user_id=user.id,
            name="Usage Test",
            filters={},
        )

        assert preset.use_count == 0
        assert preset.last_used_at is None

        before = datetime.now(UTC)
        updated = await repo.increment_usage(preset)

        assert updated.use_count == 1
        assert updated.last_used_at is not None
        assert updated.last_used_at >= before

        # Increment again
        updated = await repo.increment_usage(preset)
        assert updated.use_count == 2

    @pytest.mark.asyncio
    async def test_update_preset(self, db_session):
        """Test updating preset fields."""
        repo = FilterPresetRepository(db_session)

        user = User(
            id="update-user",
            email="update@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        preset = await repo.create(
            user_id=user.id,
            name="Original Name",
            filters={"city": "Warsaw"},
        )

        updated = await repo.update(
            preset,
            name="New Name",
            description="Added description",
            filters={"city": "Krakow", "max_price": 1000},
        )

        assert updated.name == "New Name"
        assert updated.description == "Added description"
        assert updated.filters == {"city": "Krakow", "max_price": 1000}

    @pytest.mark.asyncio
    async def test_delete_preset(self, db_session):
        """Test deleting a preset."""
        repo = FilterPresetRepository(db_session)

        user = User(
            id="delete-user",
            email="delete@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        preset = await repo.create(
            user_id=user.id,
            name="To Delete",
            filters={},
        )

        preset_id = preset.id

        # Verify it exists
        found = await repo.get_by_id(preset_id, user.id)
        assert found is not None

        # Delete
        await repo.delete(preset)

        # Verify deleted
        found = await repo.get_by_id(preset_id, user.id)
        assert found is None


class TestFilterPresetSchemas:
    """Tests for Pydantic schemas."""

    def test_create_schema_valid(self):
        """Test valid FilterPresetCreate schema."""
        data = FilterPresetCreate(
            name="Test Preset",
            filters={"city": "Berlin", "max_price": 2000},
        )
        assert data.name == "Test Preset"
        assert data.filters == {"city": "Berlin", "max_price": 2000}

    def test_create_schema_min_name_length(self):
        """Test name length validation."""
        with pytest.raises(ValueError):
            FilterPresetCreate(name="", filters={})

    def test_create_schema_max_name_length(self):
        """Test name max length validation."""
        long_name = "x" * 256
        with pytest.raises(ValueError):
            FilterPresetCreate(name=long_name, filters={})

    def test_update_schema_partial(self):
        """Test partial updates."""
        data = FilterPresetUpdate(name="New Name")
        assert data.name == "New Name"
        assert data.filters is None

    def test_update_schema_all_optional(self):
        """Test that all update fields are optional."""
        data = FilterPresetUpdate()
        assert data.name is None
        assert data.description is None
        assert data.filters is None
        assert data.is_default is None
