"""
Migration: Make script and audio_url columns nullable in lesson_audios table
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Make script and audio_url columns nullable."""
    async with engine.begin() as conn:
        print("Modifying lesson_audios table...")

        # 1. Modify script column to be nullable
        await conn.execute(
            text(
                """
            ALTER TABLE lesson_audios 
            MODIFY COLUMN script LONGTEXT NULL
            """
            )
        )
        print("✓ Modified script to be nullable")

        # 2. Modify audio_url column to be nullable
        await conn.execute(
            text(
                """
            ALTER TABLE lesson_audios 
            MODIFY COLUMN audio_url TEXT NULL
            """
            )
        )
        print("✓ Modified audio_url to be nullable")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting changes...")

        # 1. Revert script column to be NOT NULL
        # Note: This might fail if there are NULL values
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lesson_audios 
                MODIFY COLUMN script LONGTEXT NOT NULL
                """
                )
            )
            print("✓ Reverted script to be NOT NULL")
        except Exception as e:
            print(f"Warning: Could not revert script column: {e}")

        # 2. Revert audio_url column to be NOT NULL
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lesson_audios 
                MODIFY COLUMN audio_url TEXT NOT NULL
                """
                )
            )
            print("✓ Reverted audio_url to be NOT NULL")
        except Exception as e:
            print(f"Warning: Could not revert audio_url column: {e}")


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
