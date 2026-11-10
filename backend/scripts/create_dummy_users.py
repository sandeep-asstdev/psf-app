import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.auth import Role, User, UserScope
from app.models.tenant import Tenant, Brand, Branch
from app.core.security import get_password_hash
from app.core.crypto import encrypt_phone, hash_phone

DUMMY_USERS = [
    {
        "role_name": "SUPER_ADMIN",
        "email": "admin@apexauto.com",
        "password": "Password@12345",
        "full_name": "Sandeep Sharma (Super Admin)",
        "employee_id": "EMP-SA-001",
        "phone": "+91 98765 00001",
        "scope_type": "ALL",
        "description": "L1 Super Admin - Developer & Enterprise full control across all brands & branches",
    },
    {
        "role_name": "CRE_ADMIN",
        "email": "cre.admin@apexauto.com",
        "password": "Password@12345",
        "full_name": "Rohan Mehra (CRE Admin)",
        "employee_id": "EMP-CA-002",
        "phone": "+91 98765 00002",
        "scope_type": "DEALERSHIP",
        "description": "L2 CRE Admin - Dealership-wide CRE management, call allocation & complaint closure",
    },
    {
        "role_name": "DEALER_ADMIN",
        "email": "dealer.admin@apexauto.com",
        "password": "Password@12345",
        "full_name": "Vikram Malhotra (Dealer Admin)",
        "employee_id": "EMP-DA-003",
        "phone": "+91 98765 00003",
        "scope_type": "DEALERSHIP",
        "description": "L2 Dealer Principal / Operations Administrator",
    },
    {
        "role_name": "BRAND_MANAGER",
        "email": "brand.manager@apexauto.com",
        "password": "Password@12345",
        "full_name": "Kavita Sen (Brand Manager - Hyundai)",
        "employee_id": "EMP-BM-004",
        "phone": "+91 98765 00004",
        "scope_type": "BRAND",
        "brand_code": "HYUN",
        "description": "L3 Brand Level Manager - Scoped to Hyundai brand across dealership branches",
    },
    {
        "role_name": "BRANCH_MANAGER",
        "email": "branch.manager@apexauto.com",
        "password": "Password@12345",
        "full_name": "Anand Rao (Branch Manager)",
        "employee_id": "EMP-MGR-005",
        "phone": "+91 98765 00005",
        "scope_type": "BRANCH",
        "branch_code": "APEX-CENTRAL",
        "description": "L3 Branch Manager - Scoped to Apex Central Workshop",
    },
    {
        "role_name": "SERVICE_MANAGER",
        "email": "service.manager@apexauto.com",
        "password": "Password@12345",
        "full_name": "Deepa Hiremath (Service Manager)",
        "employee_id": "EMP-SM-006",
        "phone": "+91 98765 00006",
        "scope_type": "BRANCH",
        "branch_code": "APEX-CENTRAL",
        "description": "L3 Workshop Service Manager - Escalation and technical complaint resolution",
    },
    {
        "role_name": "BRANCH_CRE",
        "email": "branch.cre@apexauto.com",
        "password": "Password@12345",
        "full_name": "Sunita Patil (Branch CRE)",
        "employee_id": "EMP-BCRE-007",
        "phone": "+91 98765 00007",
        "scope_type": "BRANCH",
        "branch_code": "APEX-CENTRAL",
        "description": "L3 Branch Customer Relationship Executive - Own branch follow-up calls & surveys",
    },
    {
        "role_name": "CRE",
        "email": "cre@apexauto.com",
        "password": "Password@12345",
        "full_name": "Priya Sharma (Central CRE)",
        "employee_id": "EMP-CRE-008",
        "phone": "+91 98765 00008",
        "scope_type": "BRANCH",
        "branch_code": "APEX-CENTRAL",
        "description": "L3 Call Center CRE - Assigned PSF & TNPS queue calling",
    },
    {
        "role_name": "SERVICE_ADVISOR",
        "email": "service.advisor@apexauto.com",
        "password": "Password@12345",
        "full_name": "Rajesh Kumar (Service Advisor)",
        "employee_id": "EMP-ADV-009",
        "phone": "+91 98765 00009",
        "scope_type": "BRANCH",
        "branch_code": "APEX-CENTRAL",
        "description": "L3 Service Advisor - Customer complaints and advisor follow-up actions",
    },
    {
        "role_name": "AUDITOR",
        "email": "auditor@apexauto.com",
        "password": "Password@12345",
        "full_name": "Meera Nambiar (Auditor)",
        "employee_id": "EMP-AUD-010",
        "phone": "+91 98765 00010",
        "scope_type": "DEALERSHIP",
        "description": "L3 Quality & Audit Officer - Read-only reporting and audit export access",
    },
]

async def seed_dummy_users():
    async with AsyncSessionLocal() as db:
        # 1. Fetch Tenant
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one_or_none()
        if not tenant:
            print("Error: No tenant found in DB.")
            return

        # 2. Fetch all active roles
        roles = (await db.execute(select(Role).where(Role.is_deleted == False))).scalars().all()
        roles_by_name = {r.name: r for r in roles}

        # 3. Fetch sample brand and branch for scoping
        hyundai_brand = (await db.execute(
            select(Brand).where(Brand.tenant_id == tenant.id, Brand.code == "HYUN")
        )).scalar_one_or_none()

        central_branch = (await db.execute(
            select(Branch).where(Branch.tenant_id == tenant.id, Branch.code == "APEX-CENTRAL")
        )).scalar_one_or_none()

        print(f"Tenant: {tenant.name} ({tenant.id})")
        print(f"Hyundai Brand: {hyundai_brand.id if hyundai_brand else 'Not found'}")
        print(f"Central Branch: {central_branch.id if central_branch else 'Not found'}")
        print("\nCreating / Updating Dummy Users for all roles:")
        print("=" * 70)

        created_or_updated = []

        for item in DUMMY_USERS:
            role_name = item["role_name"]
            role_obj = roles_by_name.get(role_name)
            if not role_obj:
                print(f"[!] Role '{role_name}' not found in database. Skipping.")
                continue

            email = item["email"].lower().strip()
            pwd = item["password"]
            hashed_pwd = get_password_hash(pwd)

            # Check if user already exists
            user = (await db.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == email)
            )).scalar_one_or_none()

            if user:
                # Update role and password
                user.role_id = role_obj.id
                user.hashed_password = hashed_pwd
                user.full_name = item["full_name"]
                user.is_active = True
                user.is_deleted = False
                user.employee_id = item["employee_id"]
                action = "UPDATED"
            else:
                user = User(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    role_id=role_obj.id,
                    email=email,
                    hashed_password=hashed_pwd,
                    full_name=item["full_name"],
                    employee_id=item["employee_id"],
                    phone=encrypt_phone(item["phone"]),
                    phone_hash=hash_phone(item["phone"]),
                    is_active=True,
                    is_deleted=False,
                )
                db.add(user)
                action = "CREATED"

            await db.flush()

            # Manage scope
            # Clear old scopes
            old_scopes = (await db.execute(
                select(UserScope).where(UserScope.user_id == user.id)
            )).scalars().all()
            for s in old_scopes:
                await db.delete(s)
            await db.flush()

            # Attach appropriate scope
            if item["scope_type"] == "BRAND" and hyundai_brand:
                scope = UserScope(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    user_id=user.id,
                    brand_id=hyundai_brand.id,
                    branch_id=None,
                )
                db.add(scope)
            elif item["scope_type"] == "BRANCH" and central_branch:
                scope = UserScope(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    user_id=user.id,
                    brand_id=central_branch.brand_id,
                    branch_id=central_branch.id,
                )
                db.add(scope)

            created_or_updated.append({
                "role": role_name,
                "level": role_obj.level,
                "email": email,
                "password": pwd,
                "full_name": item["full_name"],
                "description": item["description"],
                "action": action,
            })
            print(f"[{action}] {role_name:<16} ({role_obj.level}) -> {email:<28} [Password: {pwd}]")

        await db.commit()
        print("=" * 70)
        print("Successfully seeded all dummy users!")
        return created_or_updated

if __name__ == "__main__":
    asyncio.run(seed_dummy_users())

