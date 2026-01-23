"""Migration to make purchase_token nullable for free plan support.

Free plans are not associated with Google Play and don't have purchase tokens.
"""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Migration SQL - make purchase_token nullable
ALTER_COLUMN_SQL = """
ALTER TABLE subscriptions 
MODIFY COLUMN purchase_token VARCHAR(255) NULL;
"""

# Rollback SQL - make purchase_token NOT NULL (only works if no NULLs exist)
ROLLBACK_SQL = """
ALTER TABLE subscriptions 
MODIFY COLUMN purchase_token VARCHAR(255) NOT NULL;
"""


async def upgrade(database_url: str) -> None:
    """Apply the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Making purchase_token nullable...")
        await conn.execute(text(ALTER_COLUMN_SQL))
        logger.info("Migration completed successfully!")

    await engine.dispose()


async def downgrade(database_url: str) -> None:
    """Rollback the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Making purchase_token NOT NULL...")
        await conn.execute(text(ROLLBACK_SQL))
        logger.info("Rollback completed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    import sys
    from app.common.config import settings

    if len(sys.argv) < 2:
        print("Usage: python make_purchase_token_nullable.py [upgrade|downgrade]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "upgrade":
        asyncio.run(upgrade(settings.DATABASE_URL))
    elif action == "downgrade":
        asyncio.run(downgrade(settings.DATABASE_URL))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
