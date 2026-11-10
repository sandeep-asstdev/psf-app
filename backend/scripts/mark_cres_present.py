import asyncio
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.auth import User, Role
from app.models.allocation import AttendanceOverride

async def main():
    async with AsyncSessionLocal() as db:
        today = datetime.now(timezone.utc).date()
        # Find super admin as marker
        admin = (await db.execute(select(User).where(User.email == "admin@apexauto.com"))).scalar_one()
        
        # Find all CREs
        cre_roles = ["CRE", "BRANCH_CRE"]
        cres = (await db.execute(
            select(User).join(Role, User.role_id == Role.id).where(
                Role.name.in_(cre_roles),
                User.is_active == True,
                User.is_deleted == False
            )
        )).scalars().all()

        for cre in cres:
            existing = (await db.execute(
                select(AttendanceOverride).where(
                    AttendanceOverride.user_id == cre.id,
                    AttendanceOverride.attendance_date == today
                )
            )).scalar_one_or_none()
            if existing:
                existing.status = "PRESENT"
                existing.reason = "Shift active"
            else:
                db.add(AttendanceOverride(
                    tenant_id=cre.tenant_id,
                    user_id=cre.id,
                    attendance_date=today,
                    status="PRESENT",
                    marked_by_id=admin.id,
                    reason="Shift active",
                ))
        await db.commit()
        print(f"Marked {len(cres)} CREs as PRESENT for {today}!")

if __name__ == "__main__":
    asyncio.run(main())

