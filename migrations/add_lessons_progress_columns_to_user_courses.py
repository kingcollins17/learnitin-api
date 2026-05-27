"""
Migration: Add total_lessons and completed_lessons columns to user_courses table

Run this migration with:
    python migrations/add_lessons_progress_columns_to_user_courses.py upgrade
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def check_column_exists(column_name: str) -> bool:
    """Check if a column already exists in the user_courses table."""
    async with engine.begin() as conn:
        query = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'user_courses'
            AND COLUMN_NAME = :col_name
        """
        )
        result = await conn.execute(query, {"col_name": column_name})
        row = result.fetchone()
        return row and row[0] > 0


async def upgrade():
    """Add total_lessons and completed_lessons columns to user_courses."""
    async with engine.begin() as conn:
        # Check and add total_lessons
        if await check_column_exists("total_lessons"):
            print("SUCCESS: Column 'total_lessons' already exists in user_courses")
        else:
            print("Adding 'total_lessons' column...")
            await conn.execute(
                text("ALTER TABLE user_courses ADD COLUMN total_lessons INT NOT NULL DEFAULT 0")
            )
            print("SUCCESS: Successfully added 'total_lessons' column")

        # Check and add completed_lessons
        if await check_column_exists("completed_lessons"):
            print("SUCCESS: Column 'completed_lessons' already exists in user_courses")
        else:
            print("Adding 'completed_lessons' column...")
            await conn.execute(
                text("ALTER TABLE user_courses ADD COLUMN completed_lessons INT NOT NULL DEFAULT 0")
            )
            print("SUCCESS: Successfully added 'completed_lessons' column")


async def downgrade():
    """Remove total_lessons and completed_lessons columns from user_courses."""
    async with engine.begin() as conn:
        # Check and remove completed_lessons
        if not await check_column_exists("completed_lessons"):
            print("SUCCESS: Column 'completed_lessons' does not exist in user_courses")
        else:
            print("Removing 'completed_lessons' column...")
            await conn.execute(
                text("ALTER TABLE user_courses DROP COLUMN completed_lessons")
            )
            print("SUCCESS: Successfully removed 'completed_lessons' column")

        # Check and remove total_lessons
        if not await check_column_exists("total_lessons"):
            print("SUCCESS: Column 'total_lessons' does not exist in user_courses")
        else:
            print("Removing 'total_lessons' column...")
            await conn.execute(
                text("ALTER TABLE user_courses DROP COLUMN total_lessons")
            )
            print("SUCCESS: Successfully removed 'total_lessons' column")


async def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add lessons progress columns to user_courses table"
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Action to perform: upgrade or downgrade",
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Migration: Add lessons progress columns to user_courses")
    print(f"Action: {args.action}")
    print(f"{'='*60}\n")

    try:
        if args.action == "upgrade":
            await upgrade()
        else:
            await downgrade()

        print(f"\n{'='*60}")
        print("Migration completed successfully!")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"Migration failed: {e}")
        print(f"{'='*60}\n")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
