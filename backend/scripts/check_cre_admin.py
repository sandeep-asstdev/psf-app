import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.auth import User
from app.core.security import verify_password

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == "cre.admin@apexauto.com"))
        user = res.scalar_one_or_none()
        if user:
            print("cre.admin user found:", user.id, user.email, "active:", user.is_active, "deleted:", user.is_deleted)
            match = verify_password("Password@12345", user.hashed_password)
            print("Password matches:", match)
        else:
            print("cre.admin user NOT found!")

if __name__ == "__main__":
    asyncio.run(main())

