"""
================================================================================
FILE PURPOSE: Dealership Master Data Endpoints.
Provides endpoints for listing, creating, and updating OEM Brands, Branches,
Service Advisors, and column mapping templates.

KEY RESPONSIBILITIES:
- Lists and creates Brands (`GET/POST /masters/brands`).
- Lists and creates Branches (`GET/POST /masters/branches`).
- Lists Service Advisors (`GET /masters/advisors`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 403 Forbidden: 'brand.manage permission required'
  -> Cause: Attempted to add or edit a brand without required permissions.
  -> What should you do: Only Super Admin can create or edit OEM Brands.
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user, require, require_any, PermissionKey
from app.models.auth import User
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.crypto import encrypt_phone, hash_phone, decrypt_phone, mask_phone
from app.models.tenant import Brand, Branch, BranchContact
from app.models.additional import RatingScale, RatingScaleBand
from app.models.followup import CallStatus, CaseStatus
from app.schemas.master import (
    BrandCreate,
    BrandUpdate,
    BrandResponse,
    BranchCreate,
    BranchUpdate,
    BranchResponse,
    ComplaintCategoryCreate,
    ComplaintCategoryUpdate,
    ComplaintCategoryResponse,
    SettingUpdate,
    SettingResponse,
    BranchContactCreate,
    BranchContactUpdate,
    BranchContactResponse,
    BranchContactsOverviewResponse,
    RatingScaleBandUpdate,
    RatingScaleBandResponse,
    RatingScaleResponse,
    CallStatusCreate,
    CallStatusUpdate,
    CallStatusResponse,
    CaseStatusCreate,
    CaseStatusUpdate,
    CaseStatusResponse,
)
from app.services.master_service import (
    list_brands,
    get_brand_by_id,
    create_brand,
    update_brand,
    list_branches,
    get_branch_by_id,
    create_branch,
    update_branch,
    list_complaint_categories,
    create_complaint_category,
    get_tenant_settings,
    upsert_tenant_setting,
)

router = APIRouter(prefix="/masters", tags=["Masters & Dealership Configuration"])


# -------------------------------------------------------------
# Brands Endpoints
# -------------------------------------------------------------
@router.get("/brands", response_model=List[BrandResponse])
async def get_brands(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all automotive OEM brands under the current tenant."""
    brands = await list_brands(db, current_user.tenant_id)
    responses = []
    for b in brands:
        is_hyundai = "HYUNDAI" in b.name.upper() or b.code.upper() in ["HYUN", "HYUNDAI"]
        responses.append(
            BrandResponse(
                id=b.id,
                tenant_id=b.tenant_id,
                name=b.name,
                code=b.code,
                logo_url=b.logo_url,
                primary_color=b.primary_color,
                is_active=b.is_active,
                branches_count=len(b.branches or []),
                has_happiness_calling=is_hyundai,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
        )
    return responses


@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_new_brand(
    payload: BrandCreate,
    current_user: User = Depends(require(PermissionKey.BRAND_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Add a new brand to the dealer group."""
    norm_code = payload.code.strip().upper()
    existing_stmt = select(Brand).options(selectinload(Brand.branches)).where(
        Brand.tenant_id == current_user.tenant_id,
        Brand.code == norm_code,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        if existing.is_deleted:
            # Reactivate soft-deleted brand
            existing.name = payload.name.strip()
            existing.logo_url = payload.logo_url
            existing.primary_color = payload.primary_color
            existing.is_active = payload.is_active
            existing.is_deleted = False
            existing.deleted_at = None
            await db.commit()
            brand = existing
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Brand with code '{norm_code}' already exists ({existing.name}). Please use a unique code or edit the existing brand.",
            )
    else:
        brand = await create_brand(db, current_user.tenant_id, payload)

    is_hyundai = "HYUNDAI" in brand.name.upper() or brand.code.upper() in ["HYUN", "HYUNDAI"]
    return BrandResponse(
        id=brand.id,
        tenant_id=brand.tenant_id,
        name=brand.name,
        code=brand.code,
        logo_url=brand.logo_url,
        primary_color=brand.primary_color,
        is_active=brand.is_active,
        branches_count=len(brand.branches or []),
        has_happiness_calling=is_hyundai,
        created_at=brand.created_at,
        updated_at=brand.updated_at,
    )


@router.put("/brands/{brand_id}", response_model=BrandResponse)
async def update_brand_details(
    brand_id: uuid.UUID,
    payload: BrandUpdate,
    current_user: User = Depends(require(PermissionKey.BRAND_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    brand = await get_brand_by_id(db, current_user.tenant_id, brand_id)
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    if payload.code is not None:
        norm_code = payload.code.strip().upper()
        conflict_stmt = select(Brand).where(
            Brand.tenant_id == current_user.tenant_id,
            Brand.code == norm_code,
            Brand.id != brand_id,
            Brand.is_deleted == False,
        )
        if (await db.execute(conflict_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another brand with code '{norm_code}' already exists.",
            )

    updated = await update_brand(db, brand, payload)
    is_hyundai = "HYUNDAI" in updated.name.upper() or updated.code.upper() in ["HYUN", "HYUNDAI"]
    return BrandResponse(
        id=updated.id,
        tenant_id=updated.tenant_id,
        name=updated.name,
        code=updated.code,
        logo_url=updated.logo_url,
        primary_color=updated.primary_color,
        is_active=updated.is_active,
        branches_count=len(updated.branches or []),
        has_happiness_calling=is_hyundai,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/brands/{brand_id}", status_code=status.HTTP_200_OK)
async def delete_brand(
    brand_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.BRAND_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an OEM brand."""
    brand = await get_brand_by_id(db, current_user.tenant_id, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    brand.is_active = False
    brand.is_deleted = True
    await db.commit()
    return {"message": f"Brand '{brand.name}' deactivated successfully"}


# -------------------------------------------------------------
# Branches Endpoints
# -------------------------------------------------------------
@router.get("/branches", response_model=List[BranchResponse])
async def get_branches(
    brand_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List dealership workshop branches."""
    branches = await list_branches(db, current_user.tenant_id, brand_id)
    return [
        BranchResponse(
            id=br.id,
            tenant_id=br.tenant_id,
            brand_id=br.brand_id,
            brand_name=br.brand.name if br.brand else None,
            name=br.name,
            code=br.code,
            dms_code=br.dms_code,
            display_name=br.display_name,
            address=br.address,
            city=br.city,
            state=br.state,
            pincode=br.pincode,
            phone=br.phone,
            email=br.email,
            is_active=br.is_active,
            created_at=br.created_at,
            updated_at=br.updated_at,
        )
        for br in branches
    ]


@router.post("/branches", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_new_branch(
    payload: BranchCreate,
    current_user: User = Depends(require_any(PermissionKey.BRANCH_MANAGE, PermissionKey.BRAND_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    norm_code = payload.code.strip().upper()
    existing_stmt = select(Branch).options(selectinload(Branch.brand)).where(
        Branch.tenant_id == current_user.tenant_id,
        Branch.code == norm_code,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        if existing.is_deleted:
            existing.brand_id = payload.brand_id
            existing.name = payload.name.strip()
            existing.dms_code = payload.dms_code.strip() if payload.dms_code else None
            existing.display_name = payload.display_name.strip() if payload.display_name else None
            existing.address = payload.address
            existing.city = payload.city
            existing.state = payload.state
            existing.pincode = payload.pincode
            existing.phone = payload.phone
            existing.email = payload.email
            existing.is_active = payload.is_active
            existing.is_deleted = False
            existing.deleted_at = None
            await db.commit()
            branch = existing
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Branch with code '{norm_code}' already exists ({existing.name}). Please use a different code.",
            )
    else:
        branch = await create_branch(db, current_user.tenant_id, payload)

    return BranchResponse(
        id=branch.id,
        tenant_id=branch.tenant_id,
        brand_id=branch.brand_id,
        brand_name=branch.brand.name if branch.brand else None,
        name=branch.name,
        code=branch.code,
        dms_code=branch.dms_code,
        display_name=branch.display_name,
        address=branch.address,
        city=branch.city,
        state=branch.state,
        pincode=branch.pincode,
        phone=branch.phone,
        email=branch.email,
        is_active=branch.is_active,
        created_at=branch.created_at,
        updated_at=branch.updated_at,
    )


@router.put("/branches/{branch_id}", response_model=BranchResponse)
async def update_branch_details(
    branch_id: uuid.UUID,
    payload: BranchUpdate,
    current_user: User = Depends(require_any(PermissionKey.BRANCH_MANAGE, PermissionKey.BRAND_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update workshop branch details, DMS code, or status."""
    branch = await get_branch_by_id(db, current_user.tenant_id, branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    if payload.code is not None:
        norm_code = payload.code.strip().upper()
        conflict_stmt = select(Branch).where(
            Branch.tenant_id == current_user.tenant_id,
            Branch.code == norm_code,
            Branch.id != branch_id,
            Branch.is_deleted == False,
        )
        if (await db.execute(conflict_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another branch with code '{norm_code}' already exists.",
            )

    updated = await update_branch(db, branch, payload)
    return BranchResponse(
        id=updated.id,
        tenant_id=updated.tenant_id,
        brand_id=updated.brand_id,
        brand_name=updated.brand.name if updated.brand else None,
        name=updated.name,
        code=updated.code,
        dms_code=updated.dms_code,
        display_name=updated.display_name,
        address=updated.address,
        city=updated.city,
        state=updated.state,
        pincode=updated.pincode,
        phone=updated.phone,
        email=updated.email,
        is_active=updated.is_active,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@router.delete("/branches/{branch_id}", status_code=status.HTTP_200_OK)
async def delete_branch(
    branch_id: uuid.UUID,
    current_user: User = Depends(require_any(PermissionKey.BRANCH_MANAGE, PermissionKey.BRAND_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a workshop branch."""
    branch = await get_branch_by_id(db, current_user.tenant_id, branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    branch.is_active = False
    branch.is_deleted = True
    await db.commit()
    return {"message": f"Branch '{branch.name}' deactivated successfully"}


# -------------------------------------------------------------
# Complaint Categories Endpoints
# -------------------------------------------------------------
@router.get("/complaint-categories", response_model=List[ComplaintCategoryResponse])
async def get_complaint_categories(
    brand_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    categories = await list_complaint_categories(db, current_user.tenant_id, brand_id)
    return categories


@router.post("/complaint-categories", response_model=ComplaintCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_new_complaint_category(
    payload: ComplaintCategoryCreate,
    current_user: User = Depends(require(PermissionKey.DROPDOWN_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    return await create_complaint_category(db, current_user.tenant_id, payload)


# -------------------------------------------------------------
# Call Statuses & Case Statuses Endpoints
# -------------------------------------------------------------
@router.get("/call-statuses", response_model=List[CallStatusResponse])
async def get_call_statuses(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List call connection statuses (Connected, Not Connected, etc.)."""
    stmt = (
        select(CallStatus)
        .where(CallStatus.tenant_id == current_user.tenant_id)
        .order_by(CallStatus.name)
    )
    return (await db.execute(stmt)).scalars().all()


@router.post("/call-statuses", response_model=CallStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_call_status(
    payload: CallStatusCreate,
    current_user: User = Depends(require(PermissionKey.STATUS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    st = CallStatus(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        category=payload.category,
        counts_as_contacted=payload.counts_as_contacted,
        closes_followup=payload.closes_followup,
        retry_allowed=payload.retry_allowed,
        color=payload.color,
        is_active=payload.is_active,
    )
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


@router.put("/call-statuses/{status_id}", response_model=CallStatusResponse)
async def update_call_status(
    status_id: uuid.UUID,
    payload: CallStatusUpdate,
    current_user: User = Depends(require(PermissionKey.STATUS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CallStatus).where(CallStatus.tenant_id == current_user.tenant_id, CallStatus.id == status_id)
    st = (await db.execute(stmt)).scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Call status not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    await db.commit()
    await db.refresh(st)
    return st


@router.get("/case-statuses", response_model=List[CaseStatusResponse])
async def get_case_statuses(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List sentiment/operational case statuses (Delight, Satisfied, Non-Delight, Dissatisfied, etc.)."""
    stmt = (
        select(CaseStatus)
        .where(CaseStatus.tenant_id == current_user.tenant_id)
        .order_by(CaseStatus.name)
    )
    return (await db.execute(stmt)).scalars().all()


@router.post("/case-statuses", response_model=CaseStatusResponse, status_code=status.HTTP_201_CREATED)
async def create_case_status(
    payload: CaseStatusCreate,
    current_user: User = Depends(require(PermissionKey.STATUS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    st = CaseStatus(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        category=payload.category,
        counts_as_contacted=payload.counts_as_contacted,
        closes_followup=payload.closes_followup,
        retry_allowed=payload.retry_allowed,
        color=payload.color,
        is_active=payload.is_active,
    )
    db.add(st)
    await db.commit()
    await db.refresh(st)
    return st


@router.put("/case-statuses/{status_id}", response_model=CaseStatusResponse)
async def update_case_status(
    status_id: uuid.UUID,
    payload: CaseStatusUpdate,
    current_user: User = Depends(require(PermissionKey.STATUS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CaseStatus).where(CaseStatus.tenant_id == current_user.tenant_id, CaseStatus.id == status_id)
    st = (await db.execute(stmt)).scalar_one_or_none()
    if not st:
        raise HTTPException(status_code=404, detail="Case status not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    await db.commit()
    await db.refresh(st)
    return st


# -------------------------------------------------------------
# Tenant Settings Endpoints
# -------------------------------------------------------------
@router.get("/settings", response_model=Dict[str, Any])
async def get_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve tenant white-label configuration, SLA timers, and templates."""
    settings_dict = await get_tenant_settings(db, current_user.tenant_id)
    defaults = {
        "theme": {
            "primary_color": current_user.tenant.primary_color if current_user.tenant else "#2563EB",
            "dealer_name": current_user.tenant.name if current_user.tenant else "Apex Automotive Group",
            "logo_url": current_user.tenant.logo_url if current_user.tenant else None,
        },
        "sla_rules": {
            "default_sla_hours": 24,
            "escalation_interval_hours": 4,
            "reconfirmation_window_hours": 24,
        },
        "calling_rules": {
            "max_attempts": 3,
            "retry_interval_hours": 4,
            "happiness_trigger_days": [15, 30], # Hyundai only
        },
        "templates": {
            "sms_satisfaction": "Dear Customer, thank you for servicing your vehicle with us. For any assistance, please reply to this number.",
            "whatsapp_complaint_opened": "Hello {{customer_name}}, your complaint {{ticket_no}} has been registered. Our Service Manager is reviewing it.",
        }
    }
    defaults.update(settings_dict)
    return defaults


@router.put("/settings", response_model=Dict[str, Any])
async def update_settings(
    payload: SettingUpdate,
    current_user: User = Depends(require(PermissionKey.SETTINGS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update tenant configuration key."""
    await upsert_tenant_setting(db, current_user.tenant_id, payload.config_key, payload.config_value)
    return await get_settings(current_user=current_user, db=db)


# -------------------------------------------------------------
# Branch Contacts Endpoints
# -------------------------------------------------------------
@router.get("/branch-contacts", response_model=BranchContactsOverviewResponse)
async def get_branch_contacts(
    branch_id: Optional[uuid.UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List branch escalation contacts and surface missing contact warnings."""
    # 1. Fetch contacts
    query = (
        select(BranchContact)
        .options(selectinload(BranchContact.branch))
        .join(Branch, Branch.id == BranchContact.branch_id)
        .where(BranchContact.tenant_id == current_user.tenant_id)
    )
    if branch_id:
        query = query.where(BranchContact.branch_id == branch_id)
    query = query.order_by(Branch.name, BranchContact.name)
    contacts_res = await db.execute(query)
    contacts = contacts_res.scalars().all()

    contact_items = []
    contacted_branch_ids = set()
    for c in contacts:
        contacted_branch_ids.add(c.branch_id)
        raw_ph = decrypt_phone(c.phone) if c.phone else ""
        masked_ph = mask_phone(raw_ph) if raw_ph else "N/A"
        contact_items.append(
            BranchContactResponse(
                id=c.id,
                tenant_id=c.tenant_id,
                branch_id=c.branch_id,
                branch_name=c.branch.name if c.branch else None,
                branch_code=c.branch.code if c.branch else None,
                dms_code=c.branch.dms_code if c.branch else None,
                role=c.role,
                name=c.name,
                phone=raw_ph,
                phone_masked=masked_ph,
                email=c.email,
                notify_on=c.notify_on,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    # 2. Identify branches without any registered contacts
    all_branches_res = await db.execute(
        select(Branch)
        .options(selectinload(Branch.brand))
        .where(Branch.tenant_id == current_user.tenant_id, Branch.is_active == True)
    )
    all_branches = all_branches_res.scalars().all()
    missing = []
    for br in all_branches:
        if br.id not in contacted_branch_ids:
            missing.append({
                "branch_id": str(br.id),
                "name": br.name,
                "code": br.code,
                "dms_code": br.dms_code,
                "display_name": br.display_name or br.name,
                "brand_name": br.brand.name if br.brand else "Unassigned",
            })

    return BranchContactsOverviewResponse(
        items=contact_items,
        total_contacts=len(contact_items),
        missing_branches=missing,
        missing_count=len(missing),
    )


@router.post("/branch-contacts", response_model=BranchContactResponse, status_code=status.HTTP_201_CREATED)
async def create_new_branch_contact(
    payload: BranchContactCreate,
    current_user: User = Depends(require(PermissionKey.BRANCH_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Add a new branch service contact."""
    clean_ph = payload.phone.strip()
    contact = BranchContact(
        tenant_id=current_user.tenant_id,
        branch_id=payload.branch_id,
        role=payload.role,
        name=payload.name,
        phone=encrypt_phone(clean_ph),
        phone_hash=hash_phone(clean_ph),
        email=payload.email,
        notify_on=payload.notify_on,
        is_active=payload.is_active,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)

    # Load branch for response
    br_stmt = select(Branch).where(Branch.id == contact.branch_id)
    branch_obj = (await db.execute(br_stmt)).scalar_one_or_none()

    raw_ph = decrypt_phone(contact.phone)
    return BranchContactResponse(
        id=contact.id,
        tenant_id=contact.tenant_id,
        branch_id=contact.branch_id,
        branch_name=branch_obj.name if branch_obj else None,
        branch_code=branch_obj.code if branch_obj else None,
        dms_code=branch_obj.dms_code if branch_obj else None,
        role=contact.role,
        name=contact.name,
        phone=raw_ph,
        phone_masked=mask_phone(raw_ph),
        email=contact.email,
        notify_on=contact.notify_on,
        is_active=contact.is_active,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@router.put("/branch-contacts/{contact_id}", response_model=BranchContactResponse)
async def update_branch_contact(
    contact_id: uuid.UUID,
    payload: BranchContactUpdate,
    current_user: User = Depends(require(PermissionKey.BRANCH_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update branch service contact."""
    c_stmt = select(BranchContact).where(
        BranchContact.tenant_id == current_user.tenant_id,
        BranchContact.id == contact_id,
    )
    contact = (await db.execute(c_stmt)).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Branch contact not found")

    if payload.role is not None:
        contact.role = payload.role
    if payload.name is not None:
        contact.name = payload.name
    if payload.phone is not None:
        clean_ph = payload.phone.strip()
        contact.phone = encrypt_phone(clean_ph)
        contact.phone_hash = hash_phone(clean_ph)
    if payload.email is not None:
        contact.email = payload.email
    if payload.notify_on is not None:
        contact.notify_on = payload.notify_on
    if payload.is_active is not None:
        contact.is_active = payload.is_active

    await db.commit()
    await db.refresh(contact)

    # Load branch for response
    br_stmt = select(Branch).where(Branch.id == contact.branch_id)
    branch_obj = (await db.execute(br_stmt)).scalar_one_or_none()

    raw_ph = decrypt_phone(contact.phone)
    return BranchContactResponse(
        id=contact.id,
        tenant_id=contact.tenant_id,
        branch_id=contact.branch_id,
        branch_name=branch_obj.name if branch_obj else None,
        branch_code=branch_obj.code if branch_obj else None,
        dms_code=branch_obj.dms_code if branch_obj else None,
        role=contact.role,
        name=contact.name,
        phone=raw_ph,
        phone_masked=mask_phone(raw_ph),
        email=contact.email,
        notify_on=contact.notify_on,
        is_active=contact.is_active,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@router.delete("/branch-contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch_contact(
    contact_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.BRANCH_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a branch service contact."""
    c_stmt = select(BranchContact).where(
        BranchContact.tenant_id == current_user.tenant_id,
        BranchContact.id == contact_id,
    )
    contact = (await db.execute(c_stmt)).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Branch contact not found")
    await db.delete(contact)
    await db.commit()


# -------------------------------------------------------------
# Rating Scales Endpoints
# -------------------------------------------------------------
@router.get("/rating-scales", response_model=List[RatingScaleResponse])
async def get_rating_scales(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all brand rating scales and their bands."""
    query = (
        select(RatingScale)
        .options(selectinload(RatingScale.brand), selectinload(RatingScale.bands))
        .where(RatingScale.tenant_id == current_user.tenant_id)
        .order_by(RatingScale.name)
    )
    scales_res = await db.execute(query)
    scales = scales_res.scalars().all()

    responses = []
    for s in scales:
        bands_query = (
            select(RatingScaleBand)
            .where(RatingScaleBand.scale_id == s.id)
            .order_by(RatingScaleBand.min_score)
        )
        bands_res = await db.execute(bands_query)
        bands = bands_res.scalars().all()

        responses.append(
            RatingScaleResponse(
                id=s.id,
                tenant_id=s.tenant_id,
                brand_id=s.brand_id,
                brand_name=s.brand.name if s.brand else None,
                brand_code=s.brand.code if s.brand else None,
                name=s.name,
                max_rating=s.max_rating,
                is_active=s.is_active,
                bands=[
                    RatingScaleBandResponse(
                        id=b.id,
                        scale_id=b.scale_id,
                        min_score=b.min_score,
                        max_score=b.max_score,
                        label=b.label,
                        derived_case_status=b.derived_case_status,
                        is_delight=b.is_delight,
                        is_complaint_trigger=b.is_complaint_trigger,
                        created_at=b.created_at,
                    )
                    for b in bands
                ],
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
    return responses


@router.put("/rating-scales/{scale_id}/bands/{band_id}", response_model=RatingScaleBandResponse)
async def update_rating_scale_band(
    scale_id: uuid.UUID,
    band_id: uuid.UUID,
    payload: RatingScaleBandUpdate,
    current_user: User = Depends(require(PermissionKey.STATUS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Configure rating scale band (e.g. toggle complaint trigger for score 9)."""
    b_stmt = select(RatingScaleBand).where(
        RatingScaleBand.tenant_id == current_user.tenant_id,
        RatingScaleBand.scale_id == scale_id,
        RatingScaleBand.id == band_id,
    )
    band = (await db.execute(b_stmt)).scalar_one_or_none()
    if not band:
        raise HTTPException(status_code=404, detail="Rating scale band not found")

    if payload.label is not None:
        band.label = payload.label
    if payload.derived_case_status is not None:
        band.derived_case_status = payload.derived_case_status
    if payload.is_delight is not None:
        band.is_delight = payload.is_delight
    if payload.is_complaint_trigger is not None:
        band.is_complaint_trigger = payload.is_complaint_trigger
    if payload.min_score is not None:
        band.min_score = payload.min_score
    if payload.max_score is not None:
        band.max_score = payload.max_score

    await db.commit()
    await db.refresh(band)

    return RatingScaleBandResponse(
        id=band.id,
        scale_id=band.scale_id,
        min_score=band.min_score,
        max_score=band.max_score,
        label=band.label,
        derived_case_status=band.derived_case_status,
        is_delight=band.is_delight,
        is_complaint_trigger=band.is_complaint_trigger,
        created_at=band.created_at,
    )


