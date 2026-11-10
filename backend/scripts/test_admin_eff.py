import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.auth import User
from app.core.permissions import get_user_effective_permissions

async def main():
    async with AsyncSessionLocal() as db:
        admin = (await db.execute(select(User).where(User.email == "admin@apexauto.com"))).scalar_one()
        eff = await get_user_effective_permissions(db, admin)
        print("Admin eff:", eff)

if __name__ == "__main__":
    asyncio.run(main())

