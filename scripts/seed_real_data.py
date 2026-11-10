import asyncio
import uuid
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.core.crypto import encrypt_phone, hash_phone
from app.models.tenant import Tenant, Brand, Branch, BranchContact
from app.models.auth import Role, User, UserScope
from app.models.complaint import ComplaintCategory
from app.models.followup import CallStatus, CaseStatus
from app.models.additional import RatingScale, RatingScaleBand
from app.models.questionnaire import Questionnaire, Question


# 21 Hyundai Yes/No Questions (de-duplicated)
HYUNDAI_YES_NO_QUESTIONS = [
    ("Whether you have availed Pick & Drop Facility? - YES / NO", "availed_pick_drop", "Pick & Drop Facility Availed"),
    ("Were you offered pick up and Drop or not?", "offered_pick_drop", "Offered Pick & Drop"),
    ("Were you contacted by the workshop Staff for feedback after the delivery of vehicle?(Yes/No/Not Aware/)", "contacted_feedback_post_delivery", "Post-Delivery Feedback Call"),
    ("Whether the Service Advisor has opened the Repair Order through Tablet Device?", "opened_ro_via_tablet", "Repair Order Opened via Tablet"),
    ("How do your rate Courtesy & behaviour of the person who came to pick & drop your vehicle?", "pick_drop_staff_courtesy", "Pick & Drop Staff Courtesy"),
    ("Whether the repair charges explained to you were reasoble with respect to work done on your car?", "charges_explained_reasonable", "Repair Charges Explained Reasonable"),
    ("Basis your last service experience How strongly would you recommend to Dealer to your friends, relatives, or colleagues?", "recommend_dealer_friends", "Recommend Dealer to Friends & Family"),
    ("Did the service advisor offer you the road test of your car before opening the repair order/(Job Card)?", "road_test_before_ro", "Pre-Service Road Test Offered"),
    ("Did the service advisor offer you a road test before delivery after getting the vehicle serviced?", "road_test_before_delivery", "Post-Service Road Test Offered"),
    ("Did the service advisor check the maintence history of your vehicle?", "checked_maintenance_history", "Maintenance History Checked"),
    ("Did the service advisor conduct the vehicle inspection in front of you?", "inspection_in_front_of_customer", "Vehicle Inspection in Customer Presence"),
    ("Did you get the regular update on whats app group for your vehicle status?", "whatsapp_status_updates", "Regular WhatsApp Status Updates"),
    ("Were you offered water bottle during your visit to the workshop?(Yes/No/Not Aware/", "offered_water_bottle", "Water Bottle Offered at Workshop"),
    ("Did the service advisor explain the parts repaired and work performed?", "explained_parts_repaired_work", "Parts Repaired & Work Explained"),
    ("After completion of the Service or repair, did you receive your car back on the same day?", "car_returned_same_day", "Vehicle Returned Same Day"),
    ("Was the Service Advisor polite and courteous during interaction?", "advisor_polite_courteous", "Advisor Polite and Courteous"),
    ("Was the restroom maintained neat and Clean?", "restroom_neat_clean", "Restroom Neat and Clean"),
    ("Did the service advisor walk you out with the statement “Enjoy your Driving with Hyundai”?", "walk_out_hyundai_statement", "Enjoy Driving with Hyundai Statement"),
    ("How would you rate the workshop support for Insurance Claim processing?", "insurance_claim_support_rating", "Insurance Claim Processing Support"),
    ("Did you get the proper response from dealer staff when you visit at Workshop?", "proper_response_dealer_staff", "Proper Response from Staff"),
    ("Did the service advisor explain the parts replaced and charges taken at the time of delivery?", "explained_parts_replaced_charges", "Parts Replaced & Delivery Charges Explained"),
]

# 10 Hyundai Rating Questions
HYUNDAI_RATING_QUESTIONS = [
    ("How would you rate the maintence & repair work done on your car?", "rating_maintenance_repair_work", "Maintenance & Repair Work Done"),
    ("How would you rate the condition or cleanliness of your car, on return?", "rating_cleanliness_on_return", "Cleanliness & Condition on Return"),
    ("How would you rate the explation given by service advisor on the work done of your car?", "rating_explanation_by_advisor", "Advisor Explanation on Work Done"),
    ("How would you rate your overall interaction & experience with workshop?", "rating_overall_interaction_experience", "Overall Workshop Experience"),
    ("Whether the vehicle was Picked & Dropped as per committed Time?", "rating_pick_drop_committed_time", "Pick & Drop on Committed Time"),
    ("How would you rate the Service Delivery process of your car after servicing?", "rating_service_delivery_process", "Service Delivery Process"),
    ("How would you rate the overall cleanliness of Dealer Facility?", "rating_cleanliness_dealer_facility", "Cleanliness of Dealer Facility"),
    ("How would you rate the quality of Denting, Painting and Finishing of repairs carried out in the car?", "rating_denting_painting_quality", "Denting & Painting Finishing Quality"),
    ("How Would you rate the ambience and hygiene of customer Interaction area in the workshop?", "rating_ambience_hygiene_customer_area", "Customer Lounge Ambience & Hygiene"),
    ("Did SA Inform you about the promised delivery date and time of your car?", "rating_informed_promised_delivery_time", "Promised Delivery Date & Time Communication"),
]

# 10 Generic PSF Rating Questions
GENERIC_PSF_QUESTIONS = [
    ("MAINTENANCE AND REPAIR WORK DONE ON CAR", "rating_generic_maintenance_repair", "Maintenance and Repair Work Done"),
    ("CONDITION OF CLEANLINESS OF THE CAR", "rating_generic_cleanliness", "Condition of Cleanliness of Car"),
    ("EXPLAINATION GIVEN BY SA ON WORK DONE AND REPAIR CHARGES AFTER SERVICING", "rating_generic_explanation_charges", "SA Explanation of Work & Charges"),
    ("DELIVERY PROCESS", "rating_generic_delivery_process", "Delivery Process"),
    ("CLEANLINESS OF DEALER FACILITY", "rating_generic_facility_cleanliness", "Cleanliness of Dealer Facility"),
    ("OVERALL INTERACTION AND EXPERIENCE WITH W/S", "rating_generic_overall_experience", "Overall Interaction & Experience"),
    ("AFTER SERVICE VEHICLE CONDITION", "rating_generic_after_service_condition", "After Service Vehicle Condition"),
    ("FAIRNESS OF CHARGES", "rating_generic_fairness_charges", "Fairness of Charges"),
    ("PAYMENT CONFORMATION", "rating_generic_payment_confirmation", "Payment Confirmation"),
    ("HOW WOULD RATE OR RECCOMEND TO YOUR FAMILY & FRIENDS", "rating_generic_recommend_family_friends", "Recommendation to Family & Friends"),
]


async def seed():
    print("🌱 Starting Comprehensive Real Data Database Seeding...")

    async with AsyncSessionLocal() as db:
        # 1. Default Tenant
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
            print(f"  • Existing Tenant: {tenant.name}")

        # 2. Seed System Roles
        roles_def = [
            ("SUPER_ADMIN", "Full platform administrative access", ["*"], True),
            ("DEALER_ADMIN", "Dealer group administration", ["users:manage", "brands:manage", "branches:manage", "psf:manage", "reports:view"], True),
            ("BRAND_MANAGER", "Brand level management", ["psf:read", "reports:view", "questionnaires:manage"], False),
            ("BRANCH_MANAGER", "Branch operational oversight & complaint closer", ["psf:read", "psf:call", "complaints:manage", "reports:view"], False),
            ("SERVICE_MANAGER", "Service manager for branch complaints & escalation", ["psf:read", "complaints:manage", "reports:view"], False),
            ("CRE", "Customer Relations Executive - Outbound caller", ["psf:read", "psf:call", "complaints:create"], False),
            ("SERVICE_ADVISOR", "Workshop Service Advisor", ["advisor:read", "advisor:action", "complaints:view"], False),
            ("AUDITOR", "Read-only auditor", ["psf:read", "reports:view", "reports:export"], False),
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

        # 3. Seed Automotive Brands (7 Brands)
        brands_def = [
            ("Hyundai", "HYUN", "#002C6C"),
            ("Tata Motors", "TATA", "#005088"),
            ("MG Motors", "MG", "#CC0000"),
            ("Ather Energy", "ATHER", "#00D282"),
            ("Hero Moto Corp", "HERO", "#E31837"),
            ("Chevrolet", "CHEV", "#CD9834"),
            ("Swaraj", "SWARAJ", "#006838"),
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

        # 4. Seed Workshop Branches (Explicit branch-to-brand mapping)
        # format: (name, code, brand_code_or_none, dms_code, display_name, city, state, needs_review)
        branches_def = [
            # Hyundai
            ("HYUNDAI HUBLI", "HYUN-HUBLI", "HYUN", "S8211", "Hyundai Hubli", "Hubli", "Karnataka", False),
            ("HYUNDAI GADAG", "HYUN-GADAG", "HYUN", "S8827", "Hyundai Gadag", "Gadag", "Karnataka", False),
            ("HYUNDAI HAVERI", "HYUN-HAVERI", "HYUN", "S8830", "Hyundai Haveri", "Haveri", "Karnataka", False),
            ("HYUNDAI DHARWAD", "HYUN-DHARWAD", "HYUN", "S8840", "Hyundai Dharwad", "Dharwad", "Karnataka", False),
            # Swaraj
            ("SWARAJ HUBLI", "SWARAJ-HUBLI", "SWARAJ", None, "Swaraj Hubli", "Hubli", "Karnataka", False),
            # MG Motors
            ("MG MOTORS BELGAUM", "MG-BELGAUM", "MG", None, "MG Motors Belgaum", "Belgaum", "Karnataka", False),
            ("MG MOTORS GULBARGA", "MG-GULBARGA", "MG", None, "MG Motors Gulbarga", "Gulbarga", "Karnataka", False),
            ("MG MOTORS HUBBALLI", "MG-HUBBALLI", "MG", None, "MG Motors Hubballi", "Hubballi", "Karnataka", False),
            ("MG MOTORS HOSPET", "MG-HOSPET", "MG", None, "MG Motors Hospet", "Hospet", "Karnataka", False),
            # Ather Energy
            ("ATHER BANGALORE", "ATHER-BANGALORE", "ATHER", None, "Ather Bangalore", "Bangalore", "Karnataka", False),
            ("ATHER ENERGY BELGAUM", "ATHER-BELGAUM", "ATHER", None, "Ather Energy Belgaum", "Belgaum", "Karnataka", False),
            ("ATHER ENERGY HUBBALLI", "ATHER-HUBBALLI", "ATHER", None, "Ather Energy Hubballi", "Hubballi", "Karnataka", False),
            ("ATHER ENERGY SIRSI", "ATHER-SIRSI", "ATHER", None, "Ather Energy Sirsi", "Sirsi", "Karnataka", False),
            # Chevrolet
            ("CHEVROLET HUBLI", "CHEV-HUBLI", "CHEV", None, "Chevrolet Hubli", "Hubli", "Karnataka", False),
            ("CHEVROLET BELGAUM", "CHEV-BELGAUM", "CHEV", None, "Chevrolet Belgaum", "Belgaum", "Karnataka", False),
            ("CHEVROLET BELLARY", "CHEV-BELLARY", "CHEV", None, "Chevrolet Bellary", "Bellary", "Karnataka", False),
            # Tata Motors
            ("TATA MOTORS BELLARY", "TATA-BELLARY", "TATA", None, "Tata Motors Bellary", "Bellary", "Karnataka", False),
            ("TATA MOTORS BOMMASANDRA BANGALORE", "TATA-BOMMASANDRA", "TATA", None, "Tata Motors Bommasandra Bangalore", "Bangalore", "Karnataka", False),
            ("TATA MOTORS HOSPET", "TATA-HOSPET", "TATA", None, "Tata Motors Hospet", "Hospet", "Karnataka", False),
            ("TATA MOTORS RAICHUR", "TATA-RAICHUR", "TATA", None, "Tata Motors Raichur", "Raichur", "Karnataka", False),
            ("TATA MOTORS SARJAPUR BANGALORE", "TATA-SARJAPUR", "TATA", None, "Tata Motors Sarjapur Bangalore", "Bangalore", "Karnataka", False),
            ("TATA MOTORS BANGALORE", "TATA-BANGALORE", "TATA", None, "Tata Motors Bangalore", "Bangalore", "Karnataka", False),
            ("TATA MOTORS GANGAVATHI", "TATA-GANGAVATHI", "TATA", None, "Tata Motors Gangavathi", "Gangavathi", "Karnataka", False),
            ("TATA MOTORS SINDHNOOR", "TATA-SINDHNOOR", "TATA", None, "Tata Motors Sindhnoor", "Sindhnoor", "Karnataka", False),
            ("TATA MOTORS KOPPAL", "TATA-KOPPAL", "TATA", None, "Tata Motors Koppal", "Koppal", "Karnataka", False),
            # Hero Moto Corp
            ("HERO MOTO CORP DHARWAD", "HERO-DHARWAD", "HERO", None, "Hero Moto Corp Dharwad", "Dharwad", "Karnataka", False),
            # Haveri TRZ (unassigned / needs-review)
            ("Haveri TRZ", "HAVERI-TRZ", None, None, "Haveri TRZ", "Haveri", "Karnataka", True),
        ]

        branches_map = {}
        for br_name, br_code, b_code, dms_code, disp_name, city, state, needs_rev in branches_def:
            br_stmt = select(Branch).where(Branch.tenant_id == tenant.id, Branch.code == br_code)
            branch = (await db.execute(br_stmt)).scalar_one_or_none()
            brand_id = brands_map[b_code].id if b_code and b_code in brands_map else None

            if not branch:
                branch = Branch(
                    tenant_id=tenant.id,
                    brand_id=brand_id,
                    name=br_name,
                    code=br_code,
                    dms_code=dms_code,
                    display_name=disp_name,
                    city=city,
                    state=state,
                    needs_review=needs_rev,
                    is_active=True,
                )
                db.add(branch)
                await db.flush()
                print(f"  ✓ Created Branch: {br_name} ({br_code}) [DMS: {dms_code}]")
            else:
                # Update DMS code and review flag if missing
                if dms_code and not branch.dms_code:
                    branch.dms_code = dms_code
                if disp_name and not branch.display_name:
                    branch.display_name = disp_name
                branch.needs_review = needs_rev
            branches_map[br_name] = branch
            branches_map[br_code] = branch

        # 5. Seed Branch Contacts from WhatsApp master
        branch_contacts_def = [
            ("TATA MOTORS BELLARY", "Service Manager", "9611939838"),
            ("TATA MOTORS BOMMASANDRA BANGALORE", "Service Manager", "8904632872"),
            ("TATA MOTORS HOSPET", "Service Manager", "9606071075"),
            ("TATA MOTORS RAICHUR", "Service Manager", "6364865951"),
            ("TATA MOTORS SARJAPUR BANGALORE", "Service Manager", "8904632872"),
            ("MG MOTORS BELGAUM", "Service Manager", "9880527948"),
            ("MG MOTORS GULBARGA", "Service Manager", "8892047903"),
            ("MG MOTORS HUBBALLI", "Service Manager", "9900263466"),
        ]
        for br_name, role_name, phone in branch_contacts_def:
            br = branches_map.get(br_name)
            if br:
                p_hash = hash_phone(phone)
                bc_stmt = select(BranchContact).where(
                    BranchContact.tenant_id == tenant.id,
                    BranchContact.branch_id == br.id,
                    BranchContact.phone_hash == p_hash,
                )
                bc = (await db.execute(bc_stmt)).scalar_one_or_none()
                if not bc:
                    bc = BranchContact(
                        tenant_id=tenant.id,
                        branch_id=br.id,
                        role="SERVICE_MANAGER",
                        name=f"{br.name} Service Manager",
                        phone=encrypt_phone(phone),
                        phone_hash=p_hash,
                        notify_on="complaint,low_rating,daily_summary",
                        is_active=True,
                    )
                    db.add(bc)
                    print(f"  ✓ Created Branch Contact: {br_name} -> {role_name}")

        # 6. Seed Call Statuses
        call_statuses_def = [
            ("Connected", "SENTIMENT", True, False, True, "#10B981"),
            ("Not Connected", "CONTACT_FAILED", False, False, True, "#EF4444"),
        ]
        for cs_name, cat, contacted, closes, retry, col in call_statuses_def:
            cs_stmt = select(CallStatus).where(CallStatus.tenant_id == tenant.id, CallStatus.name == cs_name)
            cs = (await db.execute(cs_stmt)).scalar_one_or_none()
            if not cs:
                cs = CallStatus(
                    tenant_id=tenant.id,
                    name=cs_name,
                    category=cat,
                    counts_as_contacted=contacted,
                    closes_followup=closes,
                    retry_allowed=retry,
                    color=col,
                    is_active=True,
                )
                db.add(cs)
                print(f"  ✓ Created Call Status: {cs_name}")

        # 7. Seed Case Statuses (16 values with categories & flags)
        case_statuses_def = [
            # SENTIMENT
            ("Delight", "SENTIMENT", True, True, False, "#10B981"),
            ("Satisfied", "SENTIMENT", True, True, False, "#3B82F6"),
            ("Non-Delight", "SENTIMENT", True, True, False, "#F59E0B"),
            ("Dissatisfied", "SENTIMENT", True, True, False, "#EF4444"),
            # CONTACT_FAILED
            ("No Response", "CONTACT_FAILED", False, False, True, "#6B7280"),
            ("Not Reachable", "CONTACT_FAILED", False, False, True, "#6B7280"),
            ("Switch Off", "CONTACT_FAILED", False, False, True, "#6B7280"),
            ("Incoming Call Not Available", "CONTACT_FAILED", False, False, True, "#6B7280"),
            ("Call Disconnected", "CONTACT_FAILED", False, False, True, "#6B7280"),
            # INVALID
            ("Wrong Number", "INVALID", False, True, False, "#DC2626"),
            ("Invalid Number", "INVALID", False, True, False, "#DC2626"),
            ("Vehicle Sold", "INVALID", False, True, False, "#DC2626"),
            # DEFERRED
            ("Call Later", "DEFERRED", True, False, True, "#8B5CF6"),
            ("Vehicle Inside Workshop", "DEFERRED", True, False, True, "#8B5CF6"),
            ("Vehicle Not Checked", "DEFERRED", True, False, True, "#8B5CF6"),
            ("Parts Order", "DEFERRED", True, False, True, "#8B5CF6"),
        ]
        for cs_name, cat, contacted, closes, retry, col in case_statuses_def:
            cs_stmt = select(CaseStatus).where(CaseStatus.tenant_id == tenant.id, CaseStatus.name == cs_name)
            cs = (await db.execute(cs_stmt)).scalar_one_or_none()
            if not cs:
                cs = CaseStatus(
                    tenant_id=tenant.id,
                    name=cs_name,
                    category=cat,
                    counts_as_contacted=contacted,
                    closes_followup=closes,
                    retry_allowed=retry,
                    color=col,
                    is_active=True,
                )
                db.add(cs)
                print(f"  ✓ Created Case Status: {cs_name} [{cat}]")

        # 8. Seed Rating Scales + Bands
        scales_def = [
            ("HYUN", "Hyundai PSF Rating Scale", 10, [
                (1, 5, "Poor", "Dissatisfied", False, True),
                (6, 8, "Average", "Non-Delight", False, True),
                (9, 9, "Satisfied", "Satisfied", False, True),
                (10, 10, "Delight", "Delight", True, False),
            ]),
            ("TATA", "Tata Motors PSF Rating Scale", 5, [
                (1, 3, "Dissatisfied", "Dissatisfied", False, True),
                (4, 4, "Satisfied", "Satisfied", False, False),
                (5, 5, "Good", "Delight", True, False),
            ]),
            ("MG", "MG Motors PSF Rating Scale", 10, [
                (1, 8, "Dissatisfied/Poor", "Dissatisfied", False, True),
                (9, 10, "Satisfied", "Satisfied", True, False),
            ]),
        ]
        for b_code, s_name, max_r, bands in scales_def:
            brand = brands_map.get(b_code)
            if not brand:
                continue
            sc_stmt = select(RatingScale).where(RatingScale.tenant_id == tenant.id, RatingScale.brand_id == brand.id)
            scale = (await db.execute(sc_stmt)).scalar_one_or_none()
            if not scale:
                scale = RatingScale(
                    tenant_id=tenant.id,
                    brand_id=brand.id,
                    name=s_name,
                    max_rating=max_r,
                    is_active=True,
                )
                db.add(scale)
                await db.flush()
                print(f"  ✓ Created Rating Scale: {s_name}")

            # Sync bands idempotently
            existing_bands_res = await db.execute(select(RatingScaleBand).where(RatingScaleBand.scale_id == scale.id))
            existing_bands = existing_bands_res.scalars().all()
            for eb in existing_bands:
                await db.delete(eb)
            await db.flush()

            for min_s, max_s, lbl, der_cs, is_del, is_trig in bands:
                band = RatingScaleBand(
                    tenant_id=tenant.id,
                    scale_id=scale.id,
                    min_score=min_s,
                    max_score=max_s,
                    label=lbl,
                    derived_case_status=der_cs,
                    is_delight=is_del,
                    is_complaint_trigger=is_trig,
                )
                db.add(band)
            print(f"    + Synced {len(bands)} rating bands for {brand.name}")

        # 9. Seed 14 Complaint Categories
        # (Clean Name, Icon, Legacy Label, SLA, Severity, Brand Specific Code)
        categories_def = [
            ("Availability of Spares", "🔩", "AVAILABILITY OF SPARES", 48, "HIGH", None),
            ("Body Shop Complaints", "🛠️", "BODY SHOP COMPLAINTS", 24, "HIGH", None),
            ("Dealer Facility", "☕", "DEALER FACILITY", 12, "LOW", None),
            ("Delivery Process", "🚚", "DELIVERY PROCESS", 8, "MEDIUM", None),
            ("Fairness of Charges", "₹", "FAIRNESS OF CHARGES", 12, "MEDIUM", None),
            ("Other Complaint", "📋", "OTHER COMPLAINT", 24, "MEDIUM", None),
            ("Washing Complaints", "🚿", "WASHING COMPLAINTS", 6, "LOW", None),
            ("Mechanical Complaint", "🔧", "MECHANICAL COMPLAINT", 24, "HIGH", None),
            ("Electrical Complaint", "💡", "ELECTRICAL COMPLAINT", 24, "HIGH", None),
            ("No Complaint", "✅", "NO COMPLAINT", 0, "LOW", None),
            ("Advisor Behavior", "👤", "ADVISOR BEHAVIOR", 12, "MEDIUM", None),
            ("WhatsApp Rating <=9", "📱", "WATSAPP RATING <=9", 12, "MEDIUM", "HYUN"),
            ("Hyundai SOP", "📋", "HYUNDAI SOP", 24, "MEDIUM", "HYUN"),
            ("Overall Dissatisfaction", "⚠️", "OVERALL DISSATICFACTION", 24, "HIGH", None),
        ]
        for c_name, icon, leg_lbl, sla, sev, b_code in categories_def:
            b_id = brands_map[b_code].id if b_code and b_code in brands_map else None
            c_stmt = select(ComplaintCategory).where(
                ComplaintCategory.tenant_id == tenant.id,
                ComplaintCategory.name == c_name,
            )
            cat = (await db.execute(c_stmt)).scalar_one_or_none()
            if not cat:
                cat = ComplaintCategory(
                    tenant_id=tenant.id,
                    brand_id=b_id,
                    name=c_name,
                    icon=icon,
                    legacy_label=leg_lbl,
                    default_sla_hours=sla,
                    severity_level=sev,
                    is_active=True,
                )
                db.add(cat)
                print(f"  ✓ Created Complaint Category: {c_name} {icon}")
            else:
                cat.icon = icon
                cat.legacy_label = leg_lbl

        # 10. Seed Questionnaires
        # (a) Hyundai PSF Questionnaire
        hyundai_brand = brands_map.get("HYUN")
        if hyundai_brand:
            qn_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant.id,
                Questionnaire.brand_id == hyundai_brand.id,
                Questionnaire.type == "PSF",
            )
            qn = (await db.execute(qn_stmt)).scalar_one_or_none()
            if not qn:
                qn = Questionnaire(
                    tenant_id=tenant.id,
                    brand_id=hyundai_brand.id,
                    type="PSF",
                    title="Hyundai Post Service Follow-up (PSF) Standard Survey",
                    version=1,
                    is_active=True,
                )
                db.add(qn)
                await db.flush()
                print(f"  ✓ Created Hyundai PSF Questionnaire")

            # Check question count for Hyundai PSF: should be exactly 31 (21 Yes/No + 10 Ratings)
            existing_qs_stmt = select(Question).where(Question.questionnaire_id == qn.id)
            existing_qs = (await db.execute(existing_qs_stmt)).scalars().all()
            if len(existing_qs) != 31:
                for eq in existing_qs:
                    await db.delete(eq)
                await db.flush()

                order = 1
                # Add 21 Yes/No questions
                for text, key, label in HYUNDAI_YES_NO_QUESTIONS:
                    q = Question(
                        tenant_id=tenant.id,
                        questionnaire_id=qn.id,
                        key=key,
                        label=label,
                        legacy_label=text,
                        type="yes_no",
                        answer_type="YES_NO",
                        section="Service Feedback",
                        display_order=order,
                    )
                    db.add(q)
                    order += 1

                # Add 10 Rating questions
                for text, key, label in HYUNDAI_RATING_QUESTIONS:
                    q = Question(
                        tenant_id=tenant.id,
                        questionnaire_id=qn.id,
                        key=key,
                        label=label,
                        legacy_label=text,
                        type="nps_10",
                        answer_type="RATING_10",
                        section="Rating Evaluation",
                        display_order=order,
                    )
                    db.add(q)
                    order += 1
                print(f"    + Seeded 31 Hyundai PSF Questions (21 Yes/No + 10 Ratings)")

        # (b) Generic PSF Questionnaire for other brands
        generic_brands = ["TATA", "MG", "ATHER", "HERO", "CHEV", "SWARAJ"]
        for b_code in generic_brands:
            brand = brands_map.get(b_code)
            if not brand:
                continue
            qn_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant.id,
                Questionnaire.brand_id == brand.id,
                Questionnaire.type == "PSF",
            )
            qn = (await db.execute(qn_stmt)).scalar_one_or_none()
            if not qn:
                qn = Questionnaire(
                    tenant_id=tenant.id,
                    brand_id=brand.id,
                    type="PSF",
                    title=f"{brand.name} Post Service Feedback (PSF)",
                    version=1,
                    is_active=True,
                )
                db.add(qn)
                await db.flush()

                order = 1
                for text, key, label in GENERIC_PSF_QUESTIONS:
                    q = Question(
                        tenant_id=tenant.id,
                        questionnaire_id=qn.id,
                        key=key,
                        label=label,
                        legacy_label=text,
                        type="nps_10" if b_code != "TATA" else "rating_5",
                        answer_type="RATING_10" if b_code != "TATA" else "RATING_5",
                        section="General Ratings",
                        display_order=order,
                    )
                    db.add(q)
                    order += 1
                print(f"  ✓ Created Generic PSF Questionnaire for {brand.name} (10 Rating Questions)")

        # 11. Seed Closer / Personnel Users
        users_def = [
            ("admin@apexauto.com", "Admin@12345", "Sandeep Sharma", "SUPER_ADMIN", "EMP-001", "9876500001", None, None),
            ("deepa.hiremath@apexauto.com", "Closer@12345", "Deepa Hiremath", "SERVICE_MANAGER", "EMP-004", "9876500004", "HYUN", "HYUN-HUBLI"),
            ("pooja.cre@apexauto.com", "Cre@12345", "Pooja M", "CRE", "EMP-102", "9876543211", "HYUN", "HYUN-HUBLI"),
            ("arpita.cre@apexauto.com", "Cre@12345", "Arpita Tubak", "CRE", "EMP-103", "9876543212", "HYUN", "HYUN-HUBLI"),
            ("divya.cre@apexauto.com", "Cre@12345", "Divya M", "CRE", "EMP-104", "9876543213", "HYUN", "HYUN-HUBLI"),
            ("swathi.cre@apexauto.com", "Cre@12345", "Swathi Badiger", "CRE", "EMP-105", "9876543214", "HYUN", "HYUN-HUBLI"),
            ("sumitra.cre@apexauto.com", "Cre@12345", "Sumitra", "CRE", "EMP-106", "9876543215", "HYUN", "HYUN-HUBLI"),
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

                if sc_brand or sc_branch:
                    scope = UserScope(
                        tenant_id=tenant.id,
                        user_id=user.id,
                        brand_id=brands_map[sc_brand].id if sc_brand and sc_brand in brands_map else None,
                        branch_id=branches_map[sc_branch].id if sc_branch and sc_branch in branches_map else None,
                    )
                    db.add(scope)
                print(f"  ✓ Created User: {name} ({role_k})")

        await db.commit()
        print("✅ Real data database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
