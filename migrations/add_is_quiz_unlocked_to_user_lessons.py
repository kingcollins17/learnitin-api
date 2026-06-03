"""
Migration: Add is_quiz_unlocked to user_lessons table

Run this migration with:
    python migrations/add_is_quiz_unlocked_to_user_lessons.py upgrade
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.common.config import settings

async def check_column_exists(engine, table_name: str, column_name: str) -> bool:
    """Check if a column already exists in a given table."""
    async with engine.begin() as conn:
        query = text(
            """
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = :table_name
            AND COLUMN_NAME = :col_name
        """
        )
        result = await conn.execute(query, {"table_name": table_name, "col_name": column_name})
        row = result.fetchone()
        return row and row[0] > 0

async def migrate_db(db_name: str, action: str):
    # Construct connection URL for the target database using the same mysql+aiomysql driver
    db_url = f"mysql+aiomysql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{db_name}"
    print(f"Connecting to {db_name} database...")
    engine = create_async_engine(db_url, echo=True)

    try:
        if action == "upgrade":
            if await check_column_exists(engine, "user_lessons", "is_quiz_unlocked"):
                print(f"SUCCESS: Column 'is_quiz_unlocked' already exists in {db_name}.user_lessons")
            else:
                async with engine.begin() as conn:
                    print(f"Adding 'is_quiz_unlocked' column to {db_name}.user_lessons...")
                    await conn.execute(
                        text("ALTER TABLE user_lessons ADD COLUMN is_quiz_unlocked BOOLEAN NOT NULL DEFAULT FALSE")
                    )
                    print(f"SUCCESS: Successfully added 'is_quiz_unlocked' column to {db_name}.user_lessons")
        elif action == "downgrade":
            if not await check_column_exists(engine, "user_lessons", "is_quiz_unlocked"):
                print(f"SUCCESS: Column 'is_quiz_unlocked' does not exist in {db_name}.user_lessons")
            else:
                async with engine.begin() as conn:
                    print(f"Removing 'is_quiz_unlocked' column from {db_name}.user_lessons...")
                    await conn.execute(
                        text("ALTER TABLE user_lessons DROP COLUMN is_quiz_unlocked")
                    )
                    print(f"SUCCESS: Successfully removed 'is_quiz_unlocked' column from {db_name}.user_lessons")
    finally:
        await engine.dispose()

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Add is_quiz_unlocked column to user_lessons table"
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Action to perform: upgrade or downgrade",
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Migration: Add is_quiz_unlocked to user_lessons")
    print(f"Action: {args.action}")
    print(f"{'='*60}\n")

    # Compile the list of target databases to try migrating
    databases = set()
    
    # 1. From settings DB_NAME
    if settings.DB_NAME:
        databases.add(settings.DB_NAME)
        databases.add(f"test_{settings.DB_NAME}")
        
    # 2. Add common staging, production, and dev database names
    databases.add("learnitin_staging")
    databases.add("test_learnitin_staging")
    databases.add("learnitin")
    databases.add("test_learnitin")
    databases.add("learnitin_db")
    databases.add("test_learnitin_db")
    
    # Ensure they are run in a predictable sorted order
    sorted_databases = sorted(list(databases))
    
    for db in sorted_databases:
        try:
            print(f"\nStarting migration for: {db}")
            await migrate_db(db, args.action)
            print(f"Migration for {db} completed successfully!")
        except Exception as e:
            print(f"WARNING: Migration for {db} skipped or failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
