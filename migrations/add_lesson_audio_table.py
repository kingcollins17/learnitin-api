"""
Migration: Add lesson_audios table and modify lessons table
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Add lesson_audios table and modify lessons table."""
    async with engine.begin() as conn:
        print("Creating lesson_audios table...")

        # 1. Create lesson_audios table
        # Using MySQL dialect types roughly
        await conn.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS lesson_audios (
                id INTEGER NOT NULL AUTO_INCREMENT,
                lesson_id INTEGER NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                script LONGTEXT NOT NULL,
                audio_url TEXT NOT NULL,
                `order` INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME,
                PRIMARY KEY (id),
                FOREIGN KEY (lesson_id) REFERENCES lessons(id)
            );
            """
            )
        )
        print("✓ Created lesson_audios table")

        # 2. Add index on lesson_id
        # Check if index exists first or handle error?
        # MySQL usually gives warning if it exists or error.
        # Using simple CREATE INDEX.
        try:
            await conn.execute(
                text(
                    """
                CREATE INDEX ix_lesson_audios_lesson_id ON lesson_audios (lesson_id);
                """
                )
            )
            print("✓ Added index on lesson_id")
        except Exception:
            # ignore if already exists
            print("  (Index ix_lesson_audios_lesson_id might already exist)")

        # 3. Remove columns from lessons table
        print("Removing columns from lessons table...")

        # We need to check if columns exist before dropping to avoid errors if re-run
        # But for new features, usually we just try dropping.

        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                DROP COLUMN audio_transcript_url
                """
                )
            )
            print("✓ Dropped audio_transcript_url")
        except Exception as e:
            print(
                f"  Note: Could not drop audio_transcript_url (it might not exist): {e}"
            )

        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                DROP COLUMN has_quiz
                """
                )
            )
            print("✓ Dropped has_quiz")
        except Exception as e:
            print(f"  Note: Could not drop has_quiz (it might not exist): {e}")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting changes...")

        # 1. Re-add columns to lessons table
        # We assume they don't exist
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE lessons 
                ADD COLUMN audio_transcript_url TEXT,
                ADD COLUMN has_quiz BOOLEAN DEFAULT FALSE
                """
                )
            )
            print("✓ Re-added columns to lessons table")
        except Exception as e:
            print(f"Warning: Could not re-add columns: {e}")

        # 2. Drop lesson_audios table
        await conn.execute(
            text(
                """
            DROP TABLE IF EXISTS lesson_audios
            """
            )
        )
        print("✓ Dropped lesson_audios table")


async def main():
    try:
        await upgrade()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
