import asyncio
import asyncmy
from app.common.config import settings


async def create_test_db():
    db_name = f"test_{settings.DB_NAME}"
    print(f"Connecting to MySQL to create database: {db_name}...")

    conn = await asyncmy.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )

    async with conn.cursor() as cursor:
        await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        print(f"Database {db_name} created successfully.")

    conn.close()


if __name__ == "__main__":
    asyncio.run(create_test_db())
