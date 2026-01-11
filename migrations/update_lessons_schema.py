"""
Migration: Update lessons table with correct text column types
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Update lessons table column types."""
    async with engine.begin() as conn:
        print("Modifying lessons table...")

        # We need to execute ALTER TABLE statements to change column types
        # Note: MySQL syntax

        # 1. Change audio_transcript_url to TEXT
        await conn.execute(
            text(
                """
            ALTER TABLE lessons 
            MODIFY COLUMN audio_transcript_url TEXT
            """
            )
        )
        print("✓ Modified audio_transcript_url to TEXT")

        # 2. Change content to LONGTEXT
        await conn.execute(
            text(
                """
            ALTER TABLE lessons 
            MODIFY COLUMN content LONGTEXT
            """
            )
        )
        print("✓ Modified content to LONGTEXT")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        # Revert back to reasonable defaults if needed
        # Assuming they were roughly VARCHAR or TEXT before
        # This is a best-effort revert

        await conn.execute(
            text(
                """
            ALTER TABLE lessons 
            MODIFY COLUMN audio_transcript_url VARCHAR(255)
            """
            )
        )

        await conn.execute(
            text(
                """
            ALTER TABLE lessons 
            MODIFY COLUMN content TEXT
            """
            )
        )
        print("✓ Reverted column types")


async def main():
    try:
        await upgrade()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
