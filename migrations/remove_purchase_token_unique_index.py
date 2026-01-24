"""Migration to remove unique constraint on purchase_token.

This allows multiple subscription records with the same purchase_token,
which is needed for maintaining subscription history when renewals occur.
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Migration SQL - drop the unique index and create a regular index
DROP_UNIQUE_INDEX_SQL = """
DROP INDEX ix_subscriptions_purchase_token ON subscriptions;
"""

CREATE_REGULAR_INDEX_SQL = """
CREATE INDEX ix_subscriptions_purchase_token ON subscriptions(purchase_token);
"""

# Rollback SQL - drop regular index and recreate unique index
ROLLBACK_DROP_INDEX_SQL = """
DROP INDEX ix_subscriptions_purchase_token ON subscriptions;
"""

ROLLBACK_CREATE_UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX ix_subscriptions_purchase_token ON subscriptions(purchase_token);
"""


async def upgrade(database_url: str) -> None:
    """Apply the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Dropping unique index on purchase_token...")
        await conn.execute(text(DROP_UNIQUE_INDEX_SQL))

        logger.info("Creating regular index on purchase_token...")
        await conn.execute(text(CREATE_REGULAR_INDEX_SQL))

        logger.info("Migration completed successfully!")

    await engine.dispose()


async def downgrade(database_url: str) -> None:
    """Rollback the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Dropping regular index on purchase_token...")
        await conn.execute(text(ROLLBACK_DROP_INDEX_SQL))

        logger.info("Creating unique index on purchase_token...")
        await conn.execute(text(ROLLBACK_CREATE_UNIQUE_INDEX_SQL))

        logger.info("Rollback completed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    import sys
    from app.common.config import settings

    if len(sys.argv) < 2:
        print("Usage: python remove_purchase_token_unique_index.py [upgrade|downgrade]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "upgrade":
        asyncio.run(upgrade(settings.DATABASE_URL))
    elif action == "downgrade":
        asyncio.run(downgrade(settings.DATABASE_URL))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
