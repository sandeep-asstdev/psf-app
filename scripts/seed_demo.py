"""
================================================================================
FILE PURPOSE: Realistic Demo Data Seeding Script.
Seeds a dedicated demo tenant with masked data for real-browser testing:
- 2 brands: Hyundai (PSF) and Ather Energy (TNPS)
- 3 branches: Central Workshop Hubli, North Workshop Gadag, Ather Space Belgaum
- Users for every role: Super Admin, CRE Admin, 3 CREs (active & present),
  Branch Manager (scoped to branch), Service Advisor (scoped to advisor)
- 300 Job cards with realistic vehicle models, Indian names, amounts, and dates
- Calls in all statuses: PENDING, CALLBACK_REQUESTED, CONTACTED, NOT_CONTACTED, CLOSED_MAX_ATTEMPTS
- 20 Complaints in all lifecycle states: Open, In Progress, Resolved, Closed
================================================================================
"""
import asyncio
import uuid
import sys
import os
import random
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

# Ensure backend path is on sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if os.path.exists(backend_path) and backend_path not in sys.path:
    sys.path.insert(0, backend_path)
app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if app_path not in sys.path:
    sys.path.insert(0, app_path)

from sqlalchemy import select, delete, func
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.core.crypto import encrypt_phone, hash_phone
from app.core.permissions import PermissionKey, DataScope, PERMISSION_CATALOGUE
from app.models.tenant import Tenant, Brand, Branch, Setting
from app.models.auth import Role, RolePermission, User, UserScope, LoginLog
from app.models.customer import Customer, Vehicle
from app.models.service import JobCard, ServiceType, ImportBatch
from app.models.followup import FollowupQueue, Call, CallAttempt, SurveyResponse, CaseStatus, CallStatus, Reminder
from app.models.complaint import Complaint, ComplaintCategory, ComplaintEvent, Reconfirmation
from app.models.questionnaire import Questionnaire, Question, KpiTag
from app.models.additional import RatingScale, RatingScaleBand
from app.models.config import FollowUpProgram, OutcomeRule, LabelOverride


# Sample realistic Indian customer names & vehicle models
INDIAN_NAMES = [
    "Rajesh Patil", "Priya Kulkarni", "Suresh Sharma", "Sneha Rao", "Anil Deshmukh",
    "Deepa Hegde", "Rahul Joshi", "Vinod Kumar", "Kavita Nayak", "Manoj Shetty",
    "Ganesh Gokhale", "Meena Dharwad", "Arun Kamat", "Swati Katti", "Ramesh Belgaumkar",
    "Pooja Deshpande", "Sunil Maratha", "Divya Hubballi", "Kiran Vernekar", "Shilpa Angadi",
    "Santosh Hiremath", "Rekha Badami", "Vijay Kankanady", "Roopa Shirodkar", "Sachin Shirali",
    "Geeta Kundapur", "Prakash Bellad", "Anita Hukkeri", "Raghavendra Pai", "Vidya Shenoy",
]

HYUNDAI_MODELS = ["Creta 1.5 SX", "Venue 1.0 Turbo", "i20 Asta IVT", "Verna 1.5 Turbo", "Alcazar 7-Seater", "Exter SX Opt"]
ATHER_MODELS = ["Ather 450X Gen 3", "Ather 450S", "Ather 450 Apex", "Ather Rizta Z"]
SERVICE_TYPES = ["Periodic Maintenance", "Free Service 1", "General Repair", "Running Repair", "Accidental Body Repair"]

COMPLAINT_DESCRIPTIONS = [
    ("Wash Quality", "Customer unhappy with water spots and interior vacuuming not done properly."),
    ("Billing Discrepancy", "Estimated ₹ 4,500 but invoiced ₹ 6,800 without prior phone approval."),
    ("Delayed Delivery", "Vehicle promised by 4 PM but delivered at 7:30 PM causing inconvenience."),
    ("Advisor Behaviour", "Service advisor was dismissive when customer pointed out squeaking brakes."),
    ("Parts Shortage", "Brake pads were not in stock leading to vehicle detained overnight."),
    ("AC Cooling Issue", "AC cooling performance still weak after gas refill and evaporator service."),
    ("Noise from Suspension", "Thumping noise in front left suspension still persists after shocker replacement."),
    ("Wheel Alignment", "Vehicle pulls to the left slightly on highways after alignment done."),
]


async def seed_demo():
    print("🚀 Seeding realistic Demo Tenant for PSF...")
    now = datetime.now(timezone.utc)
    today = now.date()

    async with AsyncSessionLocal() as db:
        # 1. Demo Tenant
        tenant_stmt = select(Tenant).where(Tenant.slug == "demo-motors")
        tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()

        if not tenant:
            tenant = Tenant(
                name="Demo Automotive Group",
                slug="demo-motors",
                primary_color="#002C6C",
                is_active=True,
            )
            db.add(tenant)
            await db.flush()
            print(f"  ✓ Created Demo Tenant: {tenant.name} [{tenant.id}]")
        else:
            print(f"  • Using existing Demo Tenant: {tenant.name} [{tenant.id}]")

        tenant_id = tenant.id

        # 2. Roles & Permissions
        role_definitions = [
            ("SUPER_ADMIN", "L1", "Super Admin with complete platform authority"),
            ("CRE_ADMIN", "L2", "CRE Admin with dealership-wide access"),
            ("BRANCH_MANAGER", "L3", "Branch Manager scoped to workshop branch"),
            ("CRE", "L3", "CRE Caller handling customer surveys"),
            ("SERVICE_ADVISOR", "L3", "Service Advisor managing assigned customers"),
        ]

        roles = {}
        for r_name, r_level, r_desc in role_definitions:
            r_stmt = select(Role).where(Role.tenant_id == tenant_id, Role.name == r_name)
            r_obj = (await db.execute(r_stmt)).scalar_one_or_none()
            if not r_obj:
                r_obj = Role(
                    tenant_id=tenant_id,
                    name=r_name,
                    level=r_level,
                    description=r_desc,
                    is_active=True,
                    is_system=True,
                )
                db.add(r_obj)
                await db.flush()
            roles[r_name] = r_obj

        # Assign permissions per role
        for p in PERMISSION_CATALOGUE:
            pkey = p["key"]
            # Super Admin has ALL
            sa_perm = (await db.execute(select(RolePermission).where(RolePermission.role_id == roles["SUPER_ADMIN"].id, RolePermission.permission == pkey))).scalar_one_or_none()
            if not sa_perm:
                db.add(RolePermission(tenant_id=tenant_id, role_id=roles["SUPER_ADMIN"].id, permission=pkey, data_scope=DataScope.ALL))

            # CRE Admin has DEALERSHIP for operational keys
            if pkey not in ["permission.manage", "data.correct"]:
                ca_perm = (await db.execute(select(RolePermission).where(RolePermission.role_id == roles["CRE_ADMIN"].id, RolePermission.permission == pkey))).scalar_one_or_none()
                if not ca_perm:
                    db.add(RolePermission(tenant_id=tenant_id, role_id=roles["CRE_ADMIN"].id, permission=pkey, data_scope=DataScope.DEALERSHIP))

            # Branch Manager has ASSIGNED_BRANCHES for calling/complaints/reports
            if pkey in ["call.view", "call.make", "call.edit", "complaint.view", "complaint.create", "complaint.edit", "complaint.respond", "complaint.close", "report.view", "report.export", "questionnaire.view", "jobcard.view"]:
                bm_perm = (await db.execute(select(RolePermission).where(RolePermission.role_id == roles["BRANCH_MANAGER"].id, RolePermission.permission == pkey))).scalar_one_or_none()
                if not bm_perm:
                    db.add(RolePermission(tenant_id=tenant_id, role_id=roles["BRANCH_MANAGER"].id, permission=pkey, data_scope=DataScope.ASSIGNED_BRANCHES))

            # CRE has OWN for calling and surveys
            if pkey in ["call.view", "call.make", "call.edit", "survey.fill", "tnps.make", "reconfirmation.make", "jobcard.view"]:
                cre_perm = (await db.execute(select(RolePermission).where(RolePermission.role_id == roles["CRE"].id, RolePermission.permission == pkey))).scalar_one_or_none()
                if not cre_perm:
                    db.add(RolePermission(tenant_id=tenant_id, role_id=roles["CRE"].id, permission=pkey, data_scope=DataScope.OWN))

            # Service Advisor has OWN for advisor actions
            if pkey in ["advisor.action", "jobcard.view", "complaint.view"]:
                sa_perm = (await db.execute(select(RolePermission).where(RolePermission.role_id == roles["SERVICE_ADVISOR"].id, RolePermission.permission == pkey))).scalar_one_or_none()
                if not sa_perm:
                    db.add(RolePermission(tenant_id=tenant_id, role_id=roles["SERVICE_ADVISOR"].id, permission=pkey, data_scope=DataScope.OWN))

        await db.flush()

        # 3. Brands (Hyundai, Ather)
        brands = {}
        b_data = [
            ("Hyundai Motor India", "HYUNDAI", "#002C6C", False, "PSF"),
            ("Ather Energy", "ATHER", "#10B981", True, "TNPS"),
        ]
        for b_name, b_code, b_color, b_tnps, b_label in b_data:
            stmt = select(Brand).where(Brand.tenant_id == tenant_id, Brand.code == b_code)
            b_obj = (await db.execute(stmt)).scalar_one_or_none()
            if not b_obj:
                b_obj = Brand(
                    tenant_id=tenant_id,
                    name=b_name,
                    code=b_code,
                    primary_color=b_color,
                    enable_tnps=b_tnps,
                    tnps_label=b_label,
                    is_active=True,
                )
                db.add(b_obj)
                await db.flush()
            brands[b_code] = b_obj

        # 4. Branches (3 branches)
        branches = {}
        branch_data = [
            ("Central Workshop Hubli", "CW-HUB", "S8211", brands["HYUNDAI"].id, "Hubli"),
            ("North Workshop Gadag", "NW-GAD", "S8827", brands["HYUNDAI"].id, "Gadag"),
            ("Ather Space Belgaum", "AS-BEL", "ATH01", brands["ATHER"].id, "Belgaum"),
        ]
        for br_name, br_code, br_dms, br_brand_id, br_city in branch_data:
            stmt = select(Branch).where(Branch.tenant_id == tenant_id, Branch.code == br_code)
            br_obj = (await db.execute(stmt)).scalar_one_or_none()
            if not br_obj:
                br_obj = Branch(
                    tenant_id=tenant_id,
                    brand_id=br_brand_id,
                    name=br_name,
                    code=br_code,
                    dms_code=br_dms,
                    display_name=br_name,
                    city=br_city,
                    state="Karnataka",
                    is_active=True,
                )
                db.add(br_obj)
                await db.flush()
            branches[br_code] = br_obj

        # 5. Users for every role
        users_def = [
            ("superadmin@demomotors.com", "Admin@12345", "Vikram Singhania", "SUPER_ADMIN", "EMP-SA-901"),
            ("creadmin@demomotors.com", "Password@12345", "Pooja Hegde", "CRE_ADMIN", "EMP-CA-902"),
            ("cre1@demomotors.com", "Password@12345", "Anjali Sharma", "CRE", "EMP-CRE-01"),
            ("cre2@demomotors.com", "Password@12345", "Kavita Rao", "CRE", "EMP-CRE-02"),
            ("cre3@demomotors.com", "Password@12345", "Sunita Patil", "CRE", "EMP-CRE-03"),
            ("manager@demomotors.com", "Password@12345", "Rajesh Kulkarni", "BRANCH_MANAGER", "EMP-BM-01"),
            ("advisor@demomotors.com", "Password@12345", "Mahesh Joshi", "SERVICE_ADVISOR", "EMP-SA-01"),
        ]

        users = {}
        for u_email, u_pass, u_name, u_role, u_emp in users_def:
            u_stmt = select(User).where(User.tenant_id == tenant_id, User.email == u_email)
            u_obj = (await db.execute(u_stmt)).scalar_one_or_none()
            if not u_obj:
                u_obj = User(
                    tenant_id=tenant_id,
                    role_id=roles[u_role].id,
                    email=u_email,
                    hashed_password=get_password_hash(u_pass),
                    full_name=u_name,
                    employee_id=u_emp,
                    is_active=True,
                )
                db.add(u_obj)
                await db.flush()
            users[u_email] = u_obj

        # Scopes: Branch Manager scoped to Central Workshop Hubli
        bm_user = users["manager@demomotors.com"]
        bm_scope = (await db.execute(select(UserScope).where(UserScope.user_id == bm_user.id))).scalar_one_or_none()
        if not bm_scope:
            db.add(UserScope(tenant_id=tenant_id, user_id=bm_user.id, branch_id=branches["CW-HUB"].id))

        # Service Advisor scoped to Central Workshop Hubli
        sa_user = users["advisor@demomotors.com"]
        sa_scope = (await db.execute(select(UserScope).where(UserScope.user_id == sa_user.id))).scalar_one_or_none()
        if not sa_scope:
            db.add(UserScope(tenant_id=tenant_id, user_id=sa_user.id, branch_id=branches["CW-HUB"].id))

        # Active Login Logs today for CREs so allocation service considers them present
        cre_list = [users["cre1@demomotors.com"], users["cre2@demomotors.com"], users["cre3@demomotors.com"]]
        for cre_user in cre_list:
            log_stmt = select(LoginLog).where(
                LoginLog.user_id == cre_user.id,
                LoginLog.logout_at.is_(None),
                func.date(LoginLog.login_at) == today,
            )
            has_login = (await db.execute(log_stmt)).scalars().first()
            if not has_login:
                db.add(LoginLog(
                    tenant_id=tenant_id,
                    user_id=cre_user.id,
                    login_at=now - timedelta(hours=2),
                    ip_address="127.0.0.1",
                    device_info="Chrome Playwright Test Runner",
                ))
        await db.flush()

        # 6. KPI Tags & Questionnaires
        kpis = ["workshop_quality", "advisor_courtesy", "cleanliness", "delivery_time", "transparency", "recommendation"]
        kpi_map = {}
        for k in kpis:
            stmt = select(KpiTag).where(KpiTag.tenant_id == tenant_id, KpiTag.tag == k)
            k_obj = (await db.execute(stmt)).scalar_one_or_none()
            if not k_obj:
                k_obj = KpiTag(tenant_id=tenant_id, tag=k, label=k.replace("_", " ").title())
                db.add(k_obj)
                await db.flush()
            kpi_map[k] = k_obj

        # Scales
        scale_stmt = select(RatingScale).where(RatingScale.tenant_id == tenant_id, RatingScale.name == "10-Star Hyundai Scale")
        h_scale = (await db.execute(scale_stmt)).scalar_one_or_none()
        if not h_scale:
            h_scale = RatingScale(tenant_id=tenant_id, brand_id=brands["HYUNDAI"].id, name="10-Star Hyundai Scale", max_rating=10, is_active=True)
            db.add(h_scale)
            await db.flush()
            db.add_all([
                RatingScaleBand(tenant_id=tenant_id, scale_id=h_scale.id, label="Delight", min_score=9, max_score=10, derived_case_status="Delight", is_delight=True),
                RatingScaleBand(tenant_id=tenant_id, scale_id=h_scale.id, label="Satisfied", min_score=8, max_score=8, derived_case_status="Satisfied"),
                RatingScaleBand(tenant_id=tenant_id, scale_id=h_scale.id, label="Non-Delight", min_score=6, max_score=7, derived_case_status="Non-Delight"),
                RatingScaleBand(tenant_id=tenant_id, scale_id=h_scale.id, label="Dissatisfied", min_score=1, max_score=5, derived_case_status="Dissatisfied"),
            ])
            await db.flush()

        # Programs (PSF & TNPS)
        psf_prog = (await db.execute(select(FollowUpProgram).where(FollowUpProgram.tenant_id == tenant_id, FollowUpProgram.code == "PSF"))).scalar_one_or_none()
        if not psf_prog:
            psf_prog = FollowUpProgram(
                tenant_id=tenant_id,
                brand_id=brands["HYUNDAI"].id,
                code="PSF",
                label="Post Service Follow-up",
                enabled=True,
                trigger="ON_IMPORT",
                channel="PHONE",
                max_attempts=3,
                retry_gap_hours=24,
                sla_hours=48,
                sort_order=1,
            )
            db.add(psf_prog)
            await db.flush()

        tnps_prog = (await db.execute(select(FollowUpProgram).where(FollowUpProgram.tenant_id == tenant_id, FollowUpProgram.code == "TNPS"))).scalar_one_or_none()
        if not tnps_prog:
            tnps_prog = FollowUpProgram(
                tenant_id=tenant_id,
                brand_id=brands["ATHER"].id,
                code="TNPS",
                label="Ather TNPS Follow-up",
                enabled=True,
                trigger="ON_IMPORT",
                channel="PHONE",
                max_attempts=3,
                retry_gap_hours=24,
                sla_hours=48,
                sort_order=2,
            )
            db.add(tnps_prog)
            await db.flush()

        # Questionnaire for Hyundai
        q_stmt = select(Questionnaire).where(Questionnaire.tenant_id == tenant_id, Questionnaire.type == "HYUNDAI_PSF")
        qnr = (await db.execute(q_stmt)).scalar_one_or_none()
        if not qnr:
            qnr = Questionnaire(
                tenant_id=tenant_id,
                brand_id=brands["HYUNDAI"].id,
                title="Hyundai Standard Service Survey",
                type="HYUNDAI_PSF",
                version=1,
                is_active=True,
            )
            db.add(qnr)
            await db.flush()
            # Questions
            db.add_all([
                Question(tenant_id=tenant_id, questionnaire_id=qnr.id, key="maintenance_repair_work", label="How would you rate the maintenance & repair work done on your vehicle?", type="RATING", answer_type="RATING", rating_min=1, rating_max=10, kpi_tag="workshop_quality", complaint_trigger_below=6.0, display_order=1),
                Question(tenant_id=tenant_id, questionnaire_id=qnr.id, key="cleanliness_on_return", label="How would you rate the condition and cleanliness of your vehicle upon return?", type="RATING", answer_type="RATING", rating_min=1, rating_max=10, kpi_tag="cleanliness", complaint_trigger_below=6.0, display_order=2),
                Question(tenant_id=tenant_id, questionnaire_id=qnr.id, key="advisor_explanation", label="Did the service advisor clearly explain the repair charges and work performed?", type="RATING", answer_type="RATING", rating_min=1, rating_max=10, kpi_tag="advisor_courtesy", complaint_trigger_below=6.0, display_order=3),
                Question(tenant_id=tenant_id, questionnaire_id=qnr.id, key="car_returned_same_day", label="Was your car returned on the promised time?", type="BOOLEAN", answer_type="YES_NO", kpi_tag="delivery_time", display_order=4),
                Question(tenant_id=tenant_id, questionnaire_id=qnr.id, key="recommend_dealer", label="How likely are you to recommend our workshop to friends and colleagues? (0-10)", type="RATING", answer_type="NPS_0_10", rating_min=0, rating_max=10, kpi_tag="recommendation", display_order=5),
            ])
            await db.flush()

        # Complaint Categories
        cat_names = [
            ("Wash Quality", "MEDIUM", 24),
            ("Delayed Delivery", "MEDIUM", 24),
            ("Billing Discrepancy", "HIGH", 12),
            ("Advisor Behaviour", "HIGH", 12),
            ("Parts Shortage", "MEDIUM", 48),
            ("AC Cooling Issue", "CRITICAL", 8),
        ]
        categories = {}
        for cname, csev, csla in cat_names:
            c_stmt = select(ComplaintCategory).where(ComplaintCategory.tenant_id == tenant_id, ComplaintCategory.name == cname)
            c_obj = (await db.execute(c_stmt)).scalar_one_or_none()
            if not c_obj:
                c_obj = ComplaintCategory(
                    tenant_id=tenant_id,
                    name=cname,
                    severity_level=csev,
                    default_sla_hours=csla,
                    is_active=True,
                )
                db.add(c_obj)
                await db.flush()
            categories[cname] = c_obj

        # 7. Check existing JobCards count for this tenant
        jc_count = (await db.execute(select(func.count(JobCard.id)).where(JobCard.tenant_id == tenant_id))).scalar() or 0
        if jc_count < 300:
            print(f"  • Generating 300 Job Cards (currently {jc_count})...")
            target_create = 300 - jc_count

            # Create an import batch
            batch = ImportBatch(
                tenant_id=tenant_id,
                uploaded_by=users["creadmin@demomotors.com"].id,
                brand_id=brands["HYUNDAI"].id,
                branch_id=branches["CW-HUB"].id,
                file_name="DMS_Demo_Import_November_2026.xlsx",
                status="COMPLETED",
                total_rows=target_create,
                processed_rows=target_create,
                success_rows=target_create,
            )
            db.add(batch)
            await db.flush()

            # Generate 300 customers, vehicles, job cards, followup queues
            created_jobcards = []
            for i in range(1, target_create + 1):
                idx = jc_count + i
                c_name = INDIAN_NAMES[(idx - 1) % len(INDIAN_NAMES)] + f" {idx}"
                raw_phone = f"+91 9845{idx:05d}"

                # Assign branch
                if idx <= 140:
                    branch = branches["CW-HUB"]
                    brand = brands["HYUNDAI"]
                    model = random.choice(HYUNDAI_MODELS)
                    prog = psf_prog
                elif idx <= 230:
                    branch = branches["NW-GAD"]
                    brand = brands["HYUNDAI"]
                    model = random.choice(HYUNDAI_MODELS)
                    prog = psf_prog
                else:
                    branch = branches["AS-BEL"]
                    brand = brands["ATHER"]
                    model = random.choice(ATHER_MODELS)
                    prog = tnps_prog

                # Customer
                cust = Customer(
                    tenant_id=tenant_id,
                    name=c_name,
                    phone=encrypt_phone(raw_phone),
                    phone_hash=hash_phone(raw_phone),
                    city=branch.city,
                )
                db.add(cust)
                await db.flush()

                # Vehicle
                veh = Vehicle(
                    tenant_id=tenant_id,
                    brand_id=brand.id,
                    customer_id=cust.id,
                    reg_no=f"KA-25-M-{1000 + idx}",
                    vin=f"VIN{brand.code[:3]}{idx:010d}",
                    model=model,
                )
                db.add(veh)
                await db.flush()

                # Job Card
                jc_date = today - timedelta(days=(idx % 14) + 1)
                amount = Decimal(random.randint(1850, 38500))
                # 50% of CW-HUB cards linked to Mahesh Joshi advisor
                advisor_link = users["advisor@demomotors.com"] if branch.code == "CW-HUB" and (idx % 2 == 0) else None

                jc = JobCard(
                    tenant_id=tenant_id,
                    brand_id=brand.id,
                    branch_id=branch.id,
                    customer_id=cust.id,
                    vehicle_id=veh.id,
                    import_batch_id=batch.id,
                    job_card_no=f"{branch.dms_code}_R2026_{idx:05d}",
                    job_card_date=jc_date,
                    service_advisor_name=advisor_link.full_name if advisor_link else "Praveen Shinde",
                    service_advisor_id=advisor_link.id if advisor_link else None,
                    service_type=random.choice(SERVICE_TYPES),
                    total_amount=amount,
                    odometer_reading=random.randint(12000, 65000),
                )
                db.add(jc)
                await db.flush()
                created_jobcards.append(jc)

                # Assign CRE rotation
                assigned_cre = cre_list[(idx - 1) % len(cre_list)]

                # Followup Queue Status distribution
                # 1..100 -> PENDING
                # 101..140 -> CALLBACK_REQUESTED (Call Later)
                # 141..260 -> CONTACTED (completed survey)
                # 261..290 -> NOT_CONTACTED (no response / busy)
                # 291..300 -> CLOSED_MAX_ATTEMPTS
                if idx <= 100:
                    q_status = "PENDING"
                    attempts_count = 0
                    due = now
                elif idx <= 140:
                    q_status = "CALLBACK_REQUESTED"
                    attempts_count = 1
                    due = now - timedelta(hours=4)
                elif idx <= 260:
                    q_status = "CONTACTED"
                    attempts_count = random.randint(1, 2)
                    due = now - timedelta(days=2)
                elif idx <= 290:
                    q_status = "NOT_CONTACTED"
                    attempts_count = 2
                    due = now - timedelta(days=1)
                else:
                    q_status = "CLOSED_MAX_ATTEMPTS"
                    attempts_count = 3
                    due = now - timedelta(days=3)

                fq = FollowupQueue(
                    tenant_id=tenant_id,
                    job_card_id=jc.id,
                    program_id=prog.id if prog else None,
                    queue_type=prog.code if prog else "PSF",
                    status=q_status,
                    assigned_to_id=assigned_cre.id,
                    due_at=due,
                    attempts=attempts_count,
                    contacted_count=1 if q_status == "CONTACTED" else 0,
                    completed_at=now if q_status in ["CONTACTED", "CLOSED_MAX_ATTEMPTS"] else None,
                )
                db.add(fq)
                await db.flush()

                # Add Call & Attempts if contacted or failed
                if q_status == "CONTACTED":
                    # Some low ratings to trigger complaints
                    is_unhappy = (idx % 12 == 0)
                    rating_val = random.randint(2, 4) if is_unhappy else random.randint(8, 10)
                    c_status = "Dissatisfied" if is_unhappy else ("Delight" if rating_val >= 9 else "Satisfied")

                    call_rec = Call(
                        tenant_id=tenant_id,
                        followup_queue_id=fq.id,
                        job_card_id=jc.id,
                        called_by_id=assigned_cre.id,
                        phone_dialed=encrypt_phone(raw_phone),
                        call_status="Connected",
                        case_status=c_status,
                        duration_seconds=random.randint(45, 180),
                        voc="Customer shared positive feedback about car cleanliness and service." if not is_unhappy else "Customer complained about billing and brake noise.",
                    )
                    db.add(call_rec)
                    await db.flush()

                    db.add(CallAttempt(
                        tenant_id=tenant_id,
                        followup_queue_id=fq.id,
                        attempt_number=1,
                        call_status="Connected",
                        case_status=c_status,
                        rating=rating_val,
                        called_by_id=assigned_cre.id,
                        duration_seconds=random.randint(45, 180),
                    ))

                    # Survey response
                    db.add(SurveyResponse(
                        tenant_id=tenant_id,
                        call_id=call_rec.id,
                        job_card_id=jc.id,
                        questionnaire_id=qnr.id,
                        questionnaire_version=1,
                        csat_score=Decimal(rating_val * 10),
                        nps_score=rating_val,
                        nps_category="DETRACTOR" if rating_val <= 6 else ("PROMOTER" if rating_val >= 9 else "PASSIVE"),
                        answers={
                            "maintenance_repair_work": {"value": rating_val, "score": rating_val * 10},
                            "cleanliness_on_return": {"value": rating_val, "score": rating_val * 10},
                            "car_returned_same_day": {"value": "Yes", "score": 100},
                        },
                    ))

                elif q_status == "CALLBACK_REQUESTED":
                    db.add(CallAttempt(
                        tenant_id=tenant_id,
                        followup_queue_id=fq.id,
                        attempt_number=1,
                        call_status="Not Connected",
                        case_status="Call Later",
                        called_by_id=assigned_cre.id,
                    ))
                    db.add(Reminder(
                        tenant_id=tenant_id,
                        followup_queue_id=fq.id,
                        assigned_to_id=assigned_cre.id,
                        remind_at=now + timedelta(hours=3),
                        note="Customer in meeting, requested callback after 4 PM.",
                    ))

                elif q_status in ["NOT_CONTACTED", "CLOSED_MAX_ATTEMPTS"]:
                    for att in range(1, attempts_count + 1):
                        db.add(CallAttempt(
                            tenant_id=tenant_id,
                            followup_queue_id=fq.id,
                            attempt_number=att,
                            call_status="Not Connected",
                            case_status="No Response" if att % 2 == 1 else "Switched Off",
                            called_by_id=assigned_cre.id,
                        ))

            await db.flush()
            print("  ✓ 300 Job cards and follow-up queues generated.")

        # 8. Seed 20 Complaints in various states
        comp_count = (await db.execute(select(func.count(Complaint.id)).where(Complaint.tenant_id == tenant_id))).scalar() or 0
        if comp_count < 20:
            print(f"  • Generating 20 complaints (currently {comp_count})...")
            # Get job cards in CW-HUB
            jc_stmt = select(JobCard).where(JobCard.tenant_id == tenant_id).limit(30)
            sample_jcs = (await db.execute(jc_stmt)).scalars().all()

            cat_keys = list(categories.keys())
            statuses = [
                ("Open", 6),
                ("In Progress", 5),
                ("Resolved", 5),
                ("Closed in Time", 4),
            ]

            comp_idx = comp_count + 1
            for st_name, count in statuses:
                for _ in range(count):
                    if comp_idx > 20:
                        break
                    jc = sample_jcs[(comp_idx - 1) % len(sample_jcs)]
                    cat_name = cat_keys[(comp_idx - 1) % len(cat_keys)]
                    cat = categories[cat_name]
                    desc_text = COMPLAINT_DESCRIPTIONS[(comp_idx - 1) % len(COMPLAINT_DESCRIPTIONS)][1]

                    c_no = f"CMP-2026-{comp_idx:04d}"
                    sla_due = now + timedelta(hours=cat.default_sla_hours) if st_name == "Open" else (now - timedelta(hours=5))

                    complaint = Complaint(
                        tenant_id=tenant_id,
                        branch_id=jc.branch_id,
                        job_card_id=jc.id,
                        category_id=cat.id,
                        complaint_no=c_no,
                        severity=cat.severity_level,
                        status=st_name,
                        description=desc_text,
                        assigned_to_id=users["manager@demomotors.com"].id if st_name != "Open" else users["advisor@demomotors.com"].id,
                        sla_due_at=sla_due,
                        is_sla_breached=(st_name == "Open" and comp_idx % 2 == 0),
                        resolution_remarks="Root cause investigated: parts delayed. Free car wash and coupon provided to customer." if st_name in ["Resolved", "Closed in Time"] else None,
                        resolved_by_id=users["manager@demomotors.com"].id if st_name in ["Resolved", "Closed in Time"] else None,
                    )
                    db.add(complaint)
                    await db.flush()

                    # Add event history
                    db.add(ComplaintEvent(
                        tenant_id=tenant_id,
                        complaint_id=complaint.id,
                        event_type="CREATED",
                        performed_by_id=users["cre1@demomotors.com"].id,
                        remarks="Complaint logged via post-service follow-up call.",
                    ))

                    if st_name in ["In Progress", "Resolved", "Closed in Time"]:
                        db.add(ComplaintEvent(
                            tenant_id=tenant_id,
                            complaint_id=complaint.id,
                            event_type="ASSIGNED",
                            performed_by_id=users["manager@demomotors.com"].id,
                            remarks="Contacted customer, acknowledged grievance, scheduled workshop re-inspection.",
                        ))

                    if st_name in ["Resolved", "Closed in Time"]:
                        db.add(ComplaintEvent(
                            tenant_id=tenant_id,
                            complaint_id=complaint.id,
                            event_type="RESOLVED",
                            performed_by_id=users["manager@demomotors.com"].id,
                            remarks="Customer satisfied after rectification. Closed complaint.",
                        ))
                    
                    if st_name == "Closed in Time":
                        db.add(Reconfirmation(
                            tenant_id=tenant_id,
                            complaint_id=complaint.id,
                            conducted_by_id=users["cre1@demomotors.com"].id,
                            status="SATISFIED_CLOSED",
                            call_status="Connected",
                            customer_feedback="Customer confirmed vehicle is running smoothly and grievance is resolved.",
                            closure_verified=True,
                        ))

                    comp_idx += 1

            await db.flush()
            print("  ✓ 20 Complaints generated across Open, In Progress, Resolved, and Closed states.")

        await db.commit()
        print("🎉 Demo data seeding completed successfully!")
        print("\nDemo Credentials:")
        print("  Super Admin:    superadmin@demomotors.com   / Admin@12345")
        print("  CRE Admin:      creadmin@demomotors.com     / Password@12345")
        print("  CRE 1:          cre1@demomotors.com         / Password@12345")
        print("  CRE 2:          cre2@demomotors.com         / Password@12345")
        print("  CRE 3:          cre3@demomotors.com         / Password@12345")
        print("  Branch Manager: manager@demomotors.com      / Password@12345  (Central Workshop Hubli)")
        print("  Service Advisor: advisor@demomotors.com     / Password@12345  (Central Workshop Hubli)")


if __name__ == "__main__":
    asyncio.run(seed_demo())
