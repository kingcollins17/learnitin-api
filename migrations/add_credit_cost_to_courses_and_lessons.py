"""Migration: Add credit_cost to courses and credit_cost/audio_credit_cost to lessons tables.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Add credit-related columns to courses and lessons tables."""
    async with engine.begin() as conn:
        print("Migrating courses and lessons tables...")

        # 1. Add credit_cost to courses
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE courses 
                ADD COLUMN credit_cost INT NOT NULL DEFAULT 0
                """
                )
            )
            print("✓ Added credit_cost column to courses table")
        except Exception as e:
            print(f"Skipped adding credit_cost to courses (already exists?): {e}")

        # 2. Add credit_cost to lessons
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                ADD COLUMN credit_cost INT NOT NULL DEFAULT 0
                """
                )
            )
            print("✓ Added credit_cost column to lessons table")
        except Exception as e:
            print(f"Skipped adding credit_cost to lessons (already exists?): {e}")

        # 3. Add audio_credit_cost to lessons
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                ADD COLUMN audio_credit_cost INT NOT NULL DEFAULT 0
                """
                )
            )
            print("✓ Added audio_credit_cost column to lessons table")
        except Exception as e:
            print(f"Skipped adding audio_credit_cost to lessons (already exists?): {e}")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting credit cost columns...")

        # 1. Drop credit_cost from courses
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE courses 
                DROP COLUMN credit_cost
                """
                )
            )
            print("✓ Dropped credit_cost from courses")
        except Exception as e:
            print(f"Skipped dropping credit_cost from courses: {e}")

        # 2. Drop credit_cost from lessons
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                DROP COLUMN credit_cost
                """
                )
            )
            print("✓ Dropped credit_cost from lessons")
        except Exception as e:
            print(f"Skipped dropping credit_cost from lessons: {e}")

        # 3. Drop audio_credit_cost from lessons
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                DROP COLUMN audio_credit_cost
                """
                )
            )
            print("✓ Dropped audio_credit_cost from lessons")
        except Exception as e:
            print(f"Skipped dropping audio_credit_cost from lessons: {e}")


async def main():
    action = "upgrade"
    if len(sys.argv) > 1:
        action = sys.argv[1]

    try:
        if action == "upgrade":
            await upgrade()
            print("Migration completed successfully!")
        elif action == "downgrade":
            await downgrade()
            print("Downgrade completed successfully!")
        else:
            print(f"Unknown action: {action}")
            sys.exit(1)
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
