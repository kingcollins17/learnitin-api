"""Migration: Add credit_cost to quizzes table.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Add credit_cost column to quizzes table."""
    async with engine.begin() as conn:
        print("Migrating quizzes table...")

        # Add credit_cost to quizzes
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE quizzes 
                ADD COLUMN credit_cost INT NOT NULL DEFAULT 0
                """
                )
            )
            print("✓ Added credit_cost column to quizzes table")
        except Exception as e:
            print(f"Skipped adding credit_cost to quizzes (already exists?): {e}")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting credit cost column in quizzes...")

        # Drop credit_cost from quizzes
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE quizzes 
                DROP COLUMN credit_cost
                """
                )
            )
            print("✓ Dropped credit_cost from quizzes")
        except Exception as e:
            print(f"Skipped dropping credit_cost from quizzes: {e}")


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
