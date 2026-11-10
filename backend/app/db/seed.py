"""
================================================================================
FILE PURPOSE: Database Initial Seeding Script.
Seeds foundational system data on first installation:
default tenant, default OEM Brands (Hyundai, Tata, MG), default Branches,
all security Roles with permission mappings, and the initial Super Admin account.

KEY RESPONSIBILITIES:
- Creates default Apex Automotive Group tenant.
- Seeds standard dealership roles (Super Admin, CRE Admin, CRE, Service Advisor, etc.).
- Seeds initial Super Admin account (`admin@apexauto.com` / `Password@12345`).
- Seeds default OEM Brands and dealership workshop branches.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Seed script fails with IntegrityError
  -> Cause: Data was already seeded previously.
  -> What should you do: The script is idempotent; re-running it skips records that already exist.
================================================================================
"""
import asyncio
import uuid
import sys
import os

from sqlalchemy import select
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.core.crypto import encrypt_phone, hash_phone
from app.core.permissions import PermissionKey, DataScope
from app.models.tenant import Tenant, Brand, Branch, Setting
from app.models.auth import Role, RolePermission, User, UserScope
from app.models.complaint import ComplaintCategory
from app.models.service import ServiceType
from app.models.additional import CustomFieldDefinition, ImportMappingTemplate


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

        # 2. Seed System Roles & Hierarchy Levels (L1, L2, L3)
        roles_def = [
            (
                "SUPER_ADMIN",
                "L1",
                "Full platform administrative access across tenants, brands, and all branches",
                ["*"],
                {"phone": "unmasked"},
                True,
            ),
            (
                "CRE_ADMIN",
                "L2",
                "L2 Dealership CRE Admin: sees all brands/branches, manages CREs, allocates calls, imports, closes complaints",
                ["psf:read", "psf:call", "psf:allocate", "complaints:manage", "reports:view", "reports:export"],
                {"phone": "unmasked"},
                True,
            ),
            (
                "DEALER_ADMIN",
                "L2",
                "Full administrative access within the dealer group (Legacy alias to CRE Admin)",
                ["users:manage", "brands:manage", "branches:manage", "questionnaires:manage", "psf:read", "psf:call", "psf:allocate", "complaints:manage", "reports:view", "reports:export", "settings:manage"],
                {"phone": "unmasked"},
                True,
            ),
            (
                "BRANCH_MANAGER",
                "L3",
                "L3 Branch Manager: scoped to own branch(es), branch complaints, reassign within branch",
                ["psf:read", "psf:call", "psf:allocate", "complaints:manage", "reports:view", "reports:export"],
                {"phone": "unmasked"},
                True,
            ),
            (
                "BRANCH_CRE",
                "L3",
                "L3 Branch CRE: own assigned calls, survey execution, and feedback entry",
                ["psf:read", "psf:call", "complaints:create", "reconfirmations:conduct", "reminders:manage"],
                {"phone": "unmasked"},
                True,
            ),
            (
                "CRE",
                "L3",
                "Customer Relations Executive (Legacy alias to Branch CRE)",
                ["psf:read", "psf:call", "complaints:create", "reconfirmations:conduct", "reminders:manage"],
                {"phone": "unmasked"},
                True,
            ),
            (
                "SERVICE_ADVISOR",
                "L3",
                "L3 Service Advisor: own customers' complaints and advisor follow-up only (respond only)",
                ["advisor:read", "advisor:action", "complaints:view"],
                {"phone": "masked"},
                True,
            ),
            (
                "AUDITOR",
                "L3",
                "Read-only auditor with comprehensive export permissions",
                ["psf:read", "complaints:view", "reports:view", "reports:export", "audit:view"],
                {"phone": "masked"},
                True,
            ),
        ]

        roles_map = {}
        for role_name, level, desc, perms, field_rules, is_sys in roles_def:
            r_stmt = select(Role).where(
                (Role.tenant_id == tenant.id) | (Role.tenant_id == None),
                Role.name == role_name,
            )
            role = (await db.execute(r_stmt)).scalar_one_or_none()
            if not role:
                role = Role(
                    tenant_id=tenant.id,
                    name=role_name,
                    level=level,
                    description=desc,
                    permissions=perms,
                    field_rules=field_rules,
                    is_active=True,
                    is_system=is_sys,
                )
                db.add(role)
                await db.flush()
                print(f"  ✓ Created Role: {role_name} ({level})")
            else:
                role.level = level
                role.is_active = True
                role.field_rules = field_rules
                role.is_system = is_sys
                await db.flush()
            roles_map[role_name] = role

        # 2b. Seed Data-Driven Permission Matrix (role_permissions)
        matrix_perms = {
            "SUPER_ADMIN": [
                (PermissionKey.BRAND_MANAGE, DataScope.ALL),
                (PermissionKey.BRANCH_MANAGE, DataScope.ALL),
                (PermissionKey.USER_CREATE, DataScope.ALL),
                (PermissionKey.USER_EDIT, DataScope.ALL),
                (PermissionKey.USER_DELETE, DataScope.ALL),
                (PermissionKey.ROLE_MANAGE, DataScope.ALL),
                (PermissionKey.PERMISSION_MANAGE, DataScope.ALL),
                (PermissionKey.JOBCARD_VIEW, DataScope.ALL),
                (PermissionKey.JOBCARD_EDIT, DataScope.ALL),
                (PermissionKey.JOBCARD_IMPORT, DataScope.ALL),
                (PermissionKey.CALL_VIEW, DataScope.ALL),
                (PermissionKey.CALL_MAKE, DataScope.ALL),
                (PermissionKey.CALL_EDIT, DataScope.ALL),
                (PermissionKey.CALL_ALLOCATE, DataScope.ALL),
                (PermissionKey.CALL_REASSIGN, DataScope.ALL),
                (PermissionKey.SURVEY_FILL, DataScope.ALL),
                (PermissionKey.TNPS_MAKE, DataScope.ALL),
                (PermissionKey.RECONFIRMATION_MAKE, DataScope.ALL),
                (PermissionKey.ADVISOR_ACTION, DataScope.ALL),
                (PermissionKey.COMPLAINT_VIEW, DataScope.ALL),
                (PermissionKey.COMPLAINT_CREATE, DataScope.ALL),
                (PermissionKey.COMPLAINT_EDIT, DataScope.ALL),
                (PermissionKey.COMPLAINT_RESPOND, DataScope.ALL),
                (PermissionKey.COMPLAINT_CLOSE, DataScope.ALL),
                (PermissionKey.REPORT_VIEW, DataScope.ALL),
                (PermissionKey.REPORT_EXPORT, DataScope.ALL),
                (PermissionKey.AUDIT_VIEW, DataScope.ALL),
                (PermissionKey.CONFIG_VIEW, DataScope.ALL),
                (PermissionKey.CONFIG_MANAGE, DataScope.ALL),
                (PermissionKey.QUESTIONNAIRE_VIEW, DataScope.ALL),
                (PermissionKey.QUESTIONNAIRE_MANAGE, DataScope.ALL),
                (PermissionKey.DROPDOWN_VIEW, DataScope.ALL),
                (PermissionKey.DROPDOWN_MANAGE, DataScope.ALL),
                (PermissionKey.STATUS_VIEW, DataScope.ALL),
                (PermissionKey.STATUS_MANAGE, DataScope.ALL),
                (PermissionKey.SETTINGS_MANAGE, DataScope.ALL),
                (PermissionKey.ALLOCATION_CONFIGURE, DataScope.ALL),
                (PermissionKey.DATA_CORRECT, DataScope.ALL),
                (PermissionKey.CONTACT_UNMASK, DataScope.ALL),
            ],
            "CRE_ADMIN": [
                (PermissionKey.USER_CREATE, DataScope.OWN), # CREs only
                (PermissionKey.USER_EDIT, DataScope.OWN),
                (PermissionKey.JOBCARD_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.JOBCARD_EDIT, DataScope.DEALERSHIP),
                (PermissionKey.JOBCARD_IMPORT, DataScope.DEALERSHIP),
                (PermissionKey.CALL_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.CALL_MAKE, DataScope.DEALERSHIP),
                (PermissionKey.CALL_EDIT, DataScope.DEALERSHIP),
                (PermissionKey.CALL_ALLOCATE, DataScope.DEALERSHIP),
                (PermissionKey.CALL_REASSIGN, DataScope.DEALERSHIP),
                (PermissionKey.SURVEY_FILL, DataScope.DEALERSHIP),
                (PermissionKey.TNPS_MAKE, DataScope.DEALERSHIP),
                (PermissionKey.RECONFIRMATION_MAKE, DataScope.DEALERSHIP),
                (PermissionKey.COMPLAINT_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.COMPLAINT_CREATE, DataScope.DEALERSHIP),
                (PermissionKey.COMPLAINT_EDIT, DataScope.DEALERSHIP),
                (PermissionKey.COMPLAINT_RESPOND, DataScope.DEALERSHIP),
                (PermissionKey.COMPLAINT_CLOSE, DataScope.DEALERSHIP),
                (PermissionKey.REPORT_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.REPORT_EXPORT, DataScope.DEALERSHIP),
                (PermissionKey.AUDIT_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.QUESTIONNAIRE_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.DROPDOWN_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.STATUS_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.CONFIG_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.CONTACT_UNMASK, DataScope.DEALERSHIP),
            ],
            "BRANCH_MANAGER": [
                (PermissionKey.JOBCARD_VIEW, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.CALL_VIEW, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.CALL_ALLOCATE, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.CALL_REASSIGN, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.COMPLAINT_VIEW, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.COMPLAINT_CREATE, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.COMPLAINT_EDIT, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.COMPLAINT_RESPOND, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.COMPLAINT_CLOSE, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.REPORT_VIEW, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.REPORT_EXPORT, DataScope.ASSIGNED_BRANCHES),
                (PermissionKey.CONTACT_UNMASK, DataScope.ASSIGNED_BRANCHES),
            ],
            "BRANCH_CRE": [
                (PermissionKey.JOBCARD_VIEW, DataScope.OWN),
                (PermissionKey.CALL_VIEW, DataScope.OWN),
                (PermissionKey.CALL_MAKE, DataScope.OWN),
                (PermissionKey.CALL_EDIT, DataScope.OWN),
                (PermissionKey.SURVEY_FILL, DataScope.OWN),
                (PermissionKey.TNPS_MAKE, DataScope.OWN),
                (PermissionKey.RECONFIRMATION_MAKE, DataScope.OWN),
                (PermissionKey.COMPLAINT_CREATE, DataScope.OWN),
                (PermissionKey.REPORT_VIEW, DataScope.OWN),
                (PermissionKey.CONTACT_UNMASK, DataScope.OWN),
            ],
            "SERVICE_ADVISOR": [
                (PermissionKey.JOBCARD_VIEW, DataScope.OWN),
                (PermissionKey.COMPLAINT_VIEW, DataScope.OWN),
                (PermissionKey.COMPLAINT_RESPOND, DataScope.OWN), # Respond only
                (PermissionKey.ADVISOR_ACTION, DataScope.OWN),
                (PermissionKey.REPORT_VIEW, DataScope.OWN),
            ],
            "AUDITOR": [
                (PermissionKey.JOBCARD_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.CALL_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.COMPLAINT_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.REPORT_VIEW, DataScope.DEALERSHIP),
                (PermissionKey.REPORT_EXPORT, DataScope.DEALERSHIP),
                (PermissionKey.AUDIT_VIEW, DataScope.DEALERSHIP),
            ],
        }
        # Aliases
        matrix_perms["DEALER_ADMIN"] = matrix_perms["CRE_ADMIN"]
        matrix_perms["CRE"] = matrix_perms["BRANCH_CRE"]

        for r_name, p_list in matrix_perms.items():
            role_obj = roles_map.get(r_name)
            if not role_obj:
                continue
            for p_key, scope in p_list:
                rp_stmt = select(RolePermission).where(
                    RolePermission.tenant_id == tenant.id,
                    RolePermission.role_id == role_obj.id,
                    RolePermission.permission == p_key,
                )
                rp = (await db.execute(rp_stmt)).scalar_one_or_none()
                if not rp:
                    rp = RolePermission(
                        tenant_id=tenant.id,
                        role_id=role_obj.id,
                        permission=p_key,
                        data_scope=scope,
                    )
                    db.add(rp)
                else:
                    rp.data_scope = scope
            await db.flush()
        print("  ✓ Seeded Data-Driven Role Permission Matrix")

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

        # 7. Seed Default Service Types (Dropdown Masters)
        service_types_def = [
            ("Periodic Maintenance Service", "PMS", "#2563EB", "Wrench", 1),
            ("Running Repair", "RR", "#D97706", "Hammer", 2),
            ("Accidental & Bodyshop", "BODY", "#DC2626", "ShieldAlert", 3),
            ("General Inspection & Checkup", "GEN", "#059669", "ClipboardCheck", 4),
            ("Warranty & Recall Service", "WAR", "#7C3AED", "Award", 5),
            ("Unmapped Service", "UNMAPPED", "#6B7280", "HelpCircle", 99),
        ]
        for st_name, st_code, st_col, st_icon, st_ord in service_types_def:
            st_stmt = select(ServiceType).where(ServiceType.tenant_id == tenant.id, ServiceType.code == st_code)
            st_obj = (await db.execute(st_stmt)).scalar_one_or_none()
            if not st_obj:
                st_obj = ServiceType(
                    tenant_id=tenant.id,
                    name=st_name,
                    code=st_code,
                    color=st_col,
                    icon=st_icon,
                    display_order=st_ord,
                    is_active=True,
                )
                db.add(st_obj)
        print("  ✓ Seeded Default Service Types")

        # 8. Seed Default Custom Field Definitions
        custom_fields_def = [
            ("JOB_CARD", "fastag_verified", "Fastag Verified", "BOOLEAN", False, 1),
            ("JOB_CARD", "insurance_company", "Insurance Provider", "TEXT", False, 2),
            ("CALL", "preferred_callback_time", "Preferred Callback Time", "TEXT", False, 1),
            ("COMPLAINT", "root_cause_department", "Root Cause Department", "SELECT", False, 1),
        ]
        for ent, fkey, flabel, ftype, freq, forder in custom_fields_def:
            cf_stmt = select(CustomFieldDefinition).where(
                CustomFieldDefinition.tenant_id == tenant.id,
                CustomFieldDefinition.entity_type == ent,
                CustomFieldDefinition.field_key == fkey,
            )
            cf_obj = (await db.execute(cf_stmt)).scalar_one_or_none()
            if not cf_obj:
                cf_obj = CustomFieldDefinition(
                    tenant_id=tenant.id,
                    entity_type=ent,
                    field_key=fkey,
                    field_label=flabel,
                    field_type=ftype,
                    is_required=freq,
                    display_order=forder,
                    is_active=True,
                )
                db.add(cf_obj)
        print("  ✓ Seeded Default Custom Fields")

        # 9. Seed Default Import Column Mapping Templates (Standard DMS 13-Column Template)
        tpl_stmt = select(ImportMappingTemplate).where(
            ImportMappingTemplate.tenant_id == tenant.id,
            ImportMappingTemplate.name == "Standard DMS",
        )
        tpl_obj = (await db.execute(tpl_stmt)).scalar_one_or_none()
        standard_dms_mapping = {
            "Brand": "brand",
            "Branch": "branch",
            "Brand Logo": "brand_logo",
            "Job Card No": "job_card_no",
            "Job Card Date": "job_card_date",
            "Customer Name": "customer_name",
            "Contact Number": "contact_number",
            "Vin No": "vin_no",
            "Reg No": "reg_no",
            "Model": "model",
            "Service Advisor": "service_advisor",
            "Service Type": "service_type",
            "Total Service Amount": "total_service_amount",
        }
        if not tpl_obj:
            tpl_obj = ImportMappingTemplate(
                tenant_id=tenant.id,
                name="Standard DMS",
                column_mapping=standard_dms_mapping,
                is_default=True,
                is_active=True,
            )
            db.add(tpl_obj)
        else:
            tpl_obj.column_mapping = standard_dms_mapping
            tpl_obj.is_default = True

        print("  ✓ Seeded Default Standard DMS 13-Column Mapping Template")

        await db.commit()
        print("✅ Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())

