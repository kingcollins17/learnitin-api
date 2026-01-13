"""
Migration: Remove credits feature from users and lessons tables
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Remove credit-related columns from users and lessons tables."""
    async with engine.begin() as conn:
        print("Migrating users and lessons tables...")

        # 1. Remove credits from users
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE users 
                DROP COLUMN credits
                """
                )
            )
            print("✓ Dropped credits column from users table")
        except Exception as e:
            print(f"Skipped dropping credits from users: {e}")

        # 2. Remove credit_cost from lessons
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                DROP COLUMN credit_cost
                """
                )
            )
            print("✓ Dropped credit_cost column from lessons table")
        except Exception as e:
            print(f"Skipped dropping credit_cost from lessons: {e}")

        # 3. Remove audio_credit_cost from lessons
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                DROP COLUMN audio_credit_cost
                """
                )
            )
            print("✓ Dropped audio_credit_cost column from lessons table")
        except Exception as e:
            print(f"Skipped dropping audio_credit_cost from lessons: {e}")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting credits feature columns...")

        # 1. Add credits back to users
        await conn.execute(
            text(
                """
            ALTER TABLE users 
            ADD COLUMN credits INT DEFAULT 0
            """
            )
        )

        # 2. Add credit_cost back to lessons
        await conn.execute(
            text(
                """
            ALTER TABLE lessons 
            ADD COLUMN credit_cost INT DEFAULT 0
            """
            )
        )

        # 3. Add audio_credit_cost back to lessons
        await conn.execute(
            text(
                """
            ALTER TABLE lessons 
            ADD COLUMN audio_credit_cost INT DEFAULT 0
            """
            )
        )
        print("✓ Reverted all columns")


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
