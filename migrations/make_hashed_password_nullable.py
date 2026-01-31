"""Migration to make hashed_password nullable in users table."""

import asyncio
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Migration SQL - make hashed_password nullable
ALTER_COLUMN_SQL = """
ALTER TABLE users 
MODIFY COLUMN hashed_password VARCHAR(255) NULL;
"""

# Rollback SQL - make hashed_password NOT NULL
ROLLBACK_SQL = """
ALTER TABLE users 
MODIFY COLUMN hashed_password VARCHAR(255) NOT NULL;
"""


async def upgrade(database_url: str) -> None:
    """Apply the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Making hashed_password nullable...")
        await conn.execute(text(ALTER_COLUMN_SQL))
        logger.info("Migration completed successfully!")

    await engine.dispose()


async def downgrade(database_url: str) -> None:
    """Rollback the migration."""
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        logger.info("Making hashed_password NOT NULL...")
        await conn.execute(text(ROLLBACK_SQL))
        logger.info("Rollback completed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    import sys
    import os

    # Add the current directory to sys.path to allow importing from app
    sys.path.append(os.getcwd())
    from app.common.config import settings

    if len(sys.argv) < 2:
        print(
            "Usage: python migrations/make_hashed_password_nullable.py [upgrade|downgrade]"
        )
        sys.exit(1)

    action = sys.argv[1]

    if action == "upgrade":
        asyncio.run(upgrade(settings.DATABASE_URL))
    elif action == "downgrade":
        asyncio.run(downgrade(settings.DATABASE_URL))
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
