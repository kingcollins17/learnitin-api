"""Check database connection and tables."""
import asyncio
from app.common.database.session import engine
from sqlalchemy import text


async def check_database():
    """Check database connection and list tables."""
    async with engine.connect() as conn:
        # Check current database
        result = await conn.execute(text("SELECT DATABASE()"))
        db_name = result.scalar()
        print(f"✓ Connected to database: {db_name}")
        
        # List all tables
        result = await conn.execute(text("SHOW TABLES"))
        tables = result.fetchall()
        
        if tables:
            print(f"\n✓ Found {len(tables)} table(s):")
            for table in tables:
                print(f"  - {table[0]}")
                
                # Describe the table
                result = await conn.execute(text(f"DESCRIBE {table[0]}"))
                columns = result.fetchall()
                print(f"    Columns: {len(columns)}")
                for col in columns:
                    print(f"      • {col[0]} ({col[1]})")
        else:
            print("\n✗ No tables found in database")
        
        # Check if we can query users table
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            print(f"\n✓ Users table exists with {count} rows")
        except Exception as e:
            print(f"\n✗ Error querying users table: {e}")


if __name__ == "__main__":
    asyncio.run(check_database())
