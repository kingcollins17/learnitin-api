"""Migration to change question columns to TEXT.

This script modifies the 'questions' table to use TEXT columns for:
- question
- option_1
- option_2
- option_3
- option_4
- explanation
"""

import asyncio
from sqlalchemy import text, Column, Text
from app.common.database.session import engine


async def upgrade():
    """Apply the migration."""
    async with engine.begin() as conn:
        print("Changing question columns to TEXT...")

        # MySQL syntax for changing column types
        queries = [
            "ALTER TABLE questions MODIFY COLUMN question TEXT NOT NULL",
            "ALTER TABLE questions MODIFY COLUMN option_1 TEXT",
            "ALTER TABLE questions MODIFY COLUMN option_2 TEXT",
            "ALTER TABLE questions MODIFY COLUMN option_3 TEXT",
            "ALTER TABLE questions MODIFY COLUMN option_4 TEXT",
            "ALTER TABLE questions MODIFY COLUMN explanation TEXT",
        ]

        for query in queries:
            await conn.execute(text(query))

        print("✓ Successfully updated questions table columns to TEXT.")


async def downgrade():
    """Reverse the migration."""
    async with engine.begin() as conn:
        print("Changing question columns back to VARCHAR(255)...")
        # Assuming original was VARCHAR(255) as is default for SQLModel/SQLAlchemy if not specified
        queries = [
            "ALTER TABLE questions MODIFY COLUMN question VARCHAR(255) NOT NULL",
            "ALTER TABLE questions MODIFY COLUMN option_1 VARCHAR(255)",
            "ALTER TABLE questions MODIFY COLUMN option_2 VARCHAR(255)",
            "ALTER TABLE questions MODIFY COLUMN option_3 VARCHAR(255)",
            "ALTER TABLE questions MODIFY COLUMN option_4 VARCHAR(255)",
            "ALTER TABLE questions MODIFY COLUMN explanation VARCHAR(255)",
        ]

        for query in queries:
            await conn.execute(text(query))

        print("✓ Successfully reverted questions table columns.")


if __name__ == "__main__":
    asyncio.run(upgrade())
