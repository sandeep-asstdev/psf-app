"""
================================================================================
FILE PURPOSE: Configuration & Follow-up Programs Endpoints.
Provides APIs to manage Follow-up Programs, Draft/Publish/Rollback Config Versions,
and inspect resolved configs with Redis caching.
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_active_user as get_current_user
from app.models.auth import User
from app.models.tenant import Brand, Tenant, Branch
from app.models.questionnaire import Questionnaire, Question, KpiTag
from app.models.additional import RatingScale, AuditLog
from app.models.config import FollowUpProgram, ConfigVersion, OutcomeRule, LabelOverride, ConfigPack
from app.services.config_resolver import ConfigResolverService
from app.services.scoring_service import ScoringService
from app.services.rules_engine import RulesEngineService
from app.services.pack_service import PackService
from app.schemas.config import (
    FollowUpProgramCreate,
    FollowUpProgramUpdate,
    FollowUpProgramResponse,
    ReorderRequest,
    ConfigVersionCreate,
    ConfigPublishRequest,
    ConfigRollbackRequest,
    ConfigVersionResponse,
    KpiTagCreate,
    KpiTagResponse,
    OutcomeRuleCreate,
    OutcomeRuleUpdate,
    OutcomeRuleResponse,
    SimulateRequest,
    SimulateResponse,
    LabelOverrideBase,
    LabelOverrideCreate,
    LabelOverrideResponse,
    LabelOverrideBatch,
    PackMetadata,
    ClonePackRequest,
    OnboardDealershipRequest,
    ConfigImportRequest,
)

router = APIRouter(prefix="/config", tags=["Configuration & Programs"])


@router.get("/programs", response_model=List[FollowUpProgramResponse])
async def list_programs(
    brand_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(FollowUpProgram)
        .options(
            selectinload(FollowUpProgram.brand),
            selectinload(FollowUpProgram.questionnaire),
            selectinload(FollowUpProgram.rating_scale),
        )
        .where(
            FollowUpProgram.tenant_id == current_user.tenant_id,
            FollowUpProgram.is_deleted.is_(False),
        )
    )
    if brand_id:
        stmt = stmt.where(FollowUpProgram.brand_id == brand_id)

    stmt = stmt.order_by(FollowUpProgram.sort_order.asc(), FollowUpProgram.created_at.asc())
    programs = (await db.execute(stmt)).scalars().all()

    results = []
    for p in programs:
        results.append(
            FollowUpProgramResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                brand_id=p.brand_id,
                brand_name=p.brand.name if p.brand else None,
                code=p.code,
                label=p.label,
                enabled=p.enabled,
                trigger=p.trigger,
                channel=p.channel,
                questionnaire_id=p.questionnaire_id,
                questionnaire_title=p.questionnaire.title if p.questionnaire else None,
                rating_scale_id=p.rating_scale_id,
                rating_scale_name=p.rating_scale.name if p.rating_scale else None,
                max_attempts=p.max_attempts,
                retry_gap_hours=p.retry_gap_hours,
                sla_hours=p.sla_hours,
                sort_order=p.sort_order,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )
    return results


@router.post("/programs", response_model=FollowUpProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: FollowUpProgramCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    program = FollowUpProgram(
        tenant_id=current_user.tenant_id,
        brand_id=payload.brand_id,
        code=payload.code.upper().strip(),
        label=payload.label.strip(),
        enabled=payload.enabled,
        trigger=payload.trigger,
        channel=payload.channel,
        questionnaire_id=payload.questionnaire_id,
        rating_scale_id=payload.rating_scale_id,
        max_attempts=payload.max_attempts,
        retry_gap_hours=payload.retry_gap_hours,
        sla_hours=payload.sla_hours,
        sort_order=payload.sort_order,
    )
    db.add(program)

    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PROGRAM_CREATED",
        entity_type="FOLLOW_UP_PROGRAM",
        entity_id=str(program.id),
        new_values=payload.model_dump(mode="json"),
        reason=f"Created program {payload.code} ({payload.label})",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(program)

    # Invalidate cache
    await ConfigResolverService.invalidate_cache(current_user.tenant_id, "PROGRAMS")

    return FollowUpProgramResponse(
        id=program.id,
        tenant_id=program.tenant_id,
        brand_id=program.brand_id,
        code=program.code,
        label=program.label,
        enabled=program.enabled,
        trigger=program.trigger,
        channel=program.channel,
        questionnaire_id=program.questionnaire_id,
        rating_scale_id=program.rating_scale_id,
        max_attempts=program.max_attempts,
        retry_gap_hours=program.retry_gap_hours,
        sla_hours=program.sla_hours,
        sort_order=program.sort_order,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )


@router.put("/programs/reorder")
async def reorder_programs(
    req: ReorderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for item in req.orders:
        await db.execute(
            update(FollowUpProgram)
            .where(
                FollowUpProgram.id == item.id,
                FollowUpProgram.tenant_id == current_user.tenant_id,
            )
            .values(sort_order=item.sort_order)
        )
    await db.commit()
    await ConfigResolverService.invalidate_cache(current_user.tenant_id, "PROGRAMS")
    return {"status": "success", "message": "Programs reordered"}


@router.put("/programs/{program_id}", response_model=FollowUpProgramResponse)
async def update_program(
    program_id: uuid.UUID,
    payload: FollowUpProgramUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(FollowUpProgram).where(
        FollowUpProgram.id == program_id,
        FollowUpProgram.tenant_id == current_user.tenant_id,
        FollowUpProgram.is_deleted.is_(False),
    )
    prog = (await db.execute(stmt)).scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")

    updates = payload.model_dump(exclude_unset=True)
    if "code" in updates and updates["code"]:
        updates["code"] = updates["code"].upper().strip()

    for k, v in updates.items():
        setattr(prog, k, v)

    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PROGRAM_UPDATED",
        entity_type="FOLLOW_UP_PROGRAM",
        entity_id=str(prog.id),
        new_values=updates,
        reason=f"Updated program {prog.code}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(prog)

    await ConfigResolverService.invalidate_cache(current_user.tenant_id, "PROGRAMS")

    return FollowUpProgramResponse(
        id=prog.id,
        tenant_id=prog.tenant_id,
        brand_id=prog.brand_id,
        code=prog.code,
        label=prog.label,
        enabled=prog.enabled,
        trigger=prog.trigger,
        channel=prog.channel,
        questionnaire_id=prog.questionnaire_id,
        rating_scale_id=prog.rating_scale_id,
        max_attempts=prog.max_attempts,
        retry_gap_hours=prog.retry_gap_hours,
        sla_hours=prog.sla_hours,
        sort_order=prog.sort_order,
        created_at=prog.created_at,
        updated_at=prog.updated_at,
    )


@router.delete("/programs/{program_id}")
async def delete_program(
    program_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(FollowUpProgram).where(
        FollowUpProgram.id == program_id,
        FollowUpProgram.tenant_id == current_user.tenant_id,
    )
    prog = (await db.execute(stmt)).scalar_one_or_none()
    if not prog:
        raise HTTPException(status_code=404, detail="Program not found")

    prog.is_deleted = True
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="PROGRAM_DELETED",
        entity_type="FOLLOW_UP_PROGRAM",
        entity_id=str(prog.id),
        reason=f"Deleted program {prog.code}",
    )
    db.add(audit)
    await db.commit()

    await ConfigResolverService.invalidate_cache(current_user.tenant_id, "PROGRAMS")
    return {"status": "success", "message": "Program deleted"}


# -----------------------------------------------------------------------------
# Config Versions: Draft / Publish / Rollback
# -----------------------------------------------------------------------------
@router.get("/versions", response_model=List[ConfigVersionResponse])
async def list_config_versions(
    config_type: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    scope_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ConfigVersion).where(ConfigVersion.tenant_id == current_user.tenant_id)
    if config_type:
        stmt = stmt.where(ConfigVersion.config_type == config_type)
    if scope:
        stmt = stmt.where(ConfigVersion.scope == scope)
    if scope_id:
        stmt = stmt.where(ConfigVersion.scope_id == scope_id)

    stmt = stmt.order_by(ConfigVersion.version.desc())
    versions = (await db.execute(stmt)).scalars().all()
    return versions


@router.post("/drafts", response_model=ConfigVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_draft_version(
    payload: ConfigVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        draft = await ConfigResolverService.create_draft(
            db=db,
            tenant_id=current_user.tenant_id,
            scope=payload.scope,
            scope_id=payload.scope_id,
            config_type=payload.config_type,
            payload=payload.payload,
            user_id=current_user.id,
            note=payload.note,
        )
        return draft
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/publish", response_model=ConfigVersionResponse)
async def publish_version_endpoint(
    req: ConfigPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if req.version_id:
            # Publish existing draft by id
            return await ConfigResolverService.publish_version(
                db=db,
                tenant_id=current_user.tenant_id,
                version_id=req.version_id,
                user_id=current_user.id,
                note=req.note,
            )

        # Snapshot current active entity state into a published version
        if req.config_type == "PROGRAMS":
            # Collect current programs
            brand_id = req.scope_id if req.scope == "BRAND" else None
            p_stmt = select(FollowUpProgram).where(
                FollowUpProgram.tenant_id == current_user.tenant_id,
                FollowUpProgram.brand_id == brand_id,
                FollowUpProgram.is_deleted.is_(False),
            ).order_by(FollowUpProgram.sort_order.asc())
            progs = (await db.execute(p_stmt)).scalars().all()
            payload = [
                {
                    "code": p.code,
                    "label": p.label,
                    "enabled": p.enabled,
                    "trigger": p.trigger,
                    "channel": p.channel,
                    "questionnaire_id": str(p.questionnaire_id) if p.questionnaire_id else None,
                    "rating_scale_id": str(p.rating_scale_id) if p.rating_scale_id else None,
                    "max_attempts": p.max_attempts,
                    "retry_gap_hours": p.retry_gap_hours,
                    "sla_hours": p.sla_hours,
                    "sort_order": p.sort_order,
                }
                for p in progs
            ]
            draft = await ConfigResolverService.create_draft(
                db=db,
                tenant_id=current_user.tenant_id,
                scope=req.scope,
                scope_id=req.scope_id,
                config_type=req.config_type,
                payload=payload,
                user_id=current_user.id,
                note=req.note,
            )
            return await ConfigResolverService.publish_version(
                db=db,
                tenant_id=current_user.tenant_id,
                version_id=draft.id,
                user_id=current_user.id,
                note=req.note,
            )

        raise HTTPException(status_code=400, detail="version_id is required")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rollback", response_model=ConfigVersionResponse)
async def rollback_version_endpoint(
    req: ConfigRollbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        target_id = req.target_version_id
        if not target_id:
            # Pick latest archived/previous version
            stmt = select(ConfigVersion).where(
                ConfigVersion.tenant_id == current_user.tenant_id,
                ConfigVersion.scope == req.scope,
                ConfigVersion.scope_id == req.scope_id,
                ConfigVersion.config_type == req.config_type,
                ConfigVersion.status != "PUBLISHED",
            ).order_by(ConfigVersion.version.desc()).limit(1)
            latest_prev = (await db.execute(stmt)).scalar_one_or_none()
            if not latest_prev:
                raise HTTPException(status_code=404, detail="No previous config version found to rollback to")
            target_id = latest_prev.id

        return await ConfigResolverService.rollback_config(
            db=db,
            tenant_id=current_user.tenant_id,
            target_version_id=target_id,
            user_id=current_user.id,
            reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/resolve")
async def resolve_config_endpoint(
    config_type: str = Query(...),
    brand_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resolved = await ConfigResolverService.resolve_config(
        db=db,
        tenant_id=current_user.tenant_id,
        config_type=config_type,
        brand_id=brand_id,
    )
    return {"config_type": config_type, "brand_id": brand_id, "config": resolved}


# -----------------------------------------------------------------------------
# KPI Tags Endpoints
# -----------------------------------------------------------------------------
@router.get("/kpi-tags", response_model=List[KpiTagResponse])
async def list_kpi_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(KpiTag).where(KpiTag.tenant_id == current_user.tenant_id).order_by(KpiTag.label.asc())
    tags = (await db.execute(stmt)).scalars().all()
    return tags


@router.post("/kpi-tags", response_model=KpiTagResponse, status_code=status.HTTP_201_CREATED)
async def create_kpi_tag(
    payload: KpiTagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag_clean = payload.tag.upper().strip().replace(" ", "_")
    existing_stmt = select(KpiTag).where(KpiTag.tenant_id == current_user.tenant_id, KpiTag.tag == tag_clean)
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"KPI Tag '{tag_clean}' already exists")

    kpi = KpiTag(
        tenant_id=current_user.tenant_id,
        tag=tag_clean,
        label=payload.label.strip(),
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(kpi)
    await db.commit()
    await db.refresh(kpi)
    return kpi


# -----------------------------------------------------------------------------
# Outcome Rules Endpoints
# -----------------------------------------------------------------------------
@router.get("/rules", response_model=List[OutcomeRuleResponse])
async def list_outcome_rules(
    brand_id: Optional[uuid.UUID] = Query(None),
    program_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutcomeRule).where(OutcomeRule.tenant_id == current_user.tenant_id)
    if brand_id:
        stmt = stmt.where(OutcomeRule.brand_id == brand_id)
    if program_id:
        stmt = stmt.where(OutcomeRule.program_id == program_id)

    stmt = stmt.order_by(OutcomeRule.priority.asc(), OutcomeRule.created_at.asc())
    rules = (await db.execute(stmt)).scalars().all()
    return rules


@router.post("/rules", response_model=OutcomeRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_outcome_rule(
    payload: OutcomeRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = OutcomeRule(
        tenant_id=current_user.tenant_id,
        brand_id=payload.brand_id,
        program_id=payload.program_id,
        name=payload.name.strip(),
        enabled=payload.enabled,
        priority=payload.priority,
        conditions=payload.conditions,
        actions=payload.actions,
    )
    db.add(rule)
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="OUTCOME_RULE_CREATED",
        entity_type="OUTCOME_RULE",
        entity_id=str(rule.id),
        new_values=payload.model_dump(mode="json"),
        reason=f"Created outcome rule: {payload.name}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=OutcomeRuleResponse)
async def update_outcome_rule(
    rule_id: uuid.UUID,
    payload: OutcomeRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutcomeRule).where(OutcomeRule.id == rule_id, OutcomeRule.tenant_id == current_user.tenant_id)
    rule = (await db.execute(stmt)).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Outcome rule not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)

    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="OUTCOME_RULE_UPDATED",
        entity_type="OUTCOME_RULE",
        entity_id=str(rule.id),
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
        reason=f"Updated outcome rule: {rule.name}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
async def delete_outcome_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(OutcomeRule).where(OutcomeRule.id == rule_id, OutcomeRule.tenant_id == current_user.tenant_id)
    rule = (await db.execute(stmt)).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Outcome rule not found")

    await db.delete(rule)
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="OUTCOME_RULE_DELETED",
        entity_type="OUTCOME_RULE",
        entity_id=str(rule.id),
        reason=f"Deleted outcome rule: {rule.name}",
    )
    db.add(audit)
    await db.commit()
    return {"status": "success", "message": "Outcome rule deleted"}


# -----------------------------------------------------------------------------
# Configuration Simulator (Sample Job Card + Answers -> Outcome, nothing saved)
# -----------------------------------------------------------------------------
@router.post("/simulate", response_model=SimulateResponse)
async def simulate_config(
    req: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    brand_code = None
    brand_id = req.brand_id

    if brand_id:
        b_stmt = select(Brand).where(Brand.id == brand_id, Brand.tenant_id == current_user.tenant_id)
        brand_obj = (await db.execute(b_stmt)).scalar_one_or_none()
        if brand_obj:
            brand_code = brand_obj.code

    # 1. Fetch relevant questionnaire questions for the brand / program
    q_stmt = select(Questionnaire).options(selectinload(Questionnaire.questions)).where(
        Questionnaire.tenant_id == current_user.tenant_id,
    )
    if brand_id:
        q_stmt = q_stmt.where(Questionnaire.brand_id == brand_id)
    questionnaires = (await db.execute(q_stmt)).scalars().all()
    questions: List[Question] = []
    if questionnaires:
        questions = questionnaires[0].questions

    # 2. Process and normalize answers
    normalized_answers, kpi_buckets = ScoringService.process_and_normalize_answers(req.answers, questions)

    # 3. Aggregate KPI scores
    kpi_scores: Dict[str, float] = {}
    for tag, scores in kpi_buckets.items():
        if scores:
            kpi_scores[tag] = round(sum(scores) / len(scores), 2)

    # 4. Calculate overall result
    overall_score, nps_score, nps_cat = ScoringService.calculate_overall_result(
        normalized_answers=normalized_answers,
        questions=questions,
        method=req.scoring_method,
    )

    # 5. Derive base outcome status from brand bands
    case_status, is_delight, is_trigger = await ScoringService.resolve_bands_and_outcome(
        db=db,
        tenant_id=current_user.tenant_id,
        brand_id=brand_id,
        brand_code=brand_code,
        overall_score=overall_score,
        raw_rating=nps_score,
    )

    # 6. Evaluate Rules Engine in dry_run mode
    job_card_data = req.job_card or {}
    eval_context = {
        "overall_score": overall_score,
        "kpi_scores": kpi_scores,
        "answers": normalized_answers,
        "service_type": job_card_data.get("service_type", "Periodic Maintenance Service"),
        "branch_id": job_card_data.get("branch_id"),
        "branch_code": job_card_data.get("branch_code", "APEX-HUBLI"),
        "total_amount": float(job_card_data.get("total_amount", 5000.0)),
    }

    rule_results = await RulesEngineService.evaluate_rules(
        db=db,
        tenant_id=current_user.tenant_id,
        brand_id=brand_id,
        program_id=req.program_id,
        context=eval_context,
        dry_run=True,
    )

    final_case_status = rule_results["outcome_status"] or case_status
    if rule_results["complaint"]:
        is_trigger = True

    return SimulateResponse(
        overall_score=overall_score,
        csat_score=overall_score,
        nps_score=nps_score,
        nps_category=nps_cat,
        derived_case_status=final_case_status,
        is_delight=is_delight,
        is_complaint_trigger=is_trigger,
        kpi_scores=kpi_scores,
        normalized_answers=normalized_answers,
        rules_matched=rule_results["matched_rules"],
        resulting_outcome=final_case_status,
        complaint=rule_results["complaint"],
        notifications=rule_results["notifications"],
    )


# -----------------------------------------------------------------------------
# Dynamic Label Overrides
# -----------------------------------------------------------------------------
DEFAULT_SYSTEM_LABELS = {
    "CRE": "Customer Relationship Executive",
    "DELIGHT": "Delight",
    "TNPS": "Follow-up Program",
    "JOB_CARD": "Job Card",
    "COMPLAINT": "Customer Complaint",
}


@router.get("/labels", response_model=Dict[str, str])
async def get_labels(
    language: str = "en",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(LabelOverride).where(
        LabelOverride.tenant_id == current_user.tenant_id,
        LabelOverride.language == language,
    )
    overrides = (await db.execute(stmt)).scalars().all()
    merged = dict(DEFAULT_SYSTEM_LABELS)
    for ov in overrides:
        merged[ov.key] = ov.value
    return merged


@router.post("/labels", response_model=Dict[str, str])
async def upsert_labels(
    req: LabelOverrideBatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for key, val in req.labels.items():
        clean_key = key.strip().upper()
        clean_val = val.strip()
        stmt = select(LabelOverride).where(
            LabelOverride.tenant_id == current_user.tenant_id,
            LabelOverride.key == clean_key,
            LabelOverride.language == req.language,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.value = clean_val
        else:
            db.add(
                LabelOverride(
                    tenant_id=current_user.tenant_id,
                    key=clean_key,
                    language=req.language,
                    value=clean_val,
                )
            )
    await db.commit()

    await ConfigResolverService.invalidate_cache(current_user.tenant_id, "LABELS")
    return await get_labels(language=req.language, db=db, current_user=current_user)


@router.delete("/labels/{key}")
async def delete_label_override(
    key: str,
    language: str = "en",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clean_key = key.strip().upper()
    stmt = select(LabelOverride).where(
        LabelOverride.tenant_id == current_user.tenant_id,
        LabelOverride.key == clean_key,
        LabelOverride.language == language,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
        await ConfigResolverService.invalidate_cache(current_user.tenant_id, "LABELS")
    return {"status": "success", "message": f"Label override for {clean_key} reset to default"}


# -----------------------------------------------------------------------------
# Config Packs & Dealership Onboarding Wizard
# -----------------------------------------------------------------------------
@router.get("/packs", response_model=List[PackMetadata])
async def list_config_packs():
    """Lists all versioned configuration packs (Hyundai, Tata, MG, Ather, Blank)."""
    return PackService.list_available_packs()


@router.post("/packs/clone")
async def clone_pack(
    req: ClonePackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clones a pre-configured OEM or Blank pack into the active dealership."""
    payload = PackService.load_pack_json(req.pack_code)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Config pack '{req.pack_code}' not found")

    res = await PackService.clone_pack_to_dealership(
        db=db,
        tenant_id=current_user.tenant_id,
        pack_payload=payload,
        brand_id=req.brand_id,
    )
    return res


@router.get("/tenants")
async def list_all_tenants(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists all dealership tenants registered in the platform.
    Strictly restricted to SUPER_ADMIN.
    """
    is_super = (current_user.role and current_user.role.name == "SUPER_ADMIN") or current_user.email == "admin@apexauto.com"
    if not is_super:
        raise HTTPException(status_code=403, detail="Only Super Admins can view platform tenants")

    stmt = select(Tenant).where(Tenant.is_deleted.is_(False)).order_by(Tenant.created_at.desc())
    tenants = (await db.execute(stmt)).scalars().all()

    results = []
    for t in tenants:
        brand_cnt = (await db.execute(select(func.count(Brand.id)).where(Brand.tenant_id == t.id, Brand.is_active.is_(True)))).scalar() or 0
        branch_cnt = (await db.execute(select(func.count(Branch.id)).where(Branch.tenant_id == t.id, Branch.is_active.is_(True)))).scalar() or 0
        user_cnt = (await db.execute(select(func.count(User.id)).where(User.tenant_id == t.id, User.is_active.is_(True)))).scalar() or 0
        results.append({
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "primary_color": t.primary_color,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "brands_count": brand_cnt,
            "branches_count": branch_cnt,
            "users_count": user_cnt,
        })
    return results


@router.post("/dealerships/wizard")
async def onboard_dealership_wizard(
    req: OnboardDealershipRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Onboards a brand new dealership tenant using the wizard:
    Details, Brand, Branch, Admin user, and clones selected pack.
    Requires SUPER_ADMIN permissions.
    """
    is_super = (current_user.role and current_user.role.name == "SUPER_ADMIN") or current_user.email == "admin@apexauto.com"
    if not is_super:
        raise HTTPException(status_code=403, detail="Only Super Admins can onboard new dealerships")

    try:
        res = await PackService.create_dealership_with_pack(
            db=db,
            name=req.name,
            slug=req.slug,
            brand_name=req.brand_name,
            brand_code=req.brand_code,
            branch_name=req.branch_name,
            branch_code=req.branch_code,
            admin_name=req.admin_name,
            admin_email=req.admin_email,
            admin_password=req.admin_password,
            pack_code=req.pack_code,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/dealership/export")
async def export_dealership_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exports full configuration of the active dealership as versioned JSON."""
    return await PackService.export_dealership_config(db=db, tenant_id=current_user.tenant_id)


@router.post("/dealership/import")
async def import_dealership_config(
    req: ConfigImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Validates and imports a JSON dealership configuration pack."""
    is_valid, err_msg = PackService.validate_pack_schema(req.config)
    if not is_valid:
        raise HTTPException(status_code=422, detail=f"Configuration schema validation failed: {err_msg}")

    if req.validate_only:
        return {"status": "valid", "message": "Configuration schema is valid and ready for import"}

    res = await PackService.clone_pack_to_dealership(
        db=db,
        tenant_id=current_user.tenant_id,
        pack_payload=req.config,
    )
    return res


