"""
Migration: Add task_model_preferences table for Task #87

This migration creates the task_model_preferences table for storing
per-task model preferences including provider, model name, and fallback chains.

Run with: python -m db.migrations.add_task_model_preferences_005
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db_context

logger = logging.getLogger(__name__)

MIGRATION_ID = "005_add_task_model_preferences"
MIGRATION_NAME = "Add task_model_preferences table"


async def up(session: AsyncSession) -> None:
    """Apply the migration."""
    logger.info(f"Running migration {MIGRATION_ID}: {MIGRATION_NAME}")

    await session.execute(
        text("""
        CREATE TABLE IF NOT EXISTS task_model_preferences (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            task_type VARCHAR(50) NOT NULL,
            provider VARCHAR(50) NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            fallback_chain JSONB,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_user_task_type UNIQUE (user_id, task_type)
        )
        """)
    )

    # Create indexes
    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_task_model_preferences_user_id
        ON task_model_preferences(user_id)
        """)
    )

    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_task_model_preferences_task_type
        ON task_model_preferences(task_type)
        """)
    )

    logger.info(f"Migration {MIGRATION_ID} completed successfully")


async def down(session: AsyncSession) -> None:
    """Rollback the migration."""
    logger.info(f"Rolling back migration {MIGRATION_ID}: {MIGRATION_NAME}")

    await session.execute(text("DROP INDEX IF EXISTS ix_task_model_preferences_task_type"))
    await session.execute(text("DROP INDEX IF EXISTS ix_task_model_preferences_user_id"))
    await session.execute(text("DROP TABLE IF EXISTS task_model_preferences"))

    logger.info(f"Migration {MIGRATION_ID} rolled back successfully")


async def run_migration() -> None:
    """Run the migration standalone."""
    async with get_db_context() as session:
        await up(session)
        logger.info("Migration completed. Run with down=True to rollback.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migration())
