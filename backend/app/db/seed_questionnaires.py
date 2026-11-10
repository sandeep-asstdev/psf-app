"""
================================================================================
FILE PURPOSE: Survey Questionnaire Seeding Script.
Seeds standard manufacturer-compliant survey questionnaires for Hyundai, Tata Motors, and MG Motors,
including 1-10 NPS rating questions, service satisfaction ratings, and CSAT calculation logic.

KEY RESPONSIBILITIES:
- Seeds Hyundai 4-Question PSF Survey template.
- Seeds Tata Motors 7-Question PSF Survey template.
- Seeds MG Motors 5-Question PSF Survey template.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Questionnaire seed fails with 'Brand not found'
  -> Cause: Brands have not been seeded yet.
  -> What should you do: Run `seed.py` first to create the OEM Brands before running `seed_questionnaires.py`.
================================================================================
"""
import asyncio
import sys
import os
from decimal import Decimal

# Ensure backend root is on sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant, Brand
from app.models.questionnaire import Questionnaire, Question


async def seed_questionnaires():
    print("📋 Seeding Versioned Dynamic Questionnaires & Brand Templates...")

    async with AsyncSessionLocal() as db:
        # Fetch Tenant
        t_stmt = select(Tenant).where(Tenant.slug == "apex-auto")
        tenant = (await db.execute(t_stmt)).scalar_one_or_none()
        if not tenant:
            print("❌ Tenant 'apex-auto' not found. Run seed.py first.")
            return

        # Fetch Brands
        b_stmt = select(Brand).where(Brand.tenant_id == tenant.id)
        brands = (await db.execute(b_stmt)).scalars().all()
        brand_by_code = {b.code: b for b in brands}

        hyundai = brand_by_code.get("HYUN")
        mg = brand_by_code.get("MG")
        ather = brand_by_code.get("ATHER")

        # -------------------------------------------------------------
        # 1. HYUNDAI PSF Questionnaire (~26 questions across 5 sections)
        # -------------------------------------------------------------
        if hyundai:
            q_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant.id,
                Questionnaire.brand_id == hyundai.id,
                Questionnaire.type == "PSF",
                Questionnaire.version == 1,
            )
            hyundai_psf = (await db.execute(q_stmt)).scalar_one_or_none()
            if not hyundai_psf:
                hyundai_psf = Questionnaire(
                    tenant_id=tenant.id,
                    brand_id=hyundai.id,
                    type="PSF",
                    title="Hyundai Post Service Follow-up (PSF) Standard Survey",
                    version=1,
                    is_active=True,
                )
                db.add(hyundai_psf)
                await db.flush()

                hyundai_psf_questions = [
                    # Section: Pick-up & Drop
                    ("hyundai_pickup_drop_offered", "Was Pick-up & Drop service offered or availed?", "yes_no_na", "Pick-up & Drop", None, None, 1.0, 1, False),
                    ("hyundai_pickup_courtesy", "Courtesy and behavior of pick-up driver / personnel", "rating_5", "Pick-up & Drop", None, {"field": "hyundai_pickup_drop_offered", "operator": "==", "value": "yes"}, 1.0, 2, False),
                    ("hyundai_ontime_pickup_drop", "Was the vehicle picked up and dropped back on time?", "yes_no_na", "Pick-up & Drop", None, {"field": "hyundai_pickup_drop_offered", "operator": "==", "value": "yes"}, 1.0, 3, False),
                    # Section: Advisor & Consultation
                    ("hyundai_tablet_repair_order", "Was the repair order prepared on a digital tablet in your presence?", "yes_no", "Advisor & Reception", None, None, 1.0, 4, True),
                    ("hyundai_history_checked", "Did the service advisor review previous maintenance history with you?", "yes_no", "Advisor & Reception", None, None, 1.0, 5, False),
                    ("hyundai_inspection_in_front", "Was vehicle underbody and joint inspection done in front of you?", "yes_no", "Advisor & Reception", None, None, 1.0, 6, False),
                    ("hyundai_water_bottle_offered", "Was a complimentary sealed water bottle offered at reception?", "yes_no", "Advisor & Reception", None, None, 0.5, 7, False),
                    ("hyundai_road_test_before", "Was a pre-repair road test conducted with you?", "yes_no", "Advisor & Reception", None, None, 1.0, 8, False),
                    ("hyundai_advisor_politeness", "Politeness, listening ability, and attentiveness of Service Advisor", "rating_5", "Advisor & Reception", None, None, 1.5, 9, True),
                    ("hyundai_parts_explained", "Were required spare parts and estimated costs clearly explained beforehand?", "yes_no", "Advisor & Reception", None, None, 1.5, 10, True),
                    ("hyundai_whatsapp_updates", "Did you receive real-time repair status updates on WhatsApp?", "yes_no", "Advisor & Reception", None, None, 1.0, 11, False),
                    # Section: Facility & Cleanliness
                    ("hyundai_facility_cleanliness", "Cleanliness and organization of the service workshop", "rating_5", "Facility & Ambiance", None, None, 1.0, 12, False),
                    ("hyundai_customer_ambience", "Customer lounge ambience, seating comfort, and air conditioning", "rating_5", "Facility & Ambiance", None, None, 1.0, 13, False),
                    ("hyundai_restroom_cleanliness", "Cleanliness and hygiene of customer restrooms", "rating_5", "Facility & Ambiance", None, None, 1.0, 14, False),
                    # Section: Workmanship & Delivery
                    ("hyundai_sameday_delivery", "Was vehicle delivered on the promised date/time?", "yes_no_na", "Workmanship & Delivery", None, None, 1.5, 15, True),
                    ("hyundai_work_quality", "Quality of repair and overall mechanical workmanship", "rating_5", "Workmanship & Delivery", None, None, 2.0, 16, True),
                    ("hyundai_denting_painting_quality", "Denting and painting finish quality (if body repair done)", "rating_5", "Workmanship & Delivery", None, None, 1.5, 17, False),
                    ("hyundai_car_cleanliness", "Cleanliness of your car (interior vacuuming & exterior washing)", "rating_5", "Workmanship & Delivery", None, None, 1.5, 18, True),
                    ("hyundai_road_test_after", "Was a post-repair verification road test offered at delivery?", "yes_no", "Workmanship & Delivery", None, None, 1.0, 19, False),
                    ("hyundai_repair_charges_reasonable", "Were repair and service charges reasonable and transparent?", "yes_no", "Workmanship & Delivery", None, None, 1.5, 20, True),
                    ("hyundai_charges_explained_delivery", "Were invoice line items and replaced parts explained at delivery?", "yes_no", "Workmanship & Delivery", None, None, 1.0, 21, False),
                    ("hyundai_walkout_greeting", "Did the service staff walk you out with 'Enjoy your driving with Hyundai'?", "yes_no", "Workmanship & Delivery", None, None, 0.5, 22, False),
                    ("hyundai_dealer_staff_response", "Overall helpfulness and promptness of dealership personnel", "rating_5", "Workmanship & Delivery", None, None, 1.0, 23, False),
                    # Section: Overall Experience & NPS
                    ("hyundai_recommend_dealer", "How likely are you to recommend our Hyundai workshop to family/friends? (0-10)", "nps_10", "Overall CSAT & NPS", None, None, 2.0, 24, True),
                    ("hyundai_overall_experience", "Overall experience rating for this service visit", "rating_5", "Overall CSAT & NPS", None, None, 2.0, 25, True),
                ]

                for key, label, qtype, sec, opts, s_if, wt, ord_idx, req in hyundai_psf_questions:
                    q = Question(
                        tenant_id=tenant.id,
                        questionnaire_id=hyundai_psf.id,
                        key=key,
                        label=label,
                        type=qtype,
                        section=sec,
                        options=opts,
                        show_if=s_if,
                        weight=Decimal(str(wt)),
                        display_order=ord_idx,
                        is_required=req,
                    )
                    db.add(q)
                print(f"  ✓ Created Hyundai PSF Questionnaire with {len(hyundai_psf_questions)} questions")

        # -------------------------------------------------------------
        # 2. HYUNDAI HAPPINESS CALLING (Exclusive to Hyundai!)
        # -------------------------------------------------------------
        if hyundai:
            h_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant.id,
                Questionnaire.brand_id == hyundai.id,
                Questionnaire.type == "HAPPINESS",
                Questionnaire.version == 1,
            )
            hyundai_happy = (await db.execute(h_stmt)).scalar_one_or_none()
            if not hyundai_happy:
                hyundai_happy = Questionnaire(
                    tenant_id=tenant.id,
                    brand_id=hyundai.id,
                    type="HAPPINESS",
                    title="Hyundai 15/30-Day Happiness Calling Campaign",
                    version=1,
                    is_active=True,
                )
                db.add(hyundai_happy)
                await db.flush()

                happy_questions = [
                    ("hyundai_happy_running_condition", "How is your Hyundai vehicle running post-service?", "rating_5", "Vehicle Running Condition", None, None, 1.5, 1, True),
                    ("hyundai_happy_advisor_connect", "Did your Service Advisor connect with you to confirm satisfaction?", "yes_no", "Follow-up Checks", None, None, 1.0, 2, False),
                    ("hyundai_happy_unresolved_issue", "Has any new vibration, noise, or warning light appeared?", "yes_no", "Vehicle Running Condition", None, None, 1.5, 3, True),
                    ("hyundai_happy_issue_details", "Please describe the issue or symptom observed:", "text", "Vehicle Running Condition", None, {"field": "hyundai_happy_unresolved_issue", "operator": "==", "value": "yes"}, 1.0, 4, False),
                    ("hyundai_happy_overall_satisfaction", "Overall satisfaction with your Hyundai ownership & service", "rating_5", "Overall Satisfaction", None, None, 2.0, 5, True),
                ]

                for key, label, qtype, sec, opts, s_if, wt, ord_idx, req in happy_questions:
                    db.add(Question(
                        tenant_id=tenant.id,
                        questionnaire_id=hyundai_happy.id,
                        key=key,
                        label=label,
                        type=qtype,
                        section=sec,
                        options=opts,
                        show_if=s_if,
                        weight=Decimal(str(wt)),
                        display_order=ord_idx,
                        is_required=req,
                    ))
                print(f"  ✓ Created Hyundai Happiness Questionnaire with {len(happy_questions)} questions (Exclusive to Hyundai)")

        # -------------------------------------------------------------
        # 3. MG MOTORS PSF & TNPS Questionnaire
        # -------------------------------------------------------------
        if mg:
            mg_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant.id,
                Questionnaire.brand_id == mg.id,
                Questionnaire.type == "PSF",
                Questionnaire.version == 1,
            )
            mg_psf = (await db.execute(mg_stmt)).scalar_one_or_none()
            if not mg_psf:
                mg_psf = Questionnaire(
                    tenant_id=tenant.id,
                    brand_id=mg.id,
                    type="PSF",
                    title="MG Motors PSF & TNPS Quality Survey",
                    version=1,
                    is_active=True,
                )
                db.add(mg_psf)
                await db.flush()

                mg_questions = [
                    ("mg_recommend_brand_nps", "How likely are you to recommend the MG brand to others? (0-10)", "nps_10", "Net Promoter Score", None, None, 2.0, 1, True),
                    ("mg_recommend_workshop_nps", "How likely are you to recommend this MG workshop? (0-10)", "nps_10", "Net Promoter Score", None, None, 2.0, 2, True),
                    ("mg_handover_rating", "Handover and vehicle delivery process rating", "rating_5", "Handover & Delivery", None, None, 1.5, 3, True),
                    ("mg_handover_reasons", "Reason for handover rating / areas to improve:", "text", "Handover & Delivery", None, {"field": "mg_handover_rating", "operator": "<=", "value": 3}, 1.0, 4, False),
                    ("mg_advisor_rating", "Service Advisor professionalism and transparency rating", "rating_5", "Advisor Experience", None, None, 1.5, 5, True),
                    ("mg_advisor_reasons", "Reason for advisor rating:", "text", "Advisor Experience", None, {"field": "mg_advisor_rating", "operator": "<=", "value": 3}, 1.0, 6, False),
                    ("mg_work_charges_explained_before", "Were scope of work and estimated charges explained in advance?", "yes_no", "Billing & Transparency", None, None, 1.0, 7, True),
                    ("mg_first_attempt_resolution", "Were all reported issues resolved in the first attempt?", "yes_no", "Workmanship", None, None, 2.0, 8, True),
                    ("mg_first_attempt_reasons", "Why was repeat visit required?", "text", "Workmanship", None, {"field": "mg_first_attempt_resolution", "operator": "==", "value": "no"}, 1.0, 9, False),
                    ("mg_improvement_areas", "Key improvement areas requested:", "multi_select", "Overall Feedback", [{"label": "Vehicle Washing"}, {"label": "Delivery Speed"}, {"label": "Billing Clarity"}, {"label": "Parts Availability"}, {"label": "Advisor Responsiveness"}], None, 1.0, 10, False),
                ]

                for key, label, qtype, sec, opts, s_if, wt, ord_idx, req in mg_questions:
                    db.add(Question(
                        tenant_id=tenant.id,
                        questionnaire_id=mg_psf.id,
                        key=key,
                        label=label,
                        type=qtype,
                        section=sec,
                        options=opts,
                        show_if=s_if,
                        weight=Decimal(str(wt)),
                        display_order=ord_idx,
                        is_required=req,
                    ))
                print(f"  ✓ Created MG Motors PSF Questionnaire with {len(mg_questions)} questions")

        # -------------------------------------------------------------
        # 4. ATHER ENERGY PSF Questionnaire
        # -------------------------------------------------------------
        if ather:
            ather_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant.id,
                Questionnaire.brand_id == ather.id,
                Questionnaire.type == "PSF",
                Questionnaire.version == 1,
            )
            ather_psf = (await db.execute(ather_stmt)).scalar_one_or_none()
            if not ather_psf:
                ather_psf = Questionnaire(
                    tenant_id=tenant.id,
                    brand_id=ather.id,
                    type="PSF",
                    title="Ather Energy EV Post Service Feedback",
                    version=1,
                    is_active=True,
                )
                db.add(ather_psf)
                await db.flush()

                ather_questions = [
                    ("ather_jobs_satisfaction", "Were all service jobs completed to your full satisfaction?", "yes_no", "EV Service Quality", None, None, 2.0, 1, True),
                    ("ather_charging_status", "Was the scooter charged to at least 80% SoC at delivery?", "rating_5", "EV Service Quality", None, None, 1.5, 2, True),
                    ("ather_ota_explained", "Were latest software/OTA features explained by service staff?", "yes_no_na", "Software & Features", None, None, 1.0, 3, False),
                    ("ather_doc_uploaded", "Was digital gate pass & tax invoice received on WhatsApp?", "yes_no", "Digital Handover", None, None, 1.0, 4, False),
                    ("ather_workshop_experience", "How likely are you to recommend Ather Space service to an EV buyer? (0-10)", "nps_10", "Overall CSAT", None, None, 2.0, 5, True),
                ]

                for key, label, qtype, sec, opts, s_if, wt, ord_idx, req in ather_questions:
                    db.add(Question(
                        tenant_id=tenant.id,
                        questionnaire_id=ather_psf.id,
                        key=key,
                        label=label,
                        type=qtype,
                        section=sec,
                        options=opts,
                        show_if=s_if,
                        weight=Decimal(str(wt)),
                        display_order=ord_idx,
                        is_required=req,
                    ))
                print(f"  ✓ Created Ather Energy PSF Questionnaire with {len(ather_questions)} questions")

        # -------------------------------------------------------------
        # 5. RECONFIRMATION Questionnaire (Used after complaint resolution)
        # -------------------------------------------------------------
        if hyundai:
            r_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant.id,
                Questionnaire.brand_id == hyundai.id,
                Questionnaire.type == "RECONFIRMATION",
                Questionnaire.version == 1,
            )
            reconf_q = (await db.execute(r_stmt)).scalar_one_or_none()
            if not reconf_q:
                reconf_q = Questionnaire(
                    tenant_id=tenant.id,
                    brand_id=hyundai.id,
                    type="RECONFIRMATION",
                    title="Post-Complaint Resolution Reconfirmation Call",
                    version=1,
                    is_active=True,
                )
                db.add(reconf_q)
                await db.flush()

                reconf_questions = [
                    ("reconf_repair_quality", "Has the previously reported complaint been completely resolved?", "yes_no", "Resolution Verification", None, None, 2.0, 1, True),
                    ("reconf_timely_delivery", "Was the vehicle handed over on the agreed committed schedule?", "yes_no", "Resolution Verification", None, None, 1.5, 2, True),
                    ("reconf_advisor_responsiveness", "How satisfied are you with the Service Manager's response?", "rating_5", "Staff Handling", None, None, 1.5, 3, True),
                    ("reconf_vehicle_cleanliness", "Cleanliness of your vehicle upon re-delivery", "rating_5", "Vehicle Condition", None, None, 1.0, 4, False),
                    ("reconf_overall_experience", "Overall experience following complaint resolution", "rating_5", "Final Closure", None, None, 2.0, 5, True),
                    ("reconf_recommendation", "Likelihood to continue visiting our workshop (0-10)", "nps_10", "Final Closure", None, None, 2.0, 6, True),
                ]

                for key, label, qtype, sec, opts, s_if, wt, ord_idx, req in reconf_questions:
                    db.add(Question(
                        tenant_id=tenant.id,
                        questionnaire_id=reconf_q.id,
                        key=key,
                        label=label,
                        type=qtype,
                        section=sec,
                        options=opts,
                        show_if=s_if,
                        weight=Decimal(str(wt)),
                        display_order=ord_idx,
                        is_required=req,
                    ))
                print(f"  ✓ Created Reconfirmation Questionnaire with {len(reconf_questions)} questions")

        await db.commit()
        print("✅ Questionnaire seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_questionnaires())

