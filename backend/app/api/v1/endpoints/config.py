"""
================================================================================
FILE PURPOSE: Configuration & Follow-up Programs Endpoints.
Provides APIs to manage Follow-up Programs, Draft/Publish/Rollback Config Versions,
and inspect resolved configs with Redis caching.
================================================================================
"""
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_active_user as get_current_user
from app.models.auth import User
from app.models.tenant import Brand
from app.models.questionnaire import Questionnaire
from app.models.additional import RatingScale, AuditLog
from app.models.config import FollowUpProgram, ConfigVersion
from app.services.config_resolver import ConfigResolverService
from app.schemas.config import (
    FollowUpProgramCreate,
    FollowUpProgramUpdate,
    FollowUpProgramResponse,
    ReorderRequest,
    ConfigVersionCreate,
    ConfigPublishRequest,
    ConfigRollbackRequest,
    ConfigVersionResponse,
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
