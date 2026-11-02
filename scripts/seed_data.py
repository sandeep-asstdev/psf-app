import asyncio
import uuid
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.core.crypto import encrypt_phone, hash_phone
from app.models.tenant import Tenant, Brand, Branch, Setting
from app.models.auth import Role, User, UserScope
from app.models.complaint import ComplaintCategory


async def seed():
    print("🌱 Starting PSF Platform Database Seeding...")

    async with AsyncSessionLocal() as db:
        # 1. Create Default Tenant
        tenant_stmt = select(Tenant).where(Tenant.slug == "apex-auto")
        tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()

        if not tenant:
            tenant = Tenant(
                name="Apex Automotive Group",
                slug="apex-auto",
                primary_color="#2563EB",
                is_active=True,
            )
            db.add(tenant)
            await db.flush()
            print(f"  ✓ Created Tenant: {tenant.name} [{tenant.id}]")
        else:
            print(f"  • Tenant already exists: {tenant.name}")

        # 2. Seed System Roles
        roles_def = [
            (
                "SUPER_ADMIN",
                "Full platform administrative access across tenants",
                [
                    "system:manage", "tenants:manage", "users:manage", "roles:manage",
                    "psf:read", "psf:call", "psf:admin", "complaints:manage", "reports:view",
                    "reports:export", "settings:manage",
                ],
                True,
            ),
            (
                "DEALER_ADMIN",
                "Full administrative access within the dealer group",
                [
                    "users:manage", "brands:manage", "branches:manage", "questionnaires:manage",
                    "psf:read", "psf:call", "psf:allocate", "complaints:manage", "reports:view",
                    "reports:export", "settings:manage",
                ],
                True,
            ),
            (
                "BRAND_MANAGER",
                "Brand-level reporting and questionnaire management",
                [
                    "users:manage", "psf:read", "complaints:manage", "reports:view",
                    "reports:export", "questionnaires:manage",
                ],
                False,
            ),
            (
                "BRANCH_MANAGER",
                "Branch-level operational oversight and complaint escalation",
                [
                    "psf:read", "psf:call", "psf:allocate", "complaints:manage",
                    "reports:view", "reports:export",
                ],
                False,
            ),
            (
                "CRE",
                "Customer Relations Executive - Outbound follow-up caller",
                [
                    "psf:read", "psf:call", "complaints:create", "reconfirmations:conduct",
                    "reminders:manage",
                ],
                False,
            ),
            (
                "SERVICE_ADVISOR",
                "Workshop Service Advisor - Review customer feedback and assigned complaints",
                [
                    "advisor:read", "advisor:action", "complaints:view",
                ],
                False,
            ),
            (
                "AUDITOR",
                "Read-only auditor with comprehensive export permissions",
                [
                    "psf:read", "complaints:view", "reports:view", "reports:export",
                    "audit:view",
                ],
                False,
            ),
        ]

        roles_map = {}
        for role_name, desc, perms, is_sys in roles_def:
            r_stmt = select(Role).where(
                (Role.tenant_id == tenant.id) | (Role.tenant_id == None),
                Role.name == role_name,
            )
            role = (await db.execute(r_stmt)).scalar_one_or_none()
            if not role:
                role = Role(
                    tenant_id=tenant.id,
                    name=role_name,
                    description=desc,
                    permissions=perms,
                    is_system=is_sys,
                )
                db.add(role)
                await db.flush()
                print(f"  ✓ Created Role: {role_name}")
            roles_map[role_name] = role

        # 3. Seed Automotive Brands
        brands_def = [
            ("Hyundai", "HYUN", "#002C6C"),
            ("MG Motors", "MG", "#CC0000"),
            ("Ather Energy", "ATHER", "#00D282"),
        ]
        brands_map = {}
        for b_name, b_code, b_color in brands_def:
            b_stmt = select(Brand).where(Brand.tenant_id == tenant.id, Brand.code == b_code)
            brand = (await db.execute(b_stmt)).scalar_one_or_none()
            if not brand:
                brand = Brand(
                    tenant_id=tenant.id,
                    name=b_name,
                    code=b_code,
                    primary_color=b_color,
                    is_active=True,
                )
                db.add(brand)
                await db.flush()
                print(f"  ✓ Created Brand: {b_name} ({b_code})")
            brands_map[b_code] = brand

        # 4. Seed Workshop Branches
        branches_def = [
            ("Apex Central Workshop", "APEX-CENTRAL", "HYUN", "Bangalore", "Karnataka", "+91 98888 11111"),
            ("Apex West Hub", "APEX-WEST", "MG", "Bangalore", "Karnataka", "+91 98888 22222"),
            ("Apex North EV Center", "APEX-NORTH", "ATHER", "Bangalore", "Karnataka", "+91 98888 33333"),
        ]
        branches_map = {}
        for br_name, br_code, b_code, city, state, ph in branches_def:
            br_stmt = select(Branch).where(Branch.tenant_id == tenant.id, Branch.code == br_code)
            branch = (await db.execute(br_stmt)).scalar_one_or_none()
            if not branch:
                branch = Branch(
                    tenant_id=tenant.id,
                    brand_id=brands_map[b_code].id,
                    name=br_name,
                    code=br_code,
                    city=city,
                    state=state,
                    phone=encrypt_phone(ph),
                    is_active=True,
                )
                db.add(branch)
                await db.flush()
                print(f"  ✓ Created Branch: {br_name} ({br_code})")
            branches_map[br_code] = branch

        # 5. Seed Core Personnel Users
        users_def = [
            ("admin@apexauto.com", "Admin@12345", "Sandeep Sharma", "SUPER_ADMIN", "EMP-001", "+91 98765 00001", None, None),
            ("dealer.admin@apexauto.com", "Dealer@12345", "Vikram Malhotra", "DEALER_ADMIN", "EMP-002", "+91 98765 00002", None, None),
            ("manager.central@apexauto.com", "Manager@12345", "Anand Rao", "BRANCH_MANAGER", "EMP-003", "+91 98765 00003", "HYUN", "APEX-CENTRAL"),
            ("priya.cre@apexauto.com", "Priya@12345", "Priya Sharma", "CRE", "EMP-101", "+91 98765 43210", "HYUN", "APEX-CENTRAL"),
            ("rajesh.adv@apexauto.com", "Advisor@12345", "Rajesh Kumar", "SERVICE_ADVISOR", "EMP-201", "+91 98765 54321", "HYUN", "APEX-CENTRAL"),
            ("audit@apexauto.com", "Auditor@12345", "Meera Nambiar", "AUDITOR", "EMP-301", "+91 98765 67890", None, None),
        ]

        for email, pwd, name, role_k, emp_id, phone, sc_brand, sc_branch in users_def:
            u_stmt = select(User).where(User.tenant_id == tenant.id, User.email == email)
            user = (await db.execute(u_stmt)).scalar_one_or_none()
            if not user:
                user = User(
                    tenant_id=tenant.id,
                    role_id=roles_map[role_k].id,
                    email=email,
                    hashed_password=get_password_hash(pwd),
                    full_name=name,
                    employee_id=emp_id,
                    phone=encrypt_phone(phone),
                    phone_hash=hash_phone(phone),
                    is_active=True,
                )
                db.add(user)
                await db.flush()

                # Add scope
                if sc_brand or sc_branch:
                    scope = UserScope(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        brand_id=brands_map[sc_brand].id if sc_brand else None,
                        branch_id=branches_map[sc_branch].id if sc_branch else None,
                    )
                    db.add(scope)

                print(f"  ✓ Created User: {name} ({email}) - {role_k}")

        # 6. Seed Complaint Categories
        categories_def = [
            ("Workmanship & Repair Quality", 24, "HIGH"),
            ("Billing & Charges Discrepancy", 12, "MEDIUM"),
            ("Delivery Delay", 8, "MEDIUM"),
            ("Staff Demeanor & Courtesy", 24, "LOW"),
            ("Washing & Cleanliness", 6, "LOW"),
            ("Insurance & Claim Support", 48, "HIGH"),
        ]
        for c_name, sla, sev in categories_def:
            c_stmt = select(ComplaintCategory).where(ComplaintCategory.tenant_id == tenant.id, ComplaintCategory.name == c_name)
            cat = (await db.execute(c_stmt)).scalar_one_or_none()
            if not cat:
                cat = ComplaintCategory(
                    tenant_id=tenant.id,
                    name=c_name,
                    default_sla_hours=sla,
                    severity_level=sev,
                    is_active=True,
                )
                db.add(cat)
                print(f"  ✓ Created Complaint Category: {c_name} (SLA: {sla}h)")

        await db.commit()
        print("✅ Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
