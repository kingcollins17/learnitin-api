"""Migration: Add quiz_credit_cost to lessons table and remove credit_cost from quizzes table.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Apply the migration."""
    async with engine.begin() as conn:
        print("Migrating lessons and quizzes tables...")

        # 1. Add quiz_credit_cost to lessons table
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                ADD COLUMN quiz_credit_cost INT NOT NULL DEFAULT 0
                """
                )
            )
            print("✓ Added quiz_credit_cost column to lessons table")
        except Exception as e:
            print(f"Skipped adding quiz_credit_cost to lessons (already exists?): {e}")

        # 2. Drop credit_cost from quizzes table
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE quizzes 
                DROP COLUMN credit_cost
                """
                )
            )
            print("✓ Dropped credit_cost column from quizzes table")
        except Exception as e:
            print(f"Skipped dropping credit_cost from quizzes: {e}")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting quiz credit cost changes...")

        # 1. Drop quiz_credit_cost from lessons table
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                DROP COLUMN quiz_credit_cost
                """
                )
            )
            print("✓ Dropped quiz_credit_cost from lessons")
        except Exception as e:
            print(f"Skipped dropping quiz_credit_cost from lessons: {e}")

        # 2. Add credit_cost back to quizzes table
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE quizzes 
                ADD COLUMN credit_cost INT NOT NULL DEFAULT 0
                """
                )
            )
            print("✓ Added credit_cost back to quizzes")
        except Exception as e:
            print(f"Skipped adding credit_cost back to quizzes: {e}")


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
