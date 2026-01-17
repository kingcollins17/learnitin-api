"""
Migration: Remove subscription fields and add device registration token to users table
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.common.database.session import engine


async def upgrade():
    """Remove subscription columns and add device_reg_token to users table."""
    async with engine.begin() as conn:
        print("Migrating users table...")

        # 1. Remove current_plan from users
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE users 
                DROP COLUMN current_plan
                """
                )
            )
            print("✓ Dropped current_plan column from users table")
        except Exception as e:
            print(f"Skipped dropping current_plan from users: {e}")

        # 2. Remove last_subscribed_at from users
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE users 
                DROP COLUMN last_subscribed_at
                """
                )
            )
            print("✓ Dropped last_subscribed_at column from users table")
        except Exception as e:
            print(f"Skipped dropping last_subscribed_at from users: {e}")

        # 3. Add device_reg_token to users
        try:
            await conn.execute(
                text(
                    """
                ALTER TABLE users 
                ADD COLUMN device_reg_token TEXT
                """
                )
            )
            print("✓ Added device_reg_token column to users table")
        except Exception as e:
            print(f"Skipped adding device_reg_token to users: {e}")


async def downgrade():
    """Revert changes."""
    async with engine.begin() as conn:
        print("Reverting users table changes...")

        # 1. Add current_plan back
        await conn.execute(
            text(
                """
            ALTER TABLE users 
            ADD COLUMN current_plan VARCHAR(255) DEFAULT 'free'
            """
            )
        )

        # 2. Add last_subscribed_at back
        await conn.execute(
            text(
                """
            ALTER TABLE users 
            ADD COLUMN last_subscribed_at DATETIME
            """
            )
        )

        # 3. Remove device_reg_token
        await conn.execute(
            text(
                """
            ALTER TABLE users 
            DROP COLUMN device_reg_token
            """
            )
        )
        print("✓ Reverted all changes")


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
