"""Migration: Remove credit_cost from courses table.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Drop credit_cost column from courses table."""
    async with engine.begin() as conn:
        print("Migrating courses table...")

        # Drop credit_cost from courses
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE courses 
                DROP COLUMN credit_cost
                """
                )
            )
            print("✓ Dropped credit_cost column from courses table")
        except Exception as e:
            print(f"Skipped dropping credit_cost from courses (already dropped?): {e}")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting credit_cost column in courses...")

        # Add credit_cost back to courses
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE courses 
                ADD COLUMN credit_cost INT NOT NULL DEFAULT 0
                """
                )
            )
            print("✓ Added credit_cost back to courses")
        except Exception as e:
            print(f"Skipped adding credit_cost back to courses: {e}")


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
