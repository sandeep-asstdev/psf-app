import asyncio
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.auth import User, Role, UserScope
from app.models.tenant import Branch

async def main():
    async with AsyncSessionLocal() as db:
        branches = (await db.execute(select(Branch))).scalars().all()
        print(f"Total branches: {len(branches)}")
        for b in branches:
            print(f"  Branch {b.name} ({b.id}) - Brand {b.brand_id}")

        # Find Central CREs
        central_cres = (await db.execute(
            select(User).where(User.email.in_(["priya.cre@apexauto.com", "cre@apexauto.com"]))
        )).scalars().all()

        for u in central_cres:
            # Delete old scopes
            await db.execute(text(f"DELETE FROM user_scopes WHERE user_id = '{u.id}'"))
            # Add scopes for all branches so they can take calls across all dealership branches
            for b in branches:
                db.add(UserScope(
                    tenant_id=u.tenant_id,
                    user_id=u.id,
                    brand_id=b.brand_id,
                    branch_id=b.id,
                ))
            print(f"Granted all branch scopes to {u.email}!")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())

