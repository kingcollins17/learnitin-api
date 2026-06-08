"""
Migration: Add popularity_score to sub_categories table

Run this migration with:
    python migrations/add_popularity_score_to_subcategories.py upgrade
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
            if await check_column_exists(engine, "sub_categories", "popularity_score"):
                print(f"SUCCESS: Column 'popularity_score' already exists in {db_name}.sub_categories")
            else:
                async with engine.begin() as conn:
                    print(f"Adding 'popularity_score' column to {db_name}.sub_categories...")
                    await conn.execute(
                        text("ALTER TABLE sub_categories ADD COLUMN popularity_score DOUBLE NOT NULL DEFAULT 0.0")
                    )
                    print(f"SUCCESS: Successfully added 'popularity_score' column to {db_name}.sub_categories")
        elif action == "downgrade":
            if not await check_column_exists(engine, "sub_categories", "popularity_score"):
                print(f"SUCCESS: Column 'popularity_score' does not exist in {db_name}.sub_categories")
            else:
                async with engine.begin() as conn:
                    print(f"Removing 'popularity_score' column from {db_name}.sub_categories...")
                    await conn.execute(
                        text("ALTER TABLE sub_categories DROP COLUMN popularity_score")
                    )
                    print(f"SUCCESS: Successfully removed 'popularity_score' column from {db_name}.sub_categories")
    finally:
        await engine.dispose()

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Add popularity_score column to sub_categories table"
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Action to perform: upgrade or downgrade",
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Migration: Add popularity_score to sub_categories")
    print(f"Action: {args.action}")
    print(f"{'='*60}\n")

    # Run for both staging and production
    databases = ["learnitin_staging", "learnitin"]
    for db in databases:
        try:
            print(f"\nStarting migration for: {db}")
            await migrate_db(db, args.action)
            print(f"Migration for {db} completed successfully!")
        except Exception as e:
            print(f"Migration for {db} failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
