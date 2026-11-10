import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.auth import User
from app.services.psf_service import list_followup_queues

async def main():
    async with AsyncSessionLocal() as db:
        admin = (await db.execute(select(User).where(User.email == "admin@apexauto.com"))).scalar_one()
        priya = (await db.execute(select(User).where(User.email == "priya.cre@apexauto.com"))).scalar_one()
        arpita = (await db.execute(select(User).where(User.email == "arpita.cre@apexauto.com"))).scalar_one()

        # Admin view
        admin_items, admin_total = await list_followup_queues(
            db=db,
            tenant_id=admin.tenant_id,
            queue_type="PSF",
            current_user=admin,
            limit=50
        )
        print(f"Admin sees total items: {admin_total}")
        sample_cre_names = set(item.assigned_to_name for item in admin_items if item.assigned_to_name)
        print(f"Admin sees items assigned to: {sample_cre_names}")

        # Priya view
        priya_items, priya_total = await list_followup_queues(
            db=db,
            tenant_id=priya.tenant_id,
            queue_type="PSF",
            current_user=priya,
            limit=50
        )
        print(f"Priya (CRE) sees total items: {priya_total}")
        priya_cre_names = set(item.assigned_to_name for item in priya_items if item.assigned_to_name)
        print(f"Priya sees items assigned to: {priya_cre_names}")

        # Arpita view
        arpita_items, arpita_total = await list_followup_queues(
            db=db,
            tenant_id=arpita.tenant_id,
            queue_type="PSF",
            current_user=arpita,
            limit=50
        )
        print(f"Arpita (CRE) sees total items: {arpita_total}")
        arpita_cre_names = set(item.assigned_to_name for item in arpita_items if item.assigned_to_name)
        print(f"Arpita sees items assigned to: {arpita_cre_names}")

if __name__ == "__main__":
    asyncio.run(main())

