"""
Migration: Add cma_reports table for Task #85

This migration creates the cma_reports table for storing
Comparative Market Analysis reports including subject property data,
comparable properties with adjustments, and final valuations.

Run with: python -m db.migrations.add_cma_reports_006
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db_context

logger = logging.getLogger(__name__)

MIGRATION_ID = "006_add_cma_reports"
MIGRATION_NAME = "Add cma_reports table"


async def up(session: AsyncSession) -> None:
    """Apply the migration."""
    logger.info(f"Running migration {MIGRATION_ID}: {MIGRATION_NAME}")

    await session.execute(
        text("""
        CREATE TABLE IF NOT EXISTS cma_reports (
            id VARCHAR(36) PRIMARY KEY,

            -- User association
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,

            -- Report status
            status VARCHAR(20) NOT NULL DEFAULT 'draft',

            -- Subject property reference
            subject_property_id VARCHAR(36) NOT NULL,

            -- Snapshot of subject property at report creation time
            subject_data JSONB NOT NULL DEFAULT '{}',

            -- Comparable properties with scores and adjustments
            -- Structure: [{"property_id": str, "similarity_score": float, "adjustments": [...], "adjusted_price": float}]
            comparables JSONB NOT NULL DEFAULT '[]',

            -- Final valuation result
            -- Structure: {"estimated_value": float, "value_range_low": float, "value_range_high": float, "confidence_score": float, "price_per_sqm": float}
            valuation JSONB NOT NULL DEFAULT '{}',

            -- Market context at report time (optional)
            -- Structure: {"avg_price_per_sqm": float, "median_price": float, "trend": str, "inventory_count": int}
            market_context JSONB,

            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE
        )
        """)
    )

    # Create indexes
    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_cma_reports_user_id
        ON cma_reports(user_id)
        """)
    )

    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_cma_reports_status
        ON cma_reports(status)
        """)
    )

    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_cma_reports_expires_at
        ON cma_reports(expires_at)
        """)
    )

    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_cma_reports_user_status
        ON cma_reports(user_id, status)
        """)
    )

    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_cma_reports_user_created
        ON cma_reports(user_id, created_at DESC)
        """)
    )

    # Create GIN index for JSONB queries on comparables
    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_cma_reports_comparables_gin
        ON cma_reports USING GIN (comparables)
        """)
    )

    logger.info(f"Migration {MIGRATION_ID} completed successfully")


async def down(session: AsyncSession) -> None:
    """Rollback the migration."""
    logger.info(f"Rolling back migration {MIGRATION_ID}: {MIGRATION_NAME}")

    await session.execute(text("DROP INDEX IF EXISTS ix_cma_reports_comparables_gin"))
    await session.execute(text("DROP INDEX IF EXISTS ix_cma_reports_user_created"))
    await session.execute(text("DROP INDEX IF EXISTS ix_cma_reports_user_status"))
    await session.execute(text("DROP INDEX IF EXISTS ix_cma_reports_expires_at"))
    await session.execute(text("DROP INDEX IF EXISTS ix_cma_reports_status"))
    await session.execute(text("DROP INDEX IF EXISTS ix_cma_reports_user_id"))
    await session.execute(text("DROP TABLE IF EXISTS cma_reports"))

    logger.info(f"Migration {MIGRATION_ID} rolled back successfully")


async def run_migration() -> None:
    """Run the migration standalone."""
    async with get_db_context() as session:
        await up(session)
        logger.info("Migration completed. Run with down=True to rollback.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migration())
