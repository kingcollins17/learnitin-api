"""
Migration: Add unique constraints to user_modules and user_lessons tables

This migration adds unique constraints to prevent duplicate records:
- user_modules: unique constraint on (user_id, module_id)
- user_lessons: unique constraint on (user_id, lesson_id)

Run this migration with:
    python migrations/add_unique_user_module_lesson_constraints.py upgrade
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Add unique constraints to user_modules and user_lessons tables."""
    async with engine.begin() as conn:
        # Add constraint to user_modules
        print("\n--- Processing user_modules table ---")

        # Check if constraint already exists
        check_module_constraint = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
            AND TABLE_NAME = 'user_modules'
            AND CONSTRAINT_NAME = 'unique_user_module'
            AND CONSTRAINT_TYPE = 'UNIQUE'
        """
        )

        result = await conn.execute(check_module_constraint)
        row = result.fetchone()

        if row and row[0] > 0:
            print("✓ Unique constraint 'unique_user_module' already exists")
        else:
            # Add the unique constraint
            add_module_constraint = text(
                """
                ALTER TABLE user_modules
                ADD CONSTRAINT unique_user_module UNIQUE (user_id, module_id)
            """
            )

            try:
                await conn.execute(add_module_constraint)
                print(
                    "✓ Successfully added unique constraint 'unique_user_module' to user_modules table"
                )
            except Exception as e:
                print(f"✗ Error adding constraint to user_modules: {e}")
                raise

        # Add constraint to user_lessons
        print("\n--- Processing user_lessons table ---")

        # Check if constraint already exists
        check_lesson_constraint = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
            AND TABLE_NAME = 'user_lessons'
            AND CONSTRAINT_NAME = 'unique_user_lesson'
            AND CONSTRAINT_TYPE = 'UNIQUE'
        """
        )

        result = await conn.execute(check_lesson_constraint)
        row = result.fetchone()

        if row and row[0] > 0:
            print("✓ Unique constraint 'unique_user_lesson' already exists")
        else:
            # Add the unique constraint
            add_lesson_constraint = text(
                """
                ALTER TABLE user_lessons
                ADD CONSTRAINT unique_user_lesson UNIQUE (user_id, lesson_id)
            """
            )

            try:
                await conn.execute(add_lesson_constraint)
                print(
                    "✓ Successfully added unique constraint 'unique_user_lesson' to user_lessons table"
                )
            except Exception as e:
                print(f"✗ Error adding constraint to user_lessons: {e}")
                raise


async def downgrade():
    """Remove unique constraints from user_modules and user_lessons tables."""
    async with engine.begin() as conn:
        # Remove constraint from user_modules
        print("\n--- Processing user_modules table ---")

        # Check if constraint exists
        check_module_constraint = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
            AND TABLE_NAME = 'user_modules'
            AND CONSTRAINT_NAME = 'unique_user_module'
            AND CONSTRAINT_TYPE = 'UNIQUE'
        """
        )

        result = await conn.execute(check_module_constraint)
        row = result.fetchone()

        if row and row[0] == 0:
            print("✓ Unique constraint 'unique_user_module' does not exist")
        else:
            # Remove the unique constraint
            drop_module_constraint = text(
                """
                ALTER TABLE user_modules
                DROP INDEX unique_user_module
            """
            )

            try:
                await conn.execute(drop_module_constraint)
                print(
                    "✓ Successfully removed unique constraint 'unique_user_module' from user_modules table"
                )
            except Exception as e:
                print(f"✗ Error removing constraint from user_modules: {e}")
                raise

        # Remove constraint from user_lessons
        print("\n--- Processing user_lessons table ---")

        # Check if constraint exists
        check_lesson_constraint = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.TABLE_CONSTRAINTS
            WHERE CONSTRAINT_SCHEMA = DATABASE()
            AND TABLE_NAME = 'user_lessons'
            AND CONSTRAINT_NAME = 'unique_user_lesson'
            AND CONSTRAINT_TYPE = 'UNIQUE'
        """
        )

        result = await conn.execute(check_lesson_constraint)
        row = result.fetchone()

        if row and row[0] == 0:
            print("✓ Unique constraint 'unique_user_lesson' does not exist")
        else:
            # Remove the unique constraint
            drop_lesson_constraint = text(
                """
                ALTER TABLE user_lessons
                DROP INDEX unique_user_lesson
            """
            )

            try:
                await conn.execute(drop_lesson_constraint)
                print(
                    "✓ Successfully removed unique constraint 'unique_user_lesson' from user_lessons table"
                )
            except Exception as e:
                print(f"✗ Error removing constraint from user_lessons: {e}")
                raise


async def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage user_modules and user_lessons unique constraints"
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Action to perform: upgrade (add constraints) or downgrade (remove constraints)",
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Migration: Add unique constraints to user_modules & user_lessons")
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
