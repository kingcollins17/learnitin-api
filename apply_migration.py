import asyncio
import sys
import os

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.common.database.session import engine


async def migrate():
    print("Starting migration...")
    async with engine.begin() as conn:
        try:
            print("Adding sub_category_id column to courses table...")
            await conn.execute(
                text("ALTER TABLE courses ADD COLUMN sub_category_id INTEGER")
            )
            print("Column added.")

            print("Adding FK constraint...")
            await conn.execute(
                text(
                    "ALTER TABLE courses ADD CONSTRAINT fk_courses_sub_categories FOREIGN KEY (sub_category_id) REFERENCES sub_categories(id)"
                )
            )
            print("FK constraint added.")

        except Exception as e:
            print(f"Migration step failed (ignored if already exists): {e}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
