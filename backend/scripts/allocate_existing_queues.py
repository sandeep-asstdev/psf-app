import asyncio
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.auth import User
from app.models.followup import FollowupQueue
from app.services.allocation_service import allocate_queue_items

async def main():
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one()
        admin = (await db.execute(select(User).where(User.email == "admin@apexauto.com"))).scalar_one()

        # Unassign any queues assigned to Super Admin or non-CREs
        await db.execute(text("""
            UPDATE followup_queues 
            SET assigned_to_id = NULL 
            WHERE assigned_to_id IN (
                SELECT id FROM users WHERE email IN ('admin@apexauto.com', 'dealer.admin@apexauto.com', 'cre.admin@apexauto.com')
            )
        """))
        await db.commit()

        # Now allocate all unassigned PENDING queues
        unassigned = (await db.execute(
            select(FollowupQueue).where(
                FollowupQueue.tenant_id == tenant.id,
                FollowupQueue.assigned_to_id == None,
                FollowupQueue.status == "PENDING",
                FollowupQueue.is_deleted == False
            )
        )).scalars().all()
        print(f"Unassigned queues to allocate: {len(unassigned)}")

        if unassigned:
            run = await allocate_queue_items(
                db=db,
                tenant_id=tenant.id,
                queue_items=unassigned,
                started_by_id=admin.id,
                run_type="MANUAL_ALLOCATION",
                custom_rules={"strategy": "EQUAL_PRESENT_CRE", "pool_mode": "CRE_POOL"}
            )
            await db.commit()
            print(f"Allocated! Run id: {run.id}")
            print(f"Per-CRE counts: {run.summary.get('per_cre')}")

if __name__ == "__main__":
    asyncio.run(main())
