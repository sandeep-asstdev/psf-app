"""
================================================================================
FILE PURPOSE: User Accounts & Role Management Service.
Provides business logic for creating personnel user accounts, updating passwords,
assigning roles, and configuring explicit branch/brand data scopes.

KEY RESPONSIBILITIES:
- Creates new dealership personnel users with hashed passwords (`create_user`).
- Updates user profiles, active status, and role assignments (`update_user`).
- Assigns explicit branch or brand access scopes (`set_user_scopes`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: User cannot log in after creation
  -> Cause: Password was hashed incorrectly or user was marked inactive.
  -> What should you do: Verify is_active is True and test logging in with the chosen credentials.
================================================================================
"""
import uuid
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_password_hash
from app.core.crypto import encrypt_phone, decrypt_phone, hash_phone
from app.models.auth import User, Role, UserScope
from app.models.tenant import Brand, Branch
from app.schemas.user import UserCreateRequest, UserUpdateRequest


async def list_users(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    role_id: Optional[uuid.UUID] = None,
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[User], int]:
    """List users scoped to tenant with optional filters and scopes count."""
    filters = [User.tenant_id == tenant_id, User.is_deleted == False]

    if role_id:
        filters.append(User.role_id == role_id)
    if is_active is not None:
        filters.append(User.is_active == is_active)
    if search:
        search_fmt = f"%{search.strip()}%"
        filters.append(
            (User.full_name.ilike(search_fmt)) | (User.email.ilike(search_fmt)) | (User.employee_id.ilike(search_fmt))
        )

    # Base query
    stmt = (
        select(User)
        .options(
            selectinload(User.role),
            selectinload(User.scopes),
        )
        .where(and_(*filters))
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_stmt = select(func.count(User.id)).where(and_(*filters))

    result = await db.execute(stmt)
    users = result.scalars().all()

    total_count = (await db.execute(count_stmt)).scalar() or 0

    return users, total_count


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Optional[User]:
    stmt = (
        select(User)
        .options(
            selectinload(User.role),
            selectinload(User.scopes),
        )
        .where(User.id == user_id, User.tenant_id == tenant_id, User.is_deleted == False)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: UserCreateRequest,
) -> User:
    """Create a new user with encrypted phone and mapped brand/branch scopes."""
    hashed_pwd = get_password_hash(payload.password)
    enc_phone = encrypt_phone(payload.phone) if payload.phone else None
    h_phone = hash_phone(payload.phone) if payload.phone else None

    user = User(
        tenant_id=tenant_id,
        role_id=payload.role_id,
        email=payload.email.lower().strip(),
        hashed_password=hashed_pwd,
        full_name=payload.full_name.strip(),
        phone=enc_phone,
        phone_hash=h_phone,
        employee_id=payload.employee_id,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Assign brand/branch scopes
    if payload.brand_ids:
        for b_id in payload.brand_ids:
            scope = UserScope(
                tenant_id=tenant_id,
                user_id=user.id,
                brand_id=b_id,
                branch_id=None,
            )
            db.add(scope)

    if payload.branch_ids:
        for br_id in payload.branch_ids:
            scope = UserScope(
                tenant_id=tenant_id,
                user_id=user.id,
                brand_id=None,
                branch_id=br_id,
            )
            db.add(scope)

    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    user: User,
    payload: UserUpdateRequest,
) -> User:
    """Update user fields and synchronize scopes."""
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.phone is not None:
        user.phone = encrypt_phone(payload.phone)
        user.phone_hash = hash_phone(payload.phone)
    if payload.employee_id is not None:
        user.employee_id = payload.employee_id
    if payload.role_id is not None:
        user.role_id = payload.role_id
    if payload.is_active is not None:
        user.is_active = payload.is_active

    # Scopes update if provided
    if payload.brand_ids is not None or payload.branch_ids is not None:
        # Delete existing scopes
        del_stmt = select(UserScope).where(UserScope.user_id == user.id)
        existing_scopes = (await db.execute(del_stmt)).scalars().all()
        for s in existing_scopes:
            await db.delete(s)

        if payload.brand_ids:
            for b_id in payload.brand_ids:
                db.add(UserScope(tenant_id=user.tenant_id, user_id=user.id, brand_id=b_id))
        if payload.branch_ids:
            for br_id in payload.branch_ids:
                db.add(UserScope(tenant_id=user.tenant_id, user_id=user.id, branch_id=br_id))

    await db.commit()
    await db.refresh(user)
    return user


async def reset_user_password(db: AsyncSession, user: User, new_password: str) -> None:
    user.hashed_password = get_password_hash(new_password)
    await db.commit()
