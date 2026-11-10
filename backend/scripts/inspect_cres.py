import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.services.allocation_service import get_present_cres

async def main():
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one()
        cres = await get_present_cres(db, tenant.id)
        print(f"Total eligible CREs for tenant {tenant.name}: {len(cres)}")
        for c in cres:
            print(f"  {c['email']} ({c['full_name']}) -> keys: {list(c.keys())}")
            print(f"      present: {c.get('is_present')}, pending: {c.get('pending_calls')}")

if __name__ == "__main__":
    asyncio.run(main())
