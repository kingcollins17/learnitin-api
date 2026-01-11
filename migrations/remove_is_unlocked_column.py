"""
Migration: Remove is_unlocked from user_lessons table
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Remove is_unlocked column from user_lessons table."""
    async with engine.begin() as conn:
        print("Migrating user_lessons table...")

        # Drop the is_unlocked column
        await conn.execute(
            text(
                """
            ALTER TABLE user_lessons 
            DROP COLUMN is_unlocked
            """
            )
        )
        print("✓ Dropped is_unlocked column")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        # Add the column back
        await conn.execute(
            text(
                """
            ALTER TABLE user_lessons 
            ADD COLUMN is_unlocked BOOLEAN DEFAULT FALSE
            """
            )
        )
        print("✓ Added is_unlocked column back")


async def main():
    try:
        await upgrade()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        # If it failed likely because column doesn't exist, we can ignore or print warning
        # But for now strict failure
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
