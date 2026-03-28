"""
Audit Log Service (Task #95).

Provides tamper-evident database-backed audit logging with SHA-256 hash chains.
"""

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import AuditLogRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating and querying audit log entries."""

    def __init__(self, session: AsyncSession):
        self.repo = AuditLogRepository(session)
        self.session = session

    async def log(
        self,
        *,
        action: str,
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_role: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Append an audit log entry to the hash chain.

        Errors are logged but not raised — audit failures must never break
        the request pipeline.
        """
        try:
            await self.repo.append(
                actor_id=actor_id,
                actor_email=actor_email,
                actor_role=actor_role,
                action=action,
                resource=resource,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
            await self.session.commit()
            logger.debug("Audit entry created: action=%s actor=%s", action, actor_id)
        except Exception:
            await self.session.rollback()
            logger.exception("Failed to write audit entry: action=%s", action)

    async def query(
        self,
        *,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        resource: Optional[str] = None,
        request_id: Optional[str] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list, int]:
        """Query audit log entries with filters. Returns (entries, total)."""
        return await self.repo.query(
            action=action,
            actor_id=actor_id,
            resource=resource,
            request_id=request_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    async def verify_chain(self, limit: int = 1000) -> dict[str, Any]:
        """Verify hash-chain integrity of the last N entries."""
        return await self.repo.verify_chain(limit=limit)

    async def get_by_id(self, entry_id: str):
        """Get a single audit log entry by ID."""
        return await self.repo.get_by_id(entry_id)
