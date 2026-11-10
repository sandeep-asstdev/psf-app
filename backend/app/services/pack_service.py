"""
================================================================================
FILE PURPOSE: Dealership Config Packs & Onboarding Service.
Manages versioned config packs (Hyundai, Tata, MG, Ather, Blank) containing
programs, questionnaires, rating scales, outcome rules, and custom labels.
Provides pack cloning, export/import with JSON schema validation, and 
full dealership onboarding wizard.
================================================================================
"""
import os
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tenant import Tenant, Brand, Branch
from app.models.auth import Role, User
from app.models.additional import RatingScale, RatingScaleBand
from app.models.questionnaire import Questionnaire, Question, KpiTag
from app.models.config import FollowUpProgram, OutcomeRule, LabelOverride, ConfigPack
from app.services.config_resolver import ConfigResolverService
from app.core.security import get_password_hash

PACKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db", "packs"))


class PackService:

    @classmethod
    def list_available_packs(cls) -> List[Dict[str, Any]]:
        """Scans PACKS_DIR and returns all available configuration packs."""
        packs = []
        if not os.path.exists(PACKS_DIR):
            return packs

        for filename in sorted(os.listdir(PACKS_DIR)):
            if filename.endswith(".json"):
                code = filename[:-5].upper()
                file_path = os.path.join(PACKS_DIR, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        packs.append({
                            "code": code,
                            "name": data.get("name", code),
                            "version": data.get("pack_version", "1.0.0"),
                            "description": data.get("description", ""),
                            "brand_code": data.get("brand_code", "CUSTOM"),
                        })
                except Exception as e:
                    continue
        return packs

    @classmethod
    def load_pack_json(cls, code: str) -> Optional[Dict[str, Any]]:
        """Loads full JSON payload of a specific pack."""
        filename = f"{code.lower()}.json"
        file_path = os.path.join(PACKS_DIR, filename)
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def validate_pack_schema(cls, payload: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates that a JSON configuration payload adheres to config pack specification."""
        if not isinstance(payload, dict):
            return False, "Payload must be a JSON object"

        if "pack_version" not in payload:
            return False, "Missing required key: 'pack_version'"

        # Check programs
        programs = payload.get("programs")
        if programs is not None and not isinstance(programs, list):
            return False, "'programs' must be a list"
        for p in (programs or []):
            if not isinstance(p, dict) or "code" not in p or "label" not in p:
                return False, "Each program must contain 'code' and 'label'"

        # Check questionnaires
        questionnaires = payload.get("questionnaires")
        if questionnaires is not None and not isinstance(questionnaires, list):
            return False, "'questionnaires' must be a list"

        # Check scales
        scales = payload.get("scales")
        if scales is not None and not isinstance(scales, list):
            return False, "'scales' must be a list"

        # Check rules
        rules = payload.get("rules")
        if rules is not None and not isinstance(rules, list):
            return False, "'rules' must be a list"

        # Check labels
        labels = payload.get("labels")
        if labels is not None and not isinstance(labels, dict):
            return False, "'labels' must be an object (key-value map)"

        return True, None

    @classmethod
    async def clone_pack_to_dealership(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        pack_payload: Dict[str, Any],
        brand_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Clones a config pack into the target dealership tenant."""
        created_counts = {
            "scales": 0,
            "questionnaires": 0,
            "questions": 0,
            "programs": 0,
            "rules": 0,
            "labels": 0,
        }

        # 1. Resolve or create Brand if brand_id not supplied
        if not brand_id:
            brand_code = pack_payload.get("brand_code", "CUSTOM").upper()
            b_stmt = select(Brand).where(Brand.tenant_id == tenant_id, Brand.code == brand_code)
            brand = (await db.execute(b_stmt)).scalar_one_or_none()
            if not brand:
                brand = Brand(
                    tenant_id=tenant_id,
                    name=pack_payload.get("name", brand_code).replace(" Dealership Pack", "").replace(" Pack", ""),
                    code=brand_code,
                    is_active=True,
                )
                db.add(brand)
                await db.flush()
            brand_id = brand.id

        # 2. Rating Scales & Bands
        scale_map = {}
        for s in pack_payload.get("scales", []):
            scale_name = s.get("name", "Standard Rating Scale")
            scale_stmt = select(RatingScale).where(
                RatingScale.tenant_id == tenant_id,
                RatingScale.brand_id == brand_id,
            )
            scale = (await db.execute(scale_stmt)).scalar_one_or_none()
            if not scale:
                scale = RatingScale(
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    name=scale_name,
                    max_rating=s.get("max_val", 5),
                    is_active=True,
                )
                db.add(scale)
                await db.flush()
                created_counts["scales"] += 1
            else:
                scale.name = scale_name
                scale.max_rating = s.get("max_val", scale.max_rating)
                # Refresh bands
                old_bands = (await db.execute(select(RatingScaleBand).where(RatingScaleBand.scale_id == scale.id))).scalars().all()
                for ob in old_bands:
                    await db.delete(ob)
                await db.flush()

            # Bands
            for b in s.get("bands", []):
                band = RatingScaleBand(
                    tenant_id=tenant_id,
                    scale_id=scale.id,
                    label=b.get("name", b.get("status")),
                    derived_case_status=b.get("status", "SATISFIED"),
                    min_score=b.get("min_val", 1),
                    max_score=b.get("max_val", 5),
                    is_delight=(b.get("status") == "DELIGHT"),
                    is_complaint_trigger=(b.get("status") in ["DISSATISFIED", "COMPLAINT"]),
                )
                db.add(band)
            await db.flush()
            scale_map[scale_name] = scale.id

        first_scale_id = list(scale_map.values())[0] if scale_map else None

        # 3. Questionnaires & Questions
        qnr_map = {}
        for qnr_data in pack_payload.get("questionnaires", []):
            q_title = qnr_data.get("title", "Post Service Follow-up")
            q_type = qnr_data.get("type", "PSF")

            qnr_stmt = select(Questionnaire).where(
                Questionnaire.tenant_id == tenant_id,
                Questionnaire.brand_id == brand_id,
                Questionnaire.type == q_type,
            )
            qnr = (await db.execute(qnr_stmt)).scalar_one_or_none()
            if not qnr:
                qnr = Questionnaire(
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    type=q_type,
                    title=q_title,
                    version=1,
                    status="PUBLISHED",
                    is_active=True,
                )
                db.add(qnr)
                await db.flush()
                created_counts["questionnaires"] += 1
            else:
                qnr.title = q_title
                # Clear old questions
                old_questions = (await db.execute(select(Question).where(Question.questionnaire_id == qnr.id))).scalars().all()
                for oq in old_questions:
                    await db.delete(oq)
                await db.flush()

            for idx, q_item in enumerate(qnr_data.get("questions", []), start=1):
                q = Question(
                    tenant_id=tenant_id,
                    questionnaire_id=qnr.id,
                    key=q_item.get("key", f"q_{idx}"),
                    label=q_item.get("label", "Question"),
                    type=q_item.get("type", "yes_no"),
                    answer_type=q_item.get("answer_type", "YES_NO"),
                    kpi_tag=q_item.get("kpi_tag"),
                    ask_reason_below=q_item.get("ask_reason_below"),
                    complaint_trigger_below=q_item.get("complaint_trigger_below"),
                    rating_min=q_item.get("rating_min"),
                    rating_max=q_item.get("rating_max"),
                    rating_labels=q_item.get("rating_labels"),
                    display_order=idx,
                )
                db.add(q)
                created_counts["questions"] += 1
            await db.flush()
            qnr_map[q_type] = qnr.id

        first_qnr_id = list(qnr_map.values())[0] if qnr_map else None

        # 4. FollowUp Programs
        for p_data in pack_payload.get("programs", []):
            p_code = p_data.get("code", "PSF").upper()
            prog_stmt = select(FollowUpProgram).where(
                FollowUpProgram.tenant_id == tenant_id,
                FollowUpProgram.brand_id == brand_id,
                FollowUpProgram.code == p_code,
            )
            prog = (await db.execute(prog_stmt)).scalar_one_or_none()
            if not prog:
                prog = FollowUpProgram(
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    code=p_code,
                    label=p_data.get("label", p_code),
                    enabled=p_data.get("enabled", True),
                    trigger=p_data.get("trigger", "ON_IMPORT"),
                    channel=p_data.get("channel", "PHONE"),
                    questionnaire_id=first_qnr_id,
                    rating_scale_id=first_scale_id,
                    max_attempts=p_data.get("max_attempts", 3),
                    retry_gap_hours=p_data.get("retry_gap_hours", 24),
                    sla_hours=p_data.get("sla_hours", 72),
                    sort_order=p_data.get("sort_order", 1),
                )
                db.add(prog)
                created_counts["programs"] += 1
        await db.flush()

        # 5. Outcome Rules
        for r_data in pack_payload.get("rules", []):
            r_name = r_data.get("name", "Outcome Rule")
            rule_stmt = select(OutcomeRule).where(
                OutcomeRule.tenant_id == tenant_id,
                OutcomeRule.brand_id == brand_id,
                OutcomeRule.name == r_name,
            )
            rule = (await db.execute(rule_stmt)).scalar_one_or_none()
            if not rule:
                rule = OutcomeRule(
                    tenant_id=tenant_id,
                    brand_id=brand_id,
                    name=r_name,
                    enabled=r_data.get("enabled", True),
                    priority=r_data.get("priority", 0),
                    conditions=r_data.get("conditions", {}),
                    actions=r_data.get("actions", {}),
                )
                db.add(rule)
                created_counts["rules"] += 1
        await db.flush()

        # 6. Custom Labels
        labels_map = pack_payload.get("labels", {})
        for l_key, l_val in labels_map.items():
            clean_k = l_key.strip().upper()
            lbl_stmt = select(LabelOverride).where(
                LabelOverride.tenant_id == tenant_id,
                LabelOverride.key == clean_k,
            )
            lbl = (await db.execute(lbl_stmt)).scalar_one_or_none()
            if not lbl:
                lbl = LabelOverride(
                    tenant_id=tenant_id,
                    key=clean_k,
                    language="en",
                    value=str(l_val),
                )
                db.add(lbl)
                created_counts["labels"] += 1
            else:
                lbl.value = str(l_val)
        await db.flush()

        # Invalidate caches
        await ConfigResolverService.invalidate_cache(tenant_id, "PROGRAMS")
        await ConfigResolverService.invalidate_cache(tenant_id, "LABELS")
        await db.commit()

        return {
            "status": "success",
            "message": f"Successfully cloned pack into dealership",
            "brand_id": str(brand_id),
            "created_counts": created_counts,
        }

    @classmethod
    async def export_dealership_config(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Exports full configuration of a dealership tenant as versioned JSON."""
        # 1. Programs
        prog_stmt = select(FollowUpProgram).where(FollowUpProgram.tenant_id == tenant_id, FollowUpProgram.is_deleted == False)
        programs = (await db.execute(prog_stmt)).scalars().all()

        # 2. Questionnaires & Questions
        qnr_stmt = select(Questionnaire).options(selectinload(Questionnaire.questions)).where(
            Questionnaire.tenant_id == tenant_id, Questionnaire.is_deleted == False
        )
        questionnaires = (await db.execute(qnr_stmt)).scalars().all()

        # 3. Scales
        scales_stmt = select(RatingScale).options(selectinload(RatingScale.bands)).where(
            RatingScale.tenant_id == tenant_id, RatingScale.is_active == True
        )
        scales = (await db.execute(scales_stmt)).scalars().all()

        # 4. Rules
        rules_stmt = select(OutcomeRule).where(OutcomeRule.tenant_id == tenant_id)
        rules = (await db.execute(rules_stmt)).scalars().all()

        # 5. Labels
        lbl_stmt = select(LabelOverride).where(LabelOverride.tenant_id == tenant_id)
        labels = (await db.execute(lbl_stmt)).scalars().all()

        return {
            "pack_version": "1.0.0",
            "name": "Exported Dealership Configuration",
            "tenant_id": str(tenant_id),
            "programs": [
                {
                    "code": p.code,
                    "label": p.label,
                    "enabled": p.enabled,
                    "trigger": p.trigger,
                    "channel": p.channel,
                    "max_attempts": p.max_attempts,
                    "retry_gap_hours": p.retry_gap_hours,
                    "sla_hours": p.sla_hours,
                    "sort_order": p.sort_order,
                }
                for p in programs
            ],
            "questionnaires": [
                {
                    "type": qnr.type,
                    "title": qnr.title,
                    "questions": [
                        {
                            "key": q.key,
                            "label": q.label,
                            "type": q.type,
                            "answer_type": q.answer_type,
                            "kpi_tag": q.kpi_tag,
                            "ask_reason_below": float(q.ask_reason_below) if q.ask_reason_below else None,
                            "complaint_trigger_below": float(q.complaint_trigger_below) if q.complaint_trigger_below else None,
                            "rating_min": q.rating_min,
                            "rating_max": q.rating_max,
                        }
                        for q in qnr.questions
                        if not q.is_deleted
                    ],
                }
                for qnr in questionnaires
            ],
            "scales": [
                {
                    "name": s.name,
                    "max_val": s.max_rating,
                    "bands": [
                        {
                            "name": b.label,
                            "status": b.derived_case_status,
                            "min_val": b.min_score,
                            "max_val": b.max_score,
                        }
                        for b in (s.bands or [])
                    ],
                }
                for s in scales
            ],
            "rules": [
                {
                    "name": r.name,
                    "enabled": r.enabled,
                    "priority": r.priority,
                    "conditions": r.conditions,
                    "actions": r.actions,
                }
                for r in rules
            ],
            "labels": {lbl.key: lbl.value for lbl in labels},
        }

    @classmethod
    async def create_dealership_with_pack(
        cls,
        db: AsyncSession,
        name: str,
        slug: str,
        brand_name: str,
        brand_code: str,
        branch_name: str,
        branch_code: str,
        admin_name: str,
        admin_email: str,
        admin_password: str,
        pack_code: str = "BLANK",
    ) -> Dict[str, Any]:
        """Onboards a brand new dealership tenant and clones the chosen pack."""
        # Check tenant slug
        stmt = select(Tenant).where(Tenant.slug == slug)
        if (await db.execute(stmt)).scalar_one_or_none():
            raise ValueError(f"Dealership slug '{slug}' already exists")

        # 1. Create Tenant
        tenant = Tenant(
            name=name,
            slug=slug,
            primary_color="#2563EB",
            is_active=True,
        )
        db.add(tenant)
        await db.flush()

        # 2. Create Brand
        brand = Brand(
            tenant_id=tenant.id,
            name=brand_name,
            code=brand_code.upper().strip(),
            is_active=True,
        )
        db.add(brand)
        await db.flush()

        # 3. Create Branch
        branch = Branch(
            tenant_id=tenant.id,
            brand_id=brand.id,
            name=branch_name,
            code=branch_code.upper().strip(),
            is_active=True,
        )
        db.add(branch)
        await db.flush()

        # 4. Copy system roles or create Dealer Admin role
        admin_role_stmt = select(Role).where(Role.name == "SUPER_ADMIN")
        admin_role = (await db.execute(admin_role_stmt)).scalars().first()
        if not admin_role:
            admin_role = Role(
                tenant_id=tenant.id,
                name="SUPER_ADMIN",
                hierarchy_level="L1",
                description="Super Admin",
                is_system_role=True,
            )
            db.add(admin_role)
            await db.flush()

        # 5. Create Admin User
        admin_user = User(
            tenant_id=tenant.id,
            role_id=admin_role.id,
            email=admin_email.lower().strip(),
            hashed_password=get_password_hash(admin_password),
            full_name=admin_name,
            is_active=True,
        )
        db.add(admin_user)
        await db.flush()

        # 6. Clone Config Pack
        pack_payload = cls.load_pack_json(pack_code)
        if not pack_payload:
            pack_payload = cls.load_pack_json("blank") or {
                "pack_version": "1.0.0",
                "programs": [{"code": "PSF", "label": "Post Service Follow-up", "enabled": True, "trigger": "ON_IMPORT", "channel": "PHONE"}],
                "scales": [],
                "questionnaires": [],
                "rules": [],
                "labels": {},
            }

        clone_res = await cls.clone_pack_to_dealership(
            db=db,
            tenant_id=tenant.id,
            pack_payload=pack_payload,
            brand_id=brand.id,
        )

        await db.commit()

        return {
            "status": "success",
            "message": f"Dealership '{name}' onboarded successfully with pack '{pack_code}'",
            "tenant_id": str(tenant.id),
            "brand_id": str(brand.id),
            "branch_id": str(branch.id),
            "admin_user_id": str(admin_user.id),
            "pack_cloned": pack_code,
            "clone_details": clone_res,
        }
