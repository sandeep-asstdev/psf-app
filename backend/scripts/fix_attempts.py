import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT id FROM job_cards WHERE job_card_no = 'S8211_R202600449'"))
        jc_id = res.scalar()
        if jc_id:
            await db.execute(text(f"UPDATE followup_queues SET attempts = 5, contacted_count = 0, status = 'NOT_CONTACTED' WHERE job_card_id = '{jc_id}'"))
            await db.commit()
            print("Reset attempts to 5 for S8211_R202600449")

if __name__ == "__main__":
    asyncio.run(main())

