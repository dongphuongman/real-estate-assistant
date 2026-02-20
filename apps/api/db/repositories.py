"""Repository pattern for database operations."""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    EmailVerificationToken,
    OAuthAccount,
    PasswordResetToken,
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
