#!/usr/bin/env python3
"""
Legacy Data Importer for PSF Platform
Imports the 120-column AppSheet CSV export into PostgreSQL.
Supports:
- CLI options: --file, --dry-run, --tenant-slug
- Phone encryption and hashing
- Automatic branch DMS code matching (e.g. S8211 -> Hubli, S8827 -> Gadag)
- Attempt log reconstruction from Total Attempted / Contacted counters
- Normalized survey responses (Yes/No and 1-10) with JSONB storage
- Complaint creation with closure remarks and audit trail
- Idempotent re-runs (dedupe on branch_id + job_card_no)
- Inactive placeholder user creation for unknown CREs / closers
- Dropped columns tracking and reporting
"""

import argparse
import asyncio
import csv
import os
import re
import sys
import uuid
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import select, func, and_
from app.core.database import AsyncSessionLocal
from app.core.crypto import encrypt_phone, hash_phone, uuid7
from app.core.security import get_password_hash
from app.models.tenant import Tenant, Brand, Branch, Setting
from app.models.auth import Role, User, UserScope
from app.models.customer import Customer, Vehicle
from app.models.service import JobCard, ImportBatch
from app.models.followup import FollowupQueue, CallAttempt, Call, CallStatus, CaseStatus, SurveyResponse
from app.models.complaint import Complaint, ComplaintCategory, ComplaintEvent
from app.models.questionnaire import Questionnaire, Question
from app.services.rating_service import derive_case_status_memory

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

# Columns to explicitly drop
DROPPED_COLUMNS = [
    "Brand Logo",
    "Update Changes",
    "Closure Doc",
    "Ather Docs",
    "Document (TNPS)",
    "8",
    "9",
]

# Hyundai Survey Question Column Mappings
HYUNDAI_QUESTION_MAP = {
    # 21 Yes/No
    "Whether You Have Availed Pick & Drop Facility? (Yes/No)": "availed_pick_drop",
    "Were You Offered Pick Up and Drop or Not?": "offered_pick_drop",
    "Were You Contacted by the Workshop Staff for Feedback After Delivery of Vehicle? (Yes/No/Not Aware)": "contacted_feedback_post_delivery",
    "Whether the Service Advisor Has Opened the Repair Order Through Tablet Device?": "opened_ro_via_tablet",
    "How Do You Rate Courtesy & Behaviour of the Person Who Came to Pick & Drop Your Vehicle?": "pick_drop_staff_courtesy",
    "Whether the Repair Charges Explained to You Were Reasonable With Respect to Work Done on Your Car?": "charges_explained_reasonable",
    "Basis Your Last Service Experience, How Strongly Would You Recommend the Dealer to Your Friends, Relatives, or Colleagues?": "recommend_dealer_friends",
    "Did the Service Advisor Offer You the Road Test of Your Car Before Opening the Repair Order (Job Card)?": "road_test_before_ro",
    "Did the Service Advisor Offer You a Road Test Before Delivery After Getting the Vehicle Serviced?": "road_test_before_delivery",
    "Did the Service Advisor Check the Maintenance History of Your Vehicle?": "checked_maintenance_history",
    "Did the Service Advisor Conduct the Vehicle Inspection in Front of You?": "inspection_in_front_of_customer",
    "Did You Get the Regular Update on WhatsApp Group for Your Vehicle Status?": "whatsapp_status_updates",
    "Were You Offered Water Bottle During Your Visit to the Workshop? (Yes/No/Not Aware/NA)": "offered_water_bottle",
    "Did the Service Advisor Explain the Parts Repaired and Work Performed?": "explained_parts_repaired_work",
    "After Completion of the Service or Repair, Did You Receive Your Car Back on the Same Day?": "car_returned_same_day",
    "Was the Service Advisor Polite and Courteous During Interaction?": "advisor_polite_courteous",
    "Was the Restroom Maintained Neat and Clean?": "restroom_neat_clean",
    "How Would You Rate the Workshop Support for Insurance Claim Processing?": "insurance_claim_support_rating",
    "Did You Get the Proper Response from Dealer Staff When You Visited the Workshop?": "proper_response_dealer_staff",
    "Did the Service Advisor Explain the Parts Replaced and Charges Taken at the Time of Delivery?": "explained_parts_replaced_charges",
    "Did the Service Advisor Walk You Out With the Statement Enjoy Your Driving with Hyundai?": "walk_out_hyundai_statement",
    # 10 Ratings
    "How Would You Rate the Maintenance & Repair Work Done on Your Car?": "rating_maintenance_repair_work",
    "How Would You Rate the Condition or Cleanliness of Your Car, on Return?": "rating_cleanliness_on_return",
    "How Would You Rate the Explanation Given by Service Advisor on the Work Done of Your Car?": "rating_explanation_by_advisor",
    "How Would You Rate Your Overall Interaction & Experience with Workshop?": "rating_overall_interaction_experience",
    "Whether the Vehicle Was Picked & Dropped as per Committed Time?": "rating_pick_drop_committed_time",
    "How Would You Rate the Service Delivery Process of Your Car After Servicing?": "rating_service_delivery_process",
    "How Would You Rate the Overall Cleanliness of Dealer Facility?": "rating_cleanliness_dealer_facility",
    "How Would You Rate the Quality of Denting, Painting and Finishing of Repairs Carried Out in the Car?": "rating_denting_painting_quality",
    "How Would You Rate the Ambience and Hygiene of Customer Interaction Area in the Workshop?": "rating_ambience_hygiene_customer_area",
    "Did the Service Advisor Inform You About the Promised Delivery Date and Time of Your Car?": "rating_informed_promised_delivery_time",
}


def parse_date(val: Optional[str]) -> Optional[date]:
    if not val or not val.strip():
        return None
    val = val.strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val or not val.strip():
        return None
    val = val.strip()
    for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(val, fmt)
            return dt.replace(tzinfo=KOLKATA_TZ)
        except ValueError:
            continue
    return None


def normalize_answer(val: Optional[str]) -> Optional[Any]:
    if val is None:
        return None
    val_str = str(val).strip()
    if not val_str:
        return None
    lower = val_str.lower()
    if lower in ("yes", "y", "true"):
        return "Yes"
    if lower in ("no", "n", "false"):
        return "No"
    if lower in ("na", "n/a", "not aware", "not aware/"):
        return "Not Aware"
    # Try integer parse
    try:
        return int(val_str)
    except ValueError:
        return val_str


class LegacyImporter:
    def __init__(self, file_path: str, tenant_slug: str = "apex-auto", dry_run: bool = False):
        self.file_path = file_path
        self.tenant_slug = tenant_slug
        self.dry_run = dry_run
        self.dropped_columns_found = []
        self.report = {
            "total_rows": 0,
            "job_cards_created": 0,
            "job_cards_skipped_duplicate": 0,
            "complaints_created": 0,
            "call_attempts_created": 0,
            "unknown_branches": [],
            "unknown_users": [],
            "unknown_categories": [],
            "missing_contacts": [],
            "errors": [],
        }

    async def run(self):
        print(f"==================================================")
        print(f"🚀 PSF Legacy Data Importer")
        print(f"   File: {self.file_path}")
        print(f"   Tenant: {self.tenant_slug}")
        print(f"   Mode: {'DRY RUN (No changes will be saved)' if self.dry_run else 'LIVE COMMIT'}")
        print(f"==================================================")

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")

        async with AsyncSessionLocal() as db:
            # 1. Load Tenant
            t_stmt = select(Tenant).where(Tenant.slug == self.tenant_slug)
            tenant = (await db.execute(t_stmt)).scalar_one_or_none()
            if not tenant:
                raise ValueError(f"Tenant not found for slug: {self.tenant_slug}")

            # 2. Cache Brands
            brands_res = await db.execute(select(Brand).where(Brand.tenant_id == tenant.id))
            brands_list = brands_res.scalars().all()
            brands_by_code = {b.code.upper(): b for b in brands_list}
            brands_by_name = {b.name.upper(): b for b in brands_list}

            # 3. Cache Branches (by dms_code, name, display_name)
            branches_res = await db.execute(select(Branch).where(Branch.tenant_id == tenant.id))
            branches_list = branches_res.scalars().all()
            branches_by_name = {b.name.strip().upper(): b for b in branches_list}
            branches_by_dms = {b.dms_code.strip().upper(): b for b in branches_list if b.dms_code}

            # 4. Cache Users & Roles
            roles_res = await db.execute(select(Role).where((Role.tenant_id == tenant.id) | (Role.tenant_id == None)))
            roles_by_name = {r.name: r for r in roles_res.scalars().all()}
            cre_role = roles_by_name.get("CRE")
            service_mgr_role = roles_by_name.get("SERVICE_MANAGER") or roles_by_name.get("BRANCH_MANAGER")

            users_res = await db.execute(select(User).where(User.tenant_id == tenant.id))
            users_list = users_res.scalars().all()
            users_by_name = {u.full_name.strip().upper(): u for u in users_list}

            # 5. Cache Complaint Categories
            cat_res = await db.execute(select(ComplaintCategory).where(ComplaintCategory.tenant_id == tenant.id))
            cat_list = cat_res.scalars().all()
            categories_by_label = {}
            for c in cat_list:
                if c.legacy_label:
                    categories_by_label[c.legacy_label.strip().upper()] = c
                categories_by_label[c.name.strip().upper()] = c

            # 6. Cache Hyundai Questionnaire
            hyundai_brand = brands_by_code.get("HYUN")
            qn = None
            if hyundai_brand:
                qn_stmt = select(Questionnaire).where(
                    Questionnaire.tenant_id == tenant.id,
                    Questionnaire.brand_id == hyundai_brand.id,
                    Questionnaire.type == "PSF",
                )
                qn = (await db.execute(qn_stmt)).scalar_one_or_none()

            # Helper for branch lookup
            def resolve_branch(br_name: str, jc_no: str) -> Optional[Branch]:
                if jc_no and "_" in jc_no:
                    prefix = jc_no.split("_")[0].strip().upper()
                    if prefix in branches_by_dms:
                        return branches_by_dms[prefix]
                if br_name and br_name.strip().upper() in branches_by_name:
                    return branches_by_name[br_name.strip().upper()]
                # Check for Hubli vs Gadag heuristic
                if "HUBLI" in (br_name or "").upper():
                    return branches_by_dms.get("S8211") or branches_by_name.get("HYUNDAI HUBLI")
                if "GADAG" in (br_name or "").upper():
                    return branches_by_dms.get("S8827") or branches_by_name.get("HYUNDAI GADAG")
                return None

            # Helper for user lookup or placeholder creation
            async def get_or_create_user(name: str, role_obj: Role) -> User:
                name_clean = name.strip()
                name_upper = name_clean.upper()
                if name_upper in users_by_name:
                    return users_by_name[name_upper]

                # Create inactive placeholder user
                slug = re.sub(r'[^a-zA-Z0-9]+', '.', name_clean.lower()).strip('.')
                placeholder_email = f"{slug}@placeholder.apexauto.com"
                placeholder_phone = f"00000{len(users_by_name)+1:05d}"

                user = User(
                    tenant_id=tenant.id,
                    role_id=role_obj.id if role_obj else None,
                    email=placeholder_email,
                    hashed_password=get_password_hash("Placeholder@123"),
                    full_name=name_clean,
                    employee_id=f"PH-{len(users_by_name)+1:04d}",
                    phone=encrypt_phone(placeholder_phone),
                    phone_hash=hash_phone(placeholder_phone),
                    is_active=False, # Inactive placeholder user
                )
                db.add(user)
                await db.flush()
                users_by_name[name_upper] = user
                self.report["unknown_users"].append(f"{name_clean} (created inactive placeholder {placeholder_email})")
                return user

            # Find default uploader (Admin User)
            admin_user = (await db.execute(select(User).where(User.tenant_id == tenant.id, User.is_active == True))).scalars().first()

            # 7. Create ImportBatch
            batch = ImportBatch(
                tenant_id=tenant.id,
                uploaded_by=admin_user.id if admin_user else None,
                brand_id=hyundai_brand.id if hyundai_brand else None,
                file_name=os.path.basename(self.file_path),
                file_url=self.file_path,
                total_rows=0,
                processed_rows=0,
                success_rows=0,
                error_rows=0,
                status="PROCESSING",
            )
            if not self.dry_run:
                db.add(batch)
                await db.flush()

            # 8. Read and Process CSV
            with open(self.file_path, mode="r", encoding="utf-8", errors="ignore") as infile:
                reader = csv.DictReader(infile)
                headers = reader.fieldnames or []

                # Track dropped columns
                for h in headers:
                    h_clean = h.strip()
                    if h_clean in DROPPED_COLUMNS or not h_clean:
                        if h_clean not in self.dropped_columns_found:
                            self.dropped_columns_found.append(h_clean if h_clean else "(empty column header)")

                rows = list(reader)
                self.report["total_rows"] = len(rows)
                if not self.dry_run:
                    batch.total_rows = len(rows)

                for idx, row in enumerate(rows, start=1):
                    try:
                        async with db.begin_nested():
                            jc_no = (row.get("Job Card No") or "").strip()
                            if not jc_no:
                                self.report["errors"].append(f"Row {idx}: Missing Job Card No")
                                continue

                            br_str = (row.get("Branch") or "").strip()
                            branch = resolve_branch(br_str, jc_no)
                            if not branch:
                                self.report["unknown_branches"].append(f"Row {idx}: {br_str} (JC: {jc_no})")
                                self.report["errors"].append(f"Row {idx}: Unknown branch '{br_str}'")
                                continue

                            # Check for branch contact
                            if branch.phone is None:
                                if branch.name not in self.report["missing_contacts"]:
                                    self.report["missing_contacts"].append(branch.name)

                            # Check idempotency: Dedupe on (branch_id, job_card_no)
                            existing_jc_stmt = select(JobCard).where(
                                JobCard.tenant_id == tenant.id,
                                JobCard.branch_id == branch.id,
                                JobCard.job_card_no == jc_no,
                            )
                            existing_jc = (await db.execute(existing_jc_stmt)).scalar_one_or_none()
                            if existing_jc:
                                self.report["job_cards_skipped_duplicate"] += 1
                                continue

                            # Brand resolution
                            brand = branch.brand or brands_by_name.get((row.get("Brand") or "").upper()) or hyundai_brand

                            # Customer resolution / creation
                            cust_name = (row.get("Customer Name") or "Unknown Customer").strip()
                            cust_phone = (row.get("Contact Number") or "0000000000").strip()
                            alt_phone = (row.get("Alt Contact Number") or "").strip()
                            phone_h = hash_phone(cust_phone)

                            cust_stmt = select(Customer).where(
                                Customer.tenant_id == tenant.id,
                                Customer.phone_hash == phone_h,
                            )
                            customer = (await db.execute(cust_stmt)).scalar_one_or_none()
                            if not customer:
                                customer = Customer(
                                    tenant_id=tenant.id,
                                    name=cust_name,
                                    phone=encrypt_phone(cust_phone),
                                    phone_hash=phone_h,
                                    alt_phone=encrypt_phone(alt_phone) if alt_phone else None,
                                )
                                db.add(customer)
                                await db.flush()

                            # Vehicle resolution / creation
                            reg_no = (row.get("Reg No") or "").strip()
                            vin = (row.get("Vin No") or "").strip()
                            model_name = (row.get("Model") or "Unknown").strip()

                            veh_stmt = select(Vehicle).where(
                                Vehicle.tenant_id == tenant.id,
                                (Vehicle.reg_no == reg_no) if reg_no else (Vehicle.vin == vin),
                            )
                            vehicle = (await db.execute(veh_stmt)).scalar_one_or_none()
                            if not vehicle:
                                vehicle = Vehicle(
                                    tenant_id=tenant.id,
                                    brand_id=brand.id if brand else None,
                                    customer_id=customer.id,
                                    reg_no=reg_no if reg_no else None,
                                    vin=vin if vin else None,
                                    model=model_name,
                                )
                                db.add(vehicle)
                                await db.flush()

                            # Parse Dates
                            jc_date = parse_date(row.get("Job Card Date")) or date.today()
                            calling_date = parse_date(row.get("Calling Date"))
                            followup_dt = parse_datetime(row.get("Followup Timestamp")) or datetime.now(KOLKATA_TZ)
                            due_datetime = datetime.combine(calling_date or jc_date, datetime.min.time(), tzinfo=KOLKATA_TZ)
                            tnps_dt = parse_date(row.get("TNPS Date"))

                            # Service Advisor & Technician
                            sa_name = (row.get("Service Advisor") or "").strip()
                            tech_name = (row.get("Technician") or "").strip()
                            srv_type = (row.get("Service Type") or "").strip()
                            srv_amount_str = (row.get("Total Service Amount") or "0").replace(",", "").strip()
                            try:
                                srv_amount = float(srv_amount_str)
                            except ValueError:
                                srv_amount = 0.0

                            # Create JobCard
                            job_card = JobCard(
                                tenant_id=tenant.id,
                                brand_id=brand.id if brand else None,
                                branch_id=branch.id,
                                customer_id=customer.id,
                                vehicle_id=vehicle.id,
                                import_batch_id=batch.id if not self.dry_run else None,
                                job_card_no=jc_no,
                                job_card_date=jc_date,
                                service_advisor_name=sa_name if sa_name else None,
                                technician_name=tech_name if tech_name else None,
                                service_type=srv_type if srv_type else None,
                                total_amount=srv_amount,
                            )
                            db.add(job_card)
                            await db.flush()
                            self.report["job_cards_created"] += 1

                            # Resolve CRE User
                            cre_name = (row.get("Followed By") or row.get("Name of CRE") or "Priya Sharma").strip()
                            cre_user = await get_or_create_user(cre_name, cre_role)

                            # Parse Counters & Statuses
                            att_str = (row.get("Total Attempted") or "1").strip()
                            cont_str = (row.get("Total Contacted") or "0").strip()
                            try:
                                total_attempted = max(1, int(att_str))
                            except ValueError:
                                total_attempted = 1
                            try:
                                total_contacted = max(0, int(cont_str))
                            except ValueError:
                                total_contacted = 0

                            call_status_raw = (row.get("Call Status") or "Connected").strip()
                            case_status_raw = (row.get("Case Status") or "Delight").strip()
                            voc_raw = (row.get("VOC") or "").strip()

                            # Determine queue status
                            if case_status_raw == "No Response" or total_contacted == 0:
                                queue_status = "NOT_CONTACTED"
                            else:
                                queue_status = "CONTACTED"

                            # Create FollowupQueue
                            queue = FollowupQueue(
                                tenant_id=tenant.id,
                                job_card_id=job_card.id,
                                queue_type="PSF",
                                status=queue_status,
                                assigned_to_id=cre_user.id if cre_user else None,
                                due_at=due_datetime,
                                scheduled_tnps_date=tnps_dt,
                                attempts=total_attempted,
                                contacted_count=total_contacted,
                                last_attempt_at=followup_dt,
                                completed_at=followup_dt if queue_status == "CONTACTED" else None,
                            )
                            db.add(queue)
                            await db.flush()

                            # Rebuild CallAttempts
                            for att_num in range(1, total_attempted + 1):
                                is_last = (att_num == total_attempted)
                                if is_last:
                                    c_stat = call_status_raw
                                    cs_stat = case_status_raw
                                    voc_val = voc_raw
                                    c_time = followup_dt
                                else:
                                    c_stat = "Not Connected"
                                    cs_stat = "No Response" if total_contacted == 0 else "Call Later"
                                    voc_val = None
                                    c_time = followup_dt

                                attempt = CallAttempt(
                                    tenant_id=tenant.id,
                                    followup_queue_id=queue.id,
                                    attempt_number=att_num,
                                    call_status=c_stat,
                                    case_status=cs_stat,
                                    voc=voc_val,
                                    called_by_id=cre_user.id if cre_user else None,
                                    called_at=c_time,
                                    duration_seconds=60 if c_stat == "Connected" else 0,
                                )
                                db.add(attempt)
                                self.report["call_attempts_created"] += 1

                            # Create Call record for the primary conversation
                            call = Call(
                                tenant_id=tenant.id,
                                followup_queue_id=queue.id,
                                job_card_id=job_card.id,
                                called_by_id=cre_user.id if cre_user else None,
                                called_at=followup_dt,
                                duration_seconds=90 if total_contacted > 0 else 0,
                                phone_dialed=cust_phone,
                                call_status=call_status_raw,
                                case_status=case_status_raw,
                                voc=voc_raw if voc_raw else None,
                            )
                            db.add(call)
                            await db.flush()

                            # Survey Responses (JSONB by question key)
                            survey_answers = {}
                            raw_rating_val = None
                            for col_name, q_key in HYUNDAI_QUESTION_MAP.items():
                                if col_name in row and row[col_name] is not None:
                                    norm_val = normalize_answer(row[col_name])
                                    if norm_val is not None:
                                        survey_answers[q_key] = norm_val
                                        if isinstance(norm_val, int) and raw_rating_val is None:
                                            raw_rating_val = norm_val

                            # Determine channel: WhatsApp or Phone
                            comp_cat_str = (row.get("Complaint Categories") or "").strip()
                            channel = "WHATSAPP" if ("WATSAPP" in comp_cat_str.upper() or "whatsapp" in voc_raw.lower()) else "PHONE"

                            if survey_answers and qn:
                                sr = SurveyResponse(
                                    tenant_id=tenant.id,
                                    call_id=call.id,
                                    job_card_id=job_card.id,
                                    questionnaire_id=qn.id,
                                    answers=survey_answers,
                                    channel=channel,
                                    raw_rating=raw_rating_val,
                                    csat_score=raw_rating_val,
                                )
                                db.add(sr)

                            # Complaint Processing
                            complaint_desc = (row.get("Complaints") or "").strip()
                            has_complaint = bool(complaint_desc) or (comp_cat_str and comp_cat_str != "NO COMPLAINT")

                            if has_complaint:
                                # Clean category label from emojis
                                cat_clean = re.sub(r'[^\w\s<=]+', '', comp_cat_str).strip().upper()
                                cat_obj = categories_by_label.get(comp_cat_str.upper()) or categories_by_label.get(cat_clean)
                                if not cat_obj:
                                    for k, c_candidate in categories_by_label.items():
                                        if cat_clean and (cat_clean in k or k in cat_clean):
                                            cat_obj = c_candidate
                                            break
                                if not cat_obj:
                                    cat_obj = categories_by_label.get("OTHER COMPLAINT") or list(categories_by_label.values())[0]

                                # Closer resolution (e.g. Deepa Hiremath)
                                closer_name = (row.get("Updated By") or "Deepa Hiremath").strip()
                                closer_user = await get_or_create_user(closer_name, service_mgr_role)

                                closure_remarks = (row.get("Complaint Closure") or "").strip()
                                current_status_raw = (row.get("Current Status") or "Closed in Time").strip()
                                updated_dt = parse_datetime(row.get("Updated Timestamp")) or followup_dt

                                sla_hours = cat_obj.default_sla_hours if (cat_obj and cat_obj.default_sla_hours is not None) else 24
                                sla_due_at = followup_dt + timedelta(hours=sla_hours)
                                is_breached = (updated_dt > sla_due_at) if updated_dt and sla_due_at else False

                                complaint = Complaint(
                                    tenant_id=tenant.id,
                                    branch_id=branch.id,
                                    job_card_id=job_card.id,
                                    call_id=call.id,
                                    category_id=cat_obj.id,
                                    complaint_no=f"CMP-{jc_no}",
                                    severity="HIGH" if "MECHANICAL" in comp_cat_str.upper() else "MEDIUM",
                                    status=current_status_raw,
                                    description=complaint_desc if complaint_desc else f"Customer Complaint - {comp_cat_str}",
                                    assigned_to_id=closer_user.id if closer_user else None,
                                    sla_due_at=sla_due_at,
                                    is_sla_breached=is_breached,
                                    resolution_remarks=closure_remarks if closure_remarks else None,
                                    resolved_by_id=closer_user.id if closer_user else None,
                                    resolved_at=updated_dt,
                                    closed_by_id=closer_user.id if closer_user else None,
                                    closed_at=updated_dt,
                                )
                                db.add(complaint)
                                await db.flush()

                                # Create ComplaintEvent audit trail (CREATED then RESOLVED_AND_CLOSED)
                                created_dt = min(followup_dt, updated_dt) - timedelta(seconds=1)
                                create_event = ComplaintEvent(
                                    tenant_id=tenant.id,
                                    complaint_id=complaint.id,
                                    performed_by_id=cre_user.id if cre_user else closer_user.id,
                                    event_type="CREATED",
                                    from_status=None,
                                    to_status="OPEN",
                                    remarks=f"Complaint recorded from legacy PSF import: {complaint_desc or comp_cat_str}",
                                    created_at=created_dt,
                                )
                                db.add(create_event)

                                event = ComplaintEvent(
                                    tenant_id=tenant.id,
                                    complaint_id=complaint.id,
                                    performed_by_id=closer_user.id if closer_user else None,
                                    event_type="RESOLVED_AND_CLOSED",
                                    from_status="OPEN",
                                    to_status=current_status_raw,
                                    remarks=closure_remarks if closure_remarks else f"Closed via legacy import: {current_status_raw}",
                                    created_at=updated_dt,
                                )
                                db.add(event)
                                self.report["complaints_created"] += 1

                    except Exception as exc:
                        self.report["errors"].append(f"Row {idx} ({row.get('Job Card No')}): {str(exc)}")

            if self.dry_run:
                await db.rollback()
                print("\n[INFO] Dry-run complete. Database rollback executed successfully (0 rows written).")
            else:
                if batch:
                    batch.processed_rows = self.report["total_rows"]
                    batch.success_rows = self.report["job_cards_created"]
                    batch.error_rows = len(self.report["errors"])
                    batch.status = "COMPLETED" if len(self.report["errors"]) == 0 else "COMPLETED_WITH_ERRORS"
                await db.commit()
                print("\n[SUCCESS] Import committed to database successfully!")

        self.print_summary()

    def print_summary(self):
        print("\n" + "=" * 50)
        print("📊 LEGACY IMPORT REPORT & VALIDATION SUMMARY")
        print("=" * 50)
        print(f"Total Rows Processed:        {self.report['total_rows']}")
        print(f"Job Cards Created:           {self.report['job_cards_created']}")
        print(f"Job Cards Skipped (Dupe):    {self.report['job_cards_skipped_duplicate']}")
        print(f"Call Attempts Created:       {self.report['call_attempts_created']}")
        print(f"Complaints Created:          {self.report['complaints_created']}")
        print(f"Errors Encountered:          {len(self.report['errors'])}")

        print("\n🚫 DROPPED COLUMNS:")
        for col in self.dropped_columns_found:
            print(f"  • {col}")

        if self.report["unknown_users"]:
            print(f"\n👤 INACTIVE PLACEHOLDER USERS CREATED ({len(self.report['unknown_users'])}):")
            for u in set(self.report["unknown_users"]):
                print(f"  • {u}")

        if self.report["missing_contacts"]:
            print(f"\n⚠️  BRANCHES WITH MISSING SERVICE CONTACT ({len(self.report['missing_contacts'])}):")
            for br in self.report["missing_contacts"]:
                print(f"  • {br}")

        if self.report["errors"]:
            print(f"\n❌ ROW ERRORS ({len(self.report['errors'])}):")
            for err in self.report["errors"][:10]:
                print(f"  • {err}")
            if len(self.report["errors"]) > 10:
                print(f"  ... and {len(self.report['errors'])-10} more errors.")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Import legacy 120-column PSF CSV")
    parser.add_argument("--file", required=True, help="Path to legacy CSV file")
    parser.add_argument("--tenant", default="apex-auto", help="Tenant slug (default: apex-auto)")
    parser.add_argument("--dry-run", action="store_true", help="Perform validation dry-run without committing changes")
    args = parser.parse_args()

    importer = LegacyImporter(file_path=args.file, tenant_slug=args.tenant, dry_run=args.dry_run)
    asyncio.run(importer.run())


if __name__ == "__main__":
    main()
