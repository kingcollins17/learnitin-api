"""
Migration: Add image_url to categories and sub_categories tables

Run this migration with:
    python migrations/add_image_url_to_categories_and_subcategories.py upgrade
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def check_column_exists(table_name: str, column_name: str) -> bool:
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


async def upgrade():
    """Add image_url column to categories and sub_categories."""
    async with engine.begin() as conn:
        # Check and add image_url to categories
        if await check_column_exists("categories", "image_url"):
            print("SUCCESS: Column 'image_url' already exists in categories")
        else:
            print("Adding 'image_url' column to categories...")
            await conn.execute(
                text("ALTER TABLE categories ADD COLUMN image_url VARCHAR(512) NULL")
            )
            print("SUCCESS: Successfully added 'image_url' column to categories")

        # Check and add image_url to sub_categories
        if await check_column_exists("sub_categories", "image_url"):
            print("SUCCESS: Column 'image_url' already exists in sub_categories")
        else:
            print("Adding 'image_url' column to sub_categories...")
            await conn.execute(
                text("ALTER TABLE sub_categories ADD COLUMN image_url VARCHAR(512) NULL")
            )
            print("SUCCESS: Successfully added 'image_url' column to sub_categories")


async def downgrade():
    """Remove image_url column from categories and sub_categories."""
    async with engine.begin() as conn:
        # Check and remove image_url from sub_categories
        if not await check_column_exists("sub_categories", "image_url"):
            print("SUCCESS: Column 'image_url' does not exist in sub_categories")
        else:
            print("Removing 'image_url' column from sub_categories...")
            await conn.execute(
                text("ALTER TABLE sub_categories DROP COLUMN image_url")
            )
            print("SUCCESS: Successfully removed 'image_url' column from sub_categories")

        # Check and remove image_url from categories
        if not await check_column_exists("categories", "image_url"):
            print("SUCCESS: Column 'image_url' does not exist in categories")
        else:
            print("Removing 'image_url' column from categories...")
            await conn.execute(
                text("ALTER TABLE categories DROP COLUMN image_url")
            )
            print("SUCCESS: Successfully removed 'image_url' column from categories")


async def main():
    """Run the migration."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Add image_url column to categories and sub_categories tables"
    )
    parser.add_argument(
        "action",
        choices=["upgrade", "downgrade"],
        help="Action to perform: upgrade or downgrade",
    )

    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"Migration: Add image_url to categories and sub_categories")
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
