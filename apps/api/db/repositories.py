"""Repository pattern for database operations."""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    CollectionDB,
    EmailVerificationToken,
    FavoriteDB,
    OAuthAccount,
    PasswordResetToken,
    PriceSnapshot,
    RefreshToken,
    SavedSearchDB,
    User,
)


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        email: str,
        hashed_password: Optional[str] = None,
        full_name: Optional[str] = None,
        role: str = "user",
        is_verified: bool = False,
    ) -> User:
        """Create a new user."""
        user = User(
            id=str(uuid4()),
            email=email.lower().strip(),
            hashed_password=hashed_password,
            full_name=full_name,
            role=role,
            is_verified=is_verified,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.session.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()

    async def update(self, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await self.session.flush()
        return user

    async def update_last_login(self, user: User) -> None:
        """Update user's last login timestamp."""
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()

    async def set_verified(self, user: User) -> None:
        """Mark user as verified."""
        user.is_verified = True
        await self.session.flush()

    async def set_password(self, user: User, hashed_password: str) -> None:
        """Set user's password."""
        user.hashed_password = hashed_password
        await self.session.flush()

    async def delete(self, user: User) -> None:
        """Delete a user."""
        await self.session.delete(user)

    async def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email."""
        result = await self.session.execute(
            select(User.id).where(User.email == email.lower().strip())
        )
        return result.scalar_one_or_none() is not None


class RefreshTokenRepository:
    """Repository for RefreshToken model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(
        self,
        user_id: str,
        token: str,
        expires_days: int = 7,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> RefreshToken:
        """Create a new refresh token."""
        token_hash = self._hash_token(token)
        refresh_token = RefreshToken(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=expires_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def get_by_token(self, token: str) -> Optional[RefreshToken]:
        """Get refresh token by token value."""
        token_hash = self._hash_token(token)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshToken) -> None:
        """Revoke a refresh token."""
        token.revoked_at = datetime.now(UTC)
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    async def cleanup_expired(self, user_id: Optional[str] = None) -> int:
        """Remove expired tokens."""
        query = select(RefreshToken).where(RefreshToken.expires_at < datetime.now(UTC))
        if user_id:
            query = query.where(RefreshToken.user_id == user_id)

        result = await self.session.execute(query)
        expired_tokens = result.scalars().all()

        count = 0
        for token in expired_tokens:
            await self.session.delete(token)
            count += 1

        return count


class OAuthAccountRepository:
    """Repository for OAuthAccount model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: str,
        provider: str,
        provider_user_id: str,
        provider_email: Optional[str] = None,
    ) -> OAuthAccount:
        """Create a new OAuth account link."""
        oauth_account = OAuthAccount(
            id=str(uuid4()),
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
        )
        self.session.add(oauth_account)
        await self.session.flush()
        return oauth_account

    async def get_by_provider(self, provider: str, provider_user_id: str) -> Optional[OAuthAccount]:
        """Get OAuth account by provider and provider user ID."""
        result = await self.session.execute(
            select(OAuthAccount).where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: str) -> list[OAuthAccount]:
        """Get all OAuth accounts for a user."""
        result = await self.session.execute(
            select(OAuthAccount).where(OAuthAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def delete(self, oauth_account: OAuthAccount) -> None:
        """Delete an OAuth account link."""
        await self.session.delete(oauth_account)


class PasswordResetTokenRepository:
    """Repository for PasswordResetToken model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, user_id: str, token: str, expires_hours: int = 1) -> PasswordResetToken:
        """Create a new password reset token."""
        token_hash = self._hash_token(token)
        reset_token = PasswordResetToken(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
        )
        self.session.add(reset_token)
        await self.session.flush()
        return reset_token

    async def get_by_token(self, token: str) -> Optional[PasswordResetToken]:
        """Get password reset token by token value."""
        token_hash = self._hash_token(token)
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: PasswordResetToken) -> None:
        """Mark token as used."""
        token.used_at = datetime.now(UTC)
        await self.session.flush()

    async def cleanup_expired(self) -> int:
        """Remove expired tokens."""
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.expires_at < datetime.now(UTC))
        )
        expired_tokens = result.scalars().all()

        count = 0
        for token in expired_tokens:
            await self.session.delete(token)
            count += 1

        return count


class EmailVerificationTokenRepository:
    """Repository for EmailVerificationToken model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(
        self, user_id: str, token: str, expires_hours: int = 24
    ) -> EmailVerificationToken:
        """Create a new email verification token."""
        token_hash = self._hash_token(token)
        verification_token = EmailVerificationToken(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_hours),
        )
        self.session.add(verification_token)
        await self.session.flush()
        return verification_token

    async def get_by_token(self, token: str) -> Optional[EmailVerificationToken]:
        """Get email verification token by token value."""
        token_hash = self._hash_token(token)
        result = await self.session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, token: EmailVerificationToken) -> None:
        """Mark token as used."""
        token.used_at = datetime.now(UTC)
        await self.session.flush()

    async def invalidate_for_user(self, user_id: str) -> None:
        """Invalidate all unused tokens for a user."""
        await self.session.execute(
            update(EmailVerificationToken)
            .where(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )

    async def cleanup_expired(self) -> int:
        """Remove expired tokens."""
        result = await self.session.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.expires_at < datetime.now(UTC)
            )
        )
        expired_tokens = result.scalars().all()

        count = 0
        for token in expired_tokens:
            await self.session.delete(token)
            count += 1

        return count


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
            select(SavedSearchDB).where(SavedSearchDB.is_active == True)  # noqa: E712
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
                CollectionDB.id == collection_id, CollectionDB.user_id == user_id
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
                CollectionDB.is_default == True,  # noqa: E712
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
                FavoriteDB.user_id == user_id, FavoriteDB.property_id == property_id
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


class PriceSnapshotRepository:
    """Repository for PriceSnapshot model operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        property_id: str,
        price: float,
        price_per_sqm: Optional[float] = None,
        currency: Optional[str] = None,
        source: Optional[str] = None,
    ) -> PriceSnapshot:
        """Create a new price snapshot."""
        snapshot = PriceSnapshot(
            id=str(uuid4()),
            property_id=property_id,
            price=price,
            price_per_sqm=price_per_sqm,
            currency=currency,
            source=source,
        )
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_by_property(
        self,
        property_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PriceSnapshot]:
        """Get price history for a property."""
        result = await self.session.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.property_id == property_id)
            .order_by(PriceSnapshot.recorded_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_for_property(self, property_id: str) -> Optional[PriceSnapshot]:
        """Get the most recent price snapshot for a property."""
        result = await self.session.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.property_id == property_id)
            .order_by(PriceSnapshot.recorded_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_for_property(self, property_id: str) -> int:
        """Count snapshots for a property."""
        result = await self.session.execute(
            select(func.count(PriceSnapshot.id)).where(PriceSnapshot.property_id == property_id)
        )
        return result.scalar() or 0

    async def get_snapshots_in_period(
        self,
        start_date: datetime,
        end_date: datetime,
        property_ids: Optional[list[str]] = None,
    ) -> list[PriceSnapshot]:
        """Get all snapshots in a time period, optionally filtered by property IDs."""
        query = select(PriceSnapshot).where(
            PriceSnapshot.recorded_at >= start_date,
            PriceSnapshot.recorded_at <= end_date,
        )
        if property_ids:
            query = query.where(PriceSnapshot.property_id.in_(property_ids))
        query = query.order_by(PriceSnapshot.recorded_at.asc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_properties_with_price_drops(
        self,
        threshold_percent: float = 5.0,
        days_back: int = 7,
    ) -> list[dict[str, Any]]:
        """Find properties with price drops exceeding threshold in the past N days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_back)

        # Get recent snapshots ordered by property and date
        result = await self.session.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.recorded_at >= cutoff_date)
            .order_by(PriceSnapshot.property_id, PriceSnapshot.recorded_at.desc())
        )
        snapshots = result.scalars().all()

        # Group by property and detect drops
        property_prices: dict[str, list[PriceSnapshot]] = {}
        for snap in snapshots:
            if snap.property_id not in property_prices:
                property_prices[snap.property_id] = []
            property_prices[snap.property_id].append(snap)

        drops = []
        for prop_id, snaps in property_prices.items():
            if len(snaps) >= 2:
                # Compare most recent to oldest in the period
                latest = snaps[0]  # Most recent (first due to desc order)
                oldest = snaps[-1]  # Oldest (last in the list)
                if oldest.price > 0:
                    change_pct = ((oldest.price - latest.price) / oldest.price) * 100
                    if change_pct >= threshold_percent:
                        drops.append(
                            {
                                "property_id": prop_id,
                                "old_price": oldest.price,
                                "new_price": latest.price,
                                "percent_drop": change_pct,
                                "recorded_at": latest.recorded_at,
                            }
                        )

        return drops

    async def cleanup_old_snapshots(self, days_to_keep: int = 365) -> int:
        """Remove snapshots older than specified days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)
        result = await self.session.execute(
            select(PriceSnapshot).where(PriceSnapshot.recorded_at < cutoff_date)
        )
        old_snapshots = result.scalars().all()

        count = 0
        for snapshot in old_snapshots:
            await self.session.delete(snapshot)
            count += 1

        return count
