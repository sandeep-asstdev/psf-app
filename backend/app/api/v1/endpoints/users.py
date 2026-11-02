import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
import io
from app.core.database import get_db
from app.core.crypto import decrypt_phone
from app.api.deps import get_current_active_user, require_role
from app.models.auth import User, Role, UserScope
from app.schemas.user import (
    UserCreateRequest,
    UserUpdateRequest,
    PasswordResetRequest,
    UserListItem,
    UserDetailResponse,
    RoleSchema,
)
from app.schemas.auth import UserScopeSchema
from app.services.user_service import (
    list_users,
    create_user,
    get_user_by_id,
    update_user,
    reset_user_password,
)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=dict)
async def get_users(
    role_id: Optional[uuid.UUID] = None,
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_role(["SUPER_ADMIN", "DEALER_ADMIN", "BRAND_MANAGER", "BRANCH_MANAGER", "AUDITOR"])),
    db: AsyncSession = Depends(get_db),
):
    """List users in tenant with filters and pagination."""
    skip = (page - 1) * page_size
    users, total = await list_users(
        db=db,
        tenant_id=current_user.tenant_id,
        role_id=role_id,
        brand_id=brand_id,
        branch_id=branch_id,
        search=search,
        is_active=is_active,
        skip=skip,
        limit=page_size,
    )

    items = [
        UserListItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            phone=decrypt_phone(u.phone) if u.phone else None,
            employee_id=u.employee_id,
            is_active=u.is_active,
            role_id=u.role_id,
            role_name=u.role.name if u.role else "USER",
            scopes_count=len(u.scopes or []),
            last_login_at=u.last_login_at,
            created_at=u.created_at,
        )
        for u in users
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    payload: UserCreateRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "DEALER_ADMIN", "BRAND_MANAGER"])),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user within the tenant."""
    # Check duplicate email in tenant
    dup_stmt = select(User).where(User.tenant_id == current_user.tenant_id, User.email == payload.email.lower().strip())
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{payload.email}' already exists in this dealership group",
        )

    # Check role
    role_stmt = select(Role).where(Role.id == payload.role_id)
    role = (await db.execute(role_stmt)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified role not found")

    new_user = await create_user(db=db, tenant_id=current_user.tenant_id, payload=payload)
    return await get_user_details(user_id=new_user.id, current_user=current_user, db=db)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user_details(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "DEALER_ADMIN", "BRAND_MANAGER", "BRANCH_MANAGER", "AUDITOR"])),
    db: AsyncSession = Depends(get_db),
):
    """Get single user profile and assigned scopes."""
    user = await get_user_by_id(db=db, user_id=user_id, tenant_id=current_user.tenant_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    scopes_data = [
        UserScopeSchema(id=s.id, brand_id=s.brand_id, branch_id=s.branch_id)
        for s in user.scopes or []
    ]

    return UserDetailResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        phone=decrypt_phone(user.phone) if user.phone else None,
        employee_id=user.employee_id,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        role=RoleSchema(
            id=user.role.id,
            name=user.role.name,
            description=user.role.description,
            permissions=user.role.permissions or [],
            is_system=user.role.is_system,
        ),
        scopes=scopes_data,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user_details(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "DEALER_ADMIN", "BRAND_MANAGER"])),
    db: AsyncSession = Depends(get_db),
):
    """Update user information and brand/branch scopes."""
    user = await get_user_by_id(db=db, user_id=user_id, tenant_id=current_user.tenant_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated = await update_user(db=db, user=user, payload=payload)
    return await get_user_details(user_id=updated.id, current_user=current_user, db=db)


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: uuid.UUID,
    payload: PasswordResetRequest,
    current_user: User = Depends(require_role(["SUPER_ADMIN", "DEALER_ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Reset password for a user account."""
    user = await get_user_by_id(db=db, user_id=user_id, tenant_id=current_user.tenant_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if len(payload.new_password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    await reset_user_password(db=db, user=user, new_password=payload.new_password)
    return {"message": f"Password reset successfully for user {user.email}"}


@router.post("/bulk-import")
async def bulk_import_users(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["SUPER_ADMIN", "DEALER_ADMIN"])),
    db: AsyncSession = Depends(get_db),
):
    """Bulk import dealership users from CSV or Excel file."""
    content = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV or Excel files supported")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse file: {e}")

    # Expected columns: email, full_name, role_name, phone, employee_id, password
    required_cols = ["email", "full_name", "role_name"]
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required column in import sheet: '{col}'",
            )

    # Fetch tenant roles mapping
    roles_stmt = select(Role).where(
        (Role.tenant_id == current_user.tenant_id) | (Role.tenant_id == None),
        Role.is_deleted == False,
    )
    roles = (await db.execute(roles_stmt)).scalars().all()
    roles_by_name = {r.name.upper(): r.id for r in roles}

    success_count = 0
    errors = []

    for idx, row in df.iterrows():
        email = str(row["email"]).strip()
        full_name = str(row["full_name"]).strip()
        role_name = str(row["role_name"]).strip().upper()
        phone = str(row.get("phone", "")).strip() or None
        emp_id = str(row.get("employee_id", "")).strip() or None
        password = str(row.get("password", "Welcome@123")).strip()

        if role_name not in roles_by_name:
            errors.append(f"Row {idx+2}: Role '{role_name}' does not exist")
            continue

        # Check existing
        existing_stmt = select(User).where(User.tenant_id == current_user.tenant_id, User.email == email.lower())
        if (await db.execute(existing_stmt)).scalar_one_or_none():
            errors.append(f"Row {idx+2}: User with email '{email}' already exists")
            continue

        try:
            req = UserCreateRequest(
                email=email,
                password=password,
                full_name=full_name,
                phone=phone,
                employee_id=emp_id,
                role_id=roles_by_name[role_name],
            )
            await create_user(db=db, tenant_id=current_user.tenant_id, payload=req)
            success_count += 1
        except Exception as e:
            errors.append(f"Row {idx+2}: Error creating user: {e}")

    return {
        "total_rows": len(df),
        "imported_count": success_count,
        "failed_count": len(errors),
        "errors": errors[:50],
    }
