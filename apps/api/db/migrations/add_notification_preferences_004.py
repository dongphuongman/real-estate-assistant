"""
Migration: Add notification_preferences table for Task #86

This migration creates the notification_preferences table for storing
granular user notification preferences including type toggles, frequency,
channel selection, and unsubscribe management.

Run with: python -m db.migrations.add_notification_preferences_004
"""

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db_context

logger = logging.getLogger(__name__)

MIGRATION_ID = "004_add_notification_preferences"
MIGRATION_NAME = "Add notification_preferences table"


async def up(session: AsyncSession) -> None:
    """Apply the migration."""
    logger.info(f"Running migration {MIGRATION_ID}: {MIGRATION_NAME}")

    await session.execute(
        text("""
        CREATE TABLE IF NOT EXISTS notification_preferences (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,

            -- Notification type toggles
            price_alerts_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            new_listings_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            saved_search_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            market_updates_enabled BOOLEAN NOT NULL DEFAULT FALSE,

            -- Frequency settings
            alert_frequency VARCHAR(20) NOT NULL DEFAULT 'daily',

            -- Channel selection
            email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            push_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            in_app_enabled BOOLEAN NOT NULL DEFAULT TRUE,

            -- Advanced settings
            quiet_hours_start VARCHAR(5),
            quiet_hours_end VARCHAR(5),
            price_drop_threshold FLOAT NOT NULL DEFAULT 5.0,

            -- Digest settings
            daily_digest_time VARCHAR(5) NOT NULL DEFAULT '09:00',
            weekly_digest_day VARCHAR(10) NOT NULL DEFAULT 'monday',

            -- Expert/Marketing preferences
            expert_mode BOOLEAN NOT NULL DEFAULT FALSE,
            marketing_emails BOOLEAN NOT NULL DEFAULT FALSE,

            -- Unsubscribe management
            unsubscribe_token VARCHAR(64) NOT NULL UNIQUE,
            unsubscribed_at TIMESTAMP WITH TIME ZONE,
            unsubscribed_types JSONB,

            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """)
    )

    # Create indexes
    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_notification_preferences_user_id
        ON notification_preferences(user_id)
        """)
    )

    await session.execute(
        text("""
        CREATE INDEX IF NOT EXISTS ix_notification_prefs_unsubscribe_token
        ON notification_preferences(unsubscribe_token)
        """)
    )

    logger.info(f"Migration {MIGRATION_ID} completed successfully")


async def down(session: AsyncSession) -> None:
    """Rollback the migration."""
    logger.info(f"Rolling back migration {MIGRATION_ID}: {MIGRATION_NAME}")

    await session.execute(text("DROP INDEX IF EXISTS ix_notification_prefs_unsubscribe_token"))
    await session.execute(text("DROP INDEX IF EXISTS ix_notification_preferences_user_id"))
    await session.execute(text("DROP TABLE IF EXISTS notification_preferences"))

    logger.info(f"Migration {MIGRATION_ID} rolled back successfully")


async def run_migration() -> None:
    """Run the migration standalone."""
    async with get_db_context() as session:
        await up(session)
        logger.info("Migration completed. Run with down=True to rollback.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migration())
