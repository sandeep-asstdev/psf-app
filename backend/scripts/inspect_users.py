import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id, email, full_name, is_active FROM users ORDER BY email"))
        rows = result.fetchall()
        print(f"Total users in DB: {len(rows)}")
        for r in rows:
            print(f"{r.id} | {r.email} | {r.full_name} | active={r.is_active}")

if __name__ == "__main__":
    asyncio.run(main())

