"""
Migration: Add unique constraint to user_courses table

This migration adds a unique constraint on the combination of user_id and course_id
in the user_courses table to prevent duplicate enrollments.

Run this migration with:
    python migrations/add_unique_user_course_constraint.py
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Add unique constraint to user_courses table."""
    async with engine.begin() as conn:
        # Check if constraint already exists
        check_constraint_query = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
            AND TABLE_NAME = 'user_courses'
            AND CONSTRAINT_NAME = 'unique_user_course'
            AND CONSTRAINT_TYPE = 'UNIQUE'
        """
        )

        result = await conn.execute(check_constraint_query)
        row = result.fetchone()

        if row and row[0] > 0:
            print("✓ Unique constraint 'unique_user_course' already exists")
            return

        # Add the unique constraint
        add_constraint_query = text(
            """
            ALTER TABLE user_courses
            ADD CONSTRAINT unique_user_course UNIQUE (user_id, course_id)
        """
        )

        try:
            await conn.execute(add_constraint_query)
            print(
                "✓ Successfully added unique constraint 'unique_user_course' to user_courses table"
            )
        except Exception as e:
            print(f"✗ Error adding constraint: {e}")
            raise


async def downgrade():
    """Remove unique constraint from user_courses table."""
    async with engine.begin() as conn:
        # Check if constraint exists
        check_constraint_query = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
            AND TABLE_NAME = 'user_courses'
            AND CONSTRAINT_NAME = 'unique_user_course'
            AND CONSTRAINT_TYPE = 'UNIQUE'
        """
        )

        result = await conn.execute(check_constraint_query)
        row = result.fetchone()

        if row and row[0] == 0:
            print("✓ Unique constraint 'unique_user_course' does not exist")
            return

        # Remove the unique constraint
        drop_constraint_query = text(
            """
            ALTER TABLE user_courses
            DROP INDEX unique_user_course
        """
        )

        try:
            await conn.execute(drop_constraint_query)
            print(
                "✓ Successfully removed unique constraint 'unique_user_course' from user_courses table"
            )
        except Exception as e:
            print(f"✗ Error removing constraint: {e}")
            raise


async def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage user_courses unique constraint"
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Action to perform: upgrade (add constraint) or downgrade (remove constraint)",
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Migration: Add unique constraint to user_courses")
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
