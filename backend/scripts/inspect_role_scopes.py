import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.auth import Role, RolePermission

async def main():
    async with AsyncSessionLocal() as db:
        roles = (await db.execute(select(Role))).scalars().all()
        for r in roles:
            rps = (await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == r.id,
                    RolePermission.permission.in_(["call.view", "call.make"])
                )
            )).scalars().all()
            print(f"Role: {r.name} (level={r.level})")
            for rp in rps:
                print(f"   {rp.permission} -> scope: {rp.data_scope}")

if __name__ == "__main__":
    asyncio.run(main())

