"""
Search-related repository classes.

Provides repositories for SavedSearch, Collection, Favorite,
and FilterPreset models.
"""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    CollectionDB,
    FavoriteDB,
    FilterPresetDB,
    SavedSearchDB,
)


class SavedSearchRepository:
    """Repository for SavedSearchDB model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        name: str,
        filters: dict,
        description: Optional[str] = None,
        alert_frequency: str = "daily",
        notify_on_new: bool = True,
        notify_on_price_drop: bool = True,
    ) -> SavedSearchDB:
        """Create a new saved search."""
        from uuid import uuid4

        search = SavedSearchDB(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            filters=filters,
            alert_frequency=alert_frequency,
            notify_on_new=notify_on_new,
            notify_on_price_drop=notify_on_price_drop,
            is_active=True,
        )
        self.session.add(search)
        await self.session.flush()
        return search

    async def get_by_id(self, search_id: str, user_id: str) -> Optional[SavedSearchDB]:
        """Get saved search by ID (scoped to user)."""
        result = await self.session.execute(
            select(SavedSearchDB).where(
                SavedSearchDB.id == search_id, SavedSearchDB.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: str, include_inactive: bool = False
    ) -> list[SavedSearchDB]:
        """Get all saved searches for a user."""
        query = select(SavedSearchDB).where(SavedSearchDB.user_id == user_id)
        if not include_inactive:
            query = query.where(SavedSearchDB.is_active == True)  # noqa: E712
        query = query.order_by(SavedSearchDB.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_all_active(self) -> list[SavedSearchDB]:
        """Get all active saved searches (for scheduler)."""
        result = await self.session.execute(
            select(SavedSearchDB).where(
                SavedSearchDB.is_active == True  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_by_frequency(self, frequency: str) -> list[SavedSearchDB]:
        """Get searches by alert frequency (for scheduler)."""
        result = await self.session.execute(
            select(SavedSearchDB).where(
                SavedSearchDB.is_active == True,  # noqa: E712
                SavedSearchDB.alert_frequency == frequency,
            )
        )
        return list(result.scalars().all())

    async def update(self, search: SavedSearchDB, **kwargs) -> SavedSearchDB:
        """Update saved search fields."""
        for key, value in kwargs.items():
            if hasattr(search, key):
                setattr(search, key, value)
        await self.session.flush()
        return search

    async def delete(self, search: SavedSearchDB) -> None:
        """Delete a saved search."""
        await self.session.delete(search)

    async def increment_usage(self, search: SavedSearchDB) -> None:
        """Increment usage count and update last_used_at."""
        search.use_count += 1
        search.last_used_at = datetime.now(UTC)
        await self.session.flush()


class CollectionRepository:
    """Repository for CollectionDB model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        is_default: bool = False,
    ) -> CollectionDB:
        """Create a new collection."""
        from uuid import uuid4

        collection = CollectionDB(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            is_default=is_default,
        )
        self.session.add(collection)
        await self.session.flush()
        return collection

    async def get_by_id(self, collection_id: str, user_id: str) -> Optional[CollectionDB]:
        """Get collection by ID (scoped to user)."""
        result = await self.session.execute(
            select(CollectionDB).where(
                CollectionDB.id == collection_id,
                CollectionDB.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> list[CollectionDB]:
        """Get all collections for a user, ordered by name."""
        result = await self.session.execute(
            select(CollectionDB)
            .where(CollectionDB.user_id == user_id)
            .order_by(CollectionDB.is_default.desc(), CollectionDB.name)
        )
        return list(result.scalars().all())

    async def get_default_collection(self, user_id: str) -> Optional[CollectionDB]:
        """Get user's default collection."""
        result = await self.session.execute(
            select(CollectionDB).where(
                CollectionDB.user_id == user_id,
                CollectionDB.is_default.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_default(self, user_id: str) -> CollectionDB:
        """Get or create default collection for user."""
        collection = await self.get_default_collection(user_id)
        if collection:
            return collection
        return await self.create(
            user_id=user_id,
            name="My Favorites",
            is_default=True,
        )

    async def update(self, collection: CollectionDB, **kwargs) -> CollectionDB:
        """Update collection fields."""
        for key, value in kwargs.items():
            if hasattr(collection, key):
                setattr(collection, key, value)
        await self.session.flush()
        return collection

    async def delete(self, collection: CollectionDB) -> None:
        """Delete a collection (favorites will become uncategorized)."""
        await self.session.delete(collection)

    async def count_favorites(self, collection_id: str) -> int:
        """Count favorites in a collection."""
        result = await self.session.execute(
            select(func.count(FavoriteDB.id)).where(FavoriteDB.collection_id == collection_id)
        )
        return result.scalar() or 0


class FavoriteRepository:
    """Repository for FavoriteDB model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        property_id: str,
        collection_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> FavoriteDB:
        """Create a new favorite."""
        from uuid import uuid4

        favorite = FavoriteDB(
            id=str(uuid4()),
            user_id=user_id,
            property_id=property_id,
            collection_id=collection_id,
            notes=notes,
        )
        self.session.add(favorite)
        await self.session.flush()
        return favorite

    async def get_by_id(self, favorite_id: str, user_id: str) -> Optional[FavoriteDB]:
        """Get favorite by ID (scoped to user)."""
        result = await self.session.execute(
            select(FavoriteDB).where(FavoriteDB.id == favorite_id, FavoriteDB.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_property(self, user_id: str, property_id: str) -> Optional[FavoriteDB]:
        """Get favorite by property ID (scoped to user)."""
        result = await self.session.execute(
            select(FavoriteDB).where(
                FavoriteDB.user_id == user_id,
                FavoriteDB.property_id == property_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: str,
        collection_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FavoriteDB]:
        """Get all favorites for a user, optionally filtered by collection."""
        query = select(FavoriteDB).where(FavoriteDB.user_id == user_id)

        if collection_id is not None:
            query = query.where(FavoriteDB.collection_id == collection_id)

        query = query.order_by(FavoriteDB.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str, collection_id: Optional[str] = None) -> int:
        """Count favorites for a user."""
        query = select(func.count(FavoriteDB.id)).where(FavoriteDB.user_id == user_id)
        if collection_id is not None:
            query = query.where(FavoriteDB.collection_id == collection_id)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_property_ids_by_user(self, user_id: str) -> list[str]:
        """Get all property IDs favorited by a user (for efficient lookup)."""
        result = await self.session.execute(
            select(FavoriteDB.property_id).where(FavoriteDB.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def update(self, favorite: FavoriteDB, **kwargs) -> FavoriteDB:
        """Update favorite fields."""
        for key, value in kwargs.items():
            if hasattr(favorite, key):
                setattr(favorite, key, value)
        await self.session.flush()
        return favorite

    async def delete(self, favorite: FavoriteDB) -> None:
        """Delete a favorite."""
        await self.session.delete(favorite)

    async def delete_by_property(self, user_id: str, property_id: str) -> bool:
        """Delete favorite by property ID. Returns True if deleted."""
        favorite = await self.get_by_property(user_id, property_id)
        if favorite:
            await self.delete(favorite)
            return True
        return False

    async def move_to_collection(
        self, user_id: str, property_id: str, collection_id: Optional[str]
    ) -> Optional[FavoriteDB]:
        """Move a favorite to a different collection."""
        favorite = await self.get_by_property(user_id, property_id)
        if favorite:
            favorite.collection_id = collection_id
            await self.session.flush()
        return favorite


class FilterPresetRepository:
    """Repository for FilterPresetDB model operations (Task #75)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        name: str,
        filters: dict,
        description: Optional[str] = None,
        is_default: bool = False,
    ) -> FilterPresetDB:
        """Create a new filter preset."""
        from uuid import uuid4

        preset = FilterPresetDB(
            id=str(uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            filters=filters,
            is_default=is_default,
        )
        self.session.add(preset)
        await self.session.flush()
        return preset

    async def get_by_id(self, preset_id: str, user_id: str) -> Optional[FilterPresetDB]:
        """Get filter preset by ID (scoped to user)."""
        result = await self.session.execute(
            select(FilterPresetDB).where(
                FilterPresetDB.id == preset_id,
                FilterPresetDB.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[FilterPresetDB]:
        """Get all filter presets for a user."""
        query = (
            select(FilterPresetDB)
            .where(FilterPresetDB.user_id == user_id)
            .order_by(
                FilterPresetDB.is_default.desc(),
                FilterPresetDB.use_count.desc(),
                FilterPresetDB.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: str) -> int:
        """Count filter presets for a user."""
        result = await self.session.execute(
            select(func.count(FilterPresetDB.id)).where(FilterPresetDB.user_id == user_id)
        )
        return result.scalar() or 0

    async def get_default(self, user_id: str) -> Optional[FilterPresetDB]:
        """Get user's default filter preset."""
        result = await self.session.execute(
            select(FilterPresetDB).where(
                FilterPresetDB.user_id == user_id,
                FilterPresetDB.is_default == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def set_default(self, preset: FilterPresetDB, user_id: str) -> FilterPresetDB:
        """Set a preset as default (unsets other defaults first)."""
        # Unset all other defaults for this user
        await self.session.execute(
            update(FilterPresetDB)
            .where(
                FilterPresetDB.user_id == user_id,
                FilterPresetDB.id != preset.id,
            )
            .values(is_default=False)
        )
        # Set this preset as default
        preset.is_default = True
        await self.session.flush()
        return preset

    async def increment_usage(self, preset: FilterPresetDB) -> FilterPresetDB:
        """Increment usage count and update last_used_at."""
        preset.use_count += 1
        preset.last_used_at = datetime.now(UTC)
        await self.session.flush()
        return preset

    async def update(self, preset: FilterPresetDB, **kwargs) -> FilterPresetDB:
        """Update filter preset fields."""
        for key, value in kwargs.items():
            if hasattr(preset, key):
                setattr(preset, key, value)
        await self.session.flush()
        return preset

    async def delete(self, preset: FilterPresetDB) -> None:
        """Delete a filter preset."""
        await self.session.delete(preset)
        await self.session.flush()
