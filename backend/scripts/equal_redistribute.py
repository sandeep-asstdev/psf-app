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

        # Reset all pending queue assignments so we can split cleanly and equally
        await db.execute(text("UPDATE followup_queues SET assigned_to_id = NULL WHERE status = 'PENDING'"))
        await db.commit()

        queues = (await db.execute(
            select(FollowupQueue).where(
                FollowupQueue.tenant_id == tenant.id,
                FollowupQueue.assigned_to_id == None,
                FollowupQueue.status == "PENDING",
                FollowupQueue.is_deleted == False
            )
        )).scalars().all()
        print(f"Total queues to equally allocate: {len(queues)}")

        run = await allocate_queue_items(
            db=db,
            tenant_id=tenant.id,
            queue_items=queues,
            started_by_id=admin.id,
            run_type="IMPORT_ALLOCATION",
            custom_rules={"strategy": "EQUAL_PRESENT_CRE", "pool_mode": "CRE_POOL"}
        )
        await db.commit()
        print(f"Allocation run {run.id} finished successfully!")
        print("Distribution breakdown:")
        for uid, info in run.summary.get("per_cre", {}).items():
            print(f"  {info['name']}: {info['count']} calls")

if __name__ == "__main__":
    asyncio.run(main())

