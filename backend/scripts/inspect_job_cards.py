import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT count(*) FROM job_cards WHERE job_card_no NOT LIKE 'JC-%' AND job_card_no NOT LIKE 'nan'"))
        print("Real job cards count:", res.scalar())
        res_test = await session.execute(text("SELECT count(*) FROM job_cards WHERE job_card_no LIKE 'JC-%' OR job_card_no = 'nan'"))
        print("Test/nan job cards count:", res_test.scalar())

if __name__ == "__main__":
    asyncio.run(main())
