import asyncio
import aiomysql
from app.common.config import settings

async def check_processlist():
    print("Connecting to MySQL to check processlist...")
    conn = await aiomysql.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )

    async with conn.cursor(aiomysql.DictCursor) as cursor:
        await cursor.execute("SHOW PROCESSLIST")
        processes = await cursor.fetchall()
        print(f"\nActive Connections: {len(processes)}")
        for proc in processes:
            print(f"ID: {proc['Id']} | User: {proc['User']} | Host: {proc['Host']} | DB: {proc['db']} | Command: {proc['Command']} | Time: {proc['Time']} | State: {proc['State']} | Info: {proc['Info']}")
            
    conn.close()

if __name__ == "__main__":
    asyncio.run(check_processlist())
