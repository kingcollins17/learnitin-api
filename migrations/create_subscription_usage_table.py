"""Migration to create subscription_usages table.

This creates the SubscriptionUsage table with a unique FK constraint
to enforce one-to-one relationship with Subscription.
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Migration SQL
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS subscription_usages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    subscription_id INT NOT NULL UNIQUE,
    year INT NOT NULL,
    month INT NOT NULL,
    learning_journeys_used INT NOT NULL DEFAULT 0,
    lessons_used INT NOT NULL DEFAULT 0,
    audio_lessons_used INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_subscription_usage_subscription
        FOREIGN KEY (subscription_id) 
        REFERENCES subscriptions(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_subscription_usage_subscription_id ON subscription_usages(subscription_id);",
    "CREATE INDEX IF NOT EXISTS idx_subscription_usage_year_month ON subscription_usages(year, month);",
]

# Rollback SQL
DROP_TABLE_SQL = "DROP TABLE IF EXISTS subscription_usages;"


async def upgrade(database_url: str) -> None:
    """Apply the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Creating subscription_usages table...")
        await conn.execute(text(CREATE_TABLE_SQL))

        for index_sql in CREATE_INDEXES_SQL:
            try:
                await conn.execute(text(index_sql))
            except Exception as e:
                # Index might already exist
                logger.warning(f"Index creation note: {e}")

        logger.info("Migration completed successfully!")

    await engine.dispose()


async def downgrade(database_url: str) -> None:
    """Rollback the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Dropping subscription_usages table...")
        await conn.execute(text(DROP_TABLE_SQL))
        logger.info("Rollback completed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    import sys
    from app.common.config import settings

    if len(sys.argv) < 2:
        print("Usage: python create_subscription_usage_table.py [upgrade|downgrade]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "upgrade":
        asyncio.run(upgrade(settings.DATABASE_URL))
    elif action == "downgrade":
        asyncio.run(downgrade(settings.DATABASE_URL))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
