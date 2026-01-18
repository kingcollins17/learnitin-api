"""
Migration: Add unique constraint to quizzes table

This migration adds a unique constraint on the lesson_id in the quizzes table
to ensure each lesson can only have one quiz.

Run this migration with:
    python migrations/add_unique_quiz_lesson_constraint.py upgrade
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Add unique constraint to quizzes table."""
    async with engine.begin() as conn:
        # Check if any unique index on lesson_id already exists
        check_index_query = text(
            """
            SHOW INDEX FROM quizzes WHERE Column_name = 'lesson_id' AND Non_unique = 0
        """
        )

        result = await conn.execute(check_index_query)
        exists = result.fetchone()

        if exists:
            print(f"✓ A unique index on 'lesson_id' already exists ({exists[2]})")
            return

        # Add the unique constraint
        add_constraint_query = text(
            """
            ALTER TABLE quizzes
            ADD CONSTRAINT unique_quiz_lesson UNIQUE (lesson_id)
        """
        )

        try:
            await conn.execute(add_constraint_query)
            print(
                "✓ Successfully added unique constraint 'unique_quiz_lesson' to quizzes table"
            )
        except Exception as e:
            print(f"✗ Error adding constraint: {e}")
            raise


async def downgrade():
    """Remove unique constraint from quizzes table."""
    async with engine.begin() as conn:
        # Check if any unique index on lesson_id exists
        check_index_query = text(
            """
            SHOW INDEX FROM quizzes WHERE Column_name = 'lesson_id' AND Non_unique = 0
        """
        )

        result = await conn.execute(check_index_query)
        exists = result.fetchone()

        if not exists:
            print("✓ No unique index on 'lesson_id' exists")
            return

        index_name = exists[2]

        # Remove the unique constraint
        drop_constraint_query = text(f"ALTER TABLE quizzes DROP INDEX {index_name}")

        try:
            await conn.execute(drop_constraint_query)
            print(
                f"✓ Successfully removed unique index '{index_name}' from quizzes table"
            )
        except Exception as e:
            print(f"✗ Error removing index: {e}")
            raise


async def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage quizzes unique constraint")
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Action to perform: upgrade (add constraint) or downgrade (remove constraint)",
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Migration: Add unique constraint to quizzes")
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
