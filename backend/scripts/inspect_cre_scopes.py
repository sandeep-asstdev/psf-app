import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.auth import User, Role, UserScope

async def main():
    async with AsyncSessionLocal() as db:
        cres = (await db.execute(
            select(User).join(Role, User.role_id == Role.id).where(
                Role.name.in_(["CRE", "BRANCH_CRE"])
            )
        )).scalars().all()
        for c in cres:
            scopes = (await db.execute(
                select(UserScope).where(UserScope.user_id == c.id)
            )).scalars().all()
            print(f"{c.email} ({c.full_name}): {[str(s.branch_id) for s in scopes]}")

if __name__ == "__main__":
    asyncio.run(main())

