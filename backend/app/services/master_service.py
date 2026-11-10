"""
================================================================================
FILE PURPOSE: Dealership Master Data Management Service.
Provides database operations for managing OEM Brands, dealer Branches, workshops,
service types, and DMS column mapping templates.

KEY RESPONSIBILITIES:
- Lists, creates, and updates Brands and Branches.
- Enforces uniqueness rules on Brand codes and Branch codes.
- Manages DMS column mapping templates for various dealership software formats.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: IntegrityError: Brand code already exists
  -> Cause: Attempted to create a brand with a duplicate code.
  -> What should you do: Use a unique 4-letter brand code (e.g. HYUN, TATA, MGMT).
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.tenant import Brand, Branch, Setting
from app.models.complaint import ComplaintCategory
from app.schemas.master import (
    BrandCreate,
    BrandUpdate,
    BranchCreate,
    BranchUpdate,
    ComplaintCategoryCreate,
    ComplaintCategoryUpdate,
)


# -------------------------------------------------------------
# Brands Service
# -------------------------------------------------------------
async def list_brands(db: AsyncSession, tenant_id: uuid.UUID) -> List[Brand]:
    stmt = (
        select(Brand)
        .options(selectinload(Brand.branches))
        .where(Brand.tenant_id == tenant_id, Brand.is_deleted == False)
        .order_by(Brand.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_brand_by_id(db: AsyncSession, tenant_id: uuid.UUID, brand_id: uuid.UUID) -> Optional[Brand]:
    stmt = (
        select(Brand)
        .options(selectinload(Brand.branches))
        .where(Brand.id == brand_id, Brand.tenant_id == tenant_id, Brand.is_deleted == False)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_brand(db: AsyncSession, tenant_id: uuid.UUID, payload: BrandCreate) -> Brand:
    brand = Brand(
        tenant_id=tenant_id,
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        logo_url=payload.logo_url,
        primary_color=payload.primary_color,
        is_active=payload.is_active,
    )
    db.add(brand)
    await db.commit()
    stmt = select(Brand).options(selectinload(Brand.branches)).where(Brand.id == brand.id)
    return (await db.execute(stmt)).scalar_one()


async def update_brand(db: AsyncSession, brand: Brand, payload: BrandUpdate) -> Brand:
    if payload.name is not None:
        brand.name = payload.name.strip()
    if payload.code is not None:
        brand.code = payload.code.strip().upper()
    if payload.logo_url is not None:
        brand.logo_url = payload.logo_url
    if payload.primary_color is not None:
        brand.primary_color = payload.primary_color
    if payload.is_active is not None:
        brand.is_active = payload.is_active

    await db.commit()
    stmt = select(Brand).options(selectinload(Brand.branches)).where(Brand.id == brand.id)
    return (await db.execute(stmt)).scalar_one()


# -------------------------------------------------------------
# Branches Service
# -------------------------------------------------------------
async def list_branches(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    brand_id: Optional[uuid.UUID] = None,
) -> List[Branch]:
    filters = [Branch.tenant_id == tenant_id, Branch.is_deleted == False]
    if brand_id:
        filters.append(Branch.brand_id == brand_id)

    stmt = (
        select(Branch)
        .options(selectinload(Branch.brand))
        .where(and_(*filters))
        .order_by(Branch.name)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_branch_by_id(db: AsyncSession, tenant_id: uuid.UUID, branch_id: uuid.UUID) -> Optional[Branch]:
    stmt = (
        select(Branch)
        .options(selectinload(Branch.brand))
        .where(Branch.id == branch_id, Branch.tenant_id == tenant_id, Branch.is_deleted == False)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_branch(db: AsyncSession, tenant_id: uuid.UUID, payload: BranchCreate) -> Branch:
    branch = Branch(
        tenant_id=tenant_id,
        brand_id=payload.brand_id,
        name=payload.name.strip(),
        code=payload.code.strip().upper(),
        dms_code=payload.dms_code.strip() if payload.dms_code else None,
        display_name=payload.display_name.strip() if payload.display_name else None,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        pincode=payload.pincode,
        phone=payload.phone,
        email=payload.email,
        is_active=payload.is_active,
    )
    db.add(branch)
    await db.commit()
    stmt = select(Branch).options(selectinload(Branch.brand)).where(Branch.id == branch.id)
    return (await db.execute(stmt)).scalar_one()


async def update_branch(db: AsyncSession, branch: Branch, payload: BranchUpdate) -> Branch:
    for field, val in payload.model_dump(exclude_unset=True).items():
        if field == "code" and val:
            setattr(branch, field, val.strip().upper())
        elif field in ["name", "dms_code", "display_name"] and val is not None:
            setattr(branch, field, val.strip())
        else:
            setattr(branch, field, val)
    await db.commit()
    stmt = select(Branch).options(selectinload(Branch.brand)).where(Branch.id == branch.id)
    return (await db.execute(stmt)).scalar_one()


# -------------------------------------------------------------
# Complaint Categories Service
# -------------------------------------------------------------
async def list_complaint_categories(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    brand_id: Optional[uuid.UUID] = None,
) -> List[ComplaintCategory]:
    filters = [ComplaintCategory.tenant_id == tenant_id, ComplaintCategory.is_deleted == False]
    if brand_id:
        filters.append((ComplaintCategory.brand_id == brand_id) | (ComplaintCategory.brand_id == None))

    stmt = select(ComplaintCategory).where(and_(*filters)).order_by(ComplaintCategory.name)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_complaint_category(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: ComplaintCategoryCreate,
) -> ComplaintCategory:
    category = ComplaintCategory(
        tenant_id=tenant_id,
        brand_id=payload.brand_id,
        name=payload.name.strip(),
        default_sla_hours=payload.default_sla_hours,
        severity_level=payload.severity_level.upper(),
        is_active=payload.is_active,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# -------------------------------------------------------------
# Settings Service
# -------------------------------------------------------------
async def get_tenant_settings(db: AsyncSession, tenant_id: uuid.UUID) -> Dict[str, Any]:
    stmt = select(Setting).where(Setting.tenant_id == tenant_id)
    result = await db.execute(stmt)
    settings_records = result.scalars().all()
    return {s.config_key: s.config_value for s in settings_records}


async def upsert_tenant_setting(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    key: str,
    value: Dict[str, Any],
) -> Setting:
    stmt = select(Setting).where(Setting.tenant_id == tenant_id, Setting.config_key == key)
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.config_value = value
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        setting = Setting(tenant_id=tenant_id, config_key=key, config_value=value)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
        return setting

