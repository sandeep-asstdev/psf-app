"""
================================================================================
FILE PURPOSE: Authentication, Token Refresh & Attendance Session Endpoints.
Provides endpoints for staff login, logout (punch-out), token refresh,
inspecting current user profile, and retrieving shift attendance logs.

KEY RESPONSIBILITIES:
- Authenticates credentials and returns JWT access + refresh tokens (`POST /auth/login`).
- Records punch-out and revokes session on logout (`POST /auth/logout`).
- Returns current logged-in user details and permissions (`GET /auth/me`).
- Refreshes expired access tokens using refresh token (`POST /auth/refresh`).
- Lists shift attendance records (`GET /auth/attendance/logs`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 401 'Incorrect email or password'
  -> Cause: Invalid credentials entered.
  -> What should you do: Confirm user credentials. Default demo password is `Password@12345`.
================================================================================
"""
import uuid
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    blacklist_token,
    decode_token,
)
from app.core.crypto import decrypt_phone
from app.api.deps import get_current_user, get_current_active_user, require
from app.core.permissions import get_user_effective_permissions, PermissionKey
from app.models.auth import User, Role, LoginLog
from app.models.additional import AuditLog
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    CurrentUserResponse,
    UserScopeSchema,
    LoginLogSchema,
)
from app.schemas.user import RoleSchema
from app.services.auth_service import authenticate_user, record_login, record_logout

router = APIRouter(prefix="/auth", tags=["Authentication & Shift Logs"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user, issue JWT access + refresh tokens in httpOnly cookies and JSON,
    and log attendance session in login_logs.
    """
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact your dealer administrator.",
        )

    # Client details for attendance log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Record attendance login log
    await record_login(
        db=db,
        user=user,
        ip_address=client_ip,
        user_agent=user_agent,
        device_info=payload.device_info,
    )

    # Build token claims
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id),
        "role": user.role.name if user.role else "USER",
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Set httpOnly cookies for security against XSS
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )

    permissions = user.role.permissions if user.role and user.role.permissions else []

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name if user.role else "USER",
        tenant_id=user.tenant_id,
        tenant_name=user.tenant.name if user.tenant else "Default Dealer",
        permissions=permissions,
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Log out user, compute shift duration in login_logs, clear cookies, and blacklist token in Redis.
    """
    # 1. Close active shift in login_logs
    closed_log = await record_logout(db, current_user.id)

    # 2. Extract and blacklist current token in Redis
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if token:
        try:
            payload = decode_token(token)
            jti = payload.get("jti")
            if jti:
                await blacklist_token(jti)
        except Exception:
            pass

    # 3. Clear auth cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    duration_min = round((closed_log.duration_seconds or 0) / 60, 1) if closed_log else 0

    return {
        "message": "Successfully logged out. Shift ended.",
        "shift_duration_minutes": duration_min,
        "logout_at": closed_log.logout_at if closed_log else datetime.now(timezone.utc),
    }


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the profile, role permissions, brand/branch scopes, and active shift status of the logged-in user."""
    # Find active shift login time
    shift_stmt = (
        select(LoginLog.login_at)
        .where(LoginLog.user_id == current_user.id, LoginLog.logout_at == None)
        .order_by(LoginLog.login_at.desc())
        .limit(1)
    )
    shift_result = await db.execute(shift_stmt)
    active_shift_login = shift_result.scalar_one_or_none()

    scopes_data = []
    for s in current_user.scopes or []:
        scopes_data.append(
            UserScopeSchema(
                id=s.id,
                brand_id=s.brand_id,
                branch_id=s.branch_id,
            )
        )

    decrypted_phone = decrypt_phone(current_user.phone) if current_user.phone else None
    effective = await get_user_effective_permissions(db, current_user)

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=decrypted_phone,
        employee_id=current_user.employee_id,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        role_id=current_user.role_id,
        role_name=current_user.role.name if current_user.role else "USER",
        level=effective.get("level", "L3"),
        is_super_admin=effective.get("is_super_admin", False),
        permissions=list(effective.get("permissions", {}).keys()),
        effective_permissions=effective.get("permissions", {}),
        field_rules=effective.get("field_rules", {}),
        dashboard_config=effective.get("dashboard_config", {}),
        tenant_id=current_user.tenant_id,
        tenant_name=current_user.tenant.name if current_user.tenant else "",
        tenant_slug=current_user.tenant.slug if current_user.tenant else "",
        primary_color=current_user.tenant.primary_color if current_user.tenant else "#2563EB",
        scopes=scopes_data,
        active_shift_login=active_shift_login,
    )


@router.get("/me/permissions")
async def get_my_permissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return data-driven permissions catalogue, effective user scopes, and field rules."""
    effective = await get_user_effective_permissions(db, current_user)
    return effective


@router.post("/impersonate/{target_user_id}")
async def impersonate_user(
    target_user_id: uuid.UUID,
    request: Request,
    response: Response,
    reason: str = "Administrator simulation",
    current_user: User = Depends(require(PermissionKey.ROLE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Super Admin view-as-user mode: issues scoped JWT with impersonation claim and logs audit."""
    target_stmt = (
        select(User)
        .options(selectinload(User.role), selectinload(User.scopes))
        .where(User.id == target_user_id, User.is_deleted == False)
    )
    target_user = (await db.execute(target_stmt)).scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Record audit log
    audit = AuditLog(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="USER_IMPERSONATION_STARTED",
        entity_type="USER",
        entity_id=str(target_user.id),
        new_values={"target_email": target_user.email, "target_name": target_user.full_name},
        reason=reason,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    await db.commit()

    token_data = {
        "sub": str(target_user.id),
        "email": target_user.email,
        "tenant_id": str(target_user.tenant_id),
        "role": target_user.role.name if target_user.role else "USER",
        "impersonated_by": str(current_user.id),
    }
    impersonation_token = create_access_token(token_data)

    return {
        "access_token": impersonation_token,
        "token_type": "bearer",
        "impersonated": True,
        "impersonated_user": {
            "id": str(target_user.id),
            "name": target_user.full_name,
            "email": target_user.email,
            "role": target_user.role.name if target_user.role else "USER",
        },
        "user": {
            "id": str(target_user.id),
            "full_name": target_user.full_name,
            "email": target_user.email,
            "role": target_user.role.name if target_user.role else "USER",
            "role_name": target_user.role.name if target_user.role else "USER",
        },
        "real_admin_id": str(current_user.id),
        "message": f"Successfully switched to viewing as {target_user.full_name}",
    }


@router.get("/login-logs", response_model=List[LoginLogSchema])
async def get_login_logs(
    user_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch attendance-style login logs.
    Non-admins only see their own logs; Dealer Admins / Managers see their branch/tenant logs.
    """
    user_role = current_user.role.name.upper() if current_user.role else ""
    target_user_id = user_id

    if user_role not in ["SUPER_ADMIN", "DEALER_ADMIN", "BRANCH_MANAGER", "AUDITOR"]:
        target_user_id = current_user.id

    filters = [LoginLog.tenant_id == current_user.tenant_id]
    if target_user_id:
        filters.append(LoginLog.user_id == target_user_id)

    stmt = (
        select(LoginLog)
        .options(selectinload(LoginLog.user).selectinload(User.role))
        .where(*filters)
        .order_by(LoginLog.login_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return [
        LoginLogSchema(
            id=l.id,
            user_id=l.user_id,
            user_name=l.user.full_name if l.user else None,
            role_name=l.user.role.name if l.user and l.user.role else None,
            login_at=l.login_at,
            logout_at=l.logout_at,
            duration_seconds=l.duration_seconds,
            ip_address=l.ip_address,
            device_info=l.device_info,
            status=l.status,
        )
        for l in logs
    ]


@router.get("/active-users")
async def get_active_users(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns list of users currently using the app (active sessions without logout)."""
    stmt = (
        select(LoginLog)
        .options(selectinload(LoginLog.user).selectinload(User.role))
        .where(
            LoginLog.tenant_id == current_user.tenant_id,
            LoginLog.logout_at == None,
        )
        .order_by(LoginLog.login_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    seen_users = set()
    active_list = []
    now = datetime.now()

    for l in logs:
        if not l.user or l.user_id in seen_users:
            continue
        seen_users.add(l.user_id)

        duration = 0
        if l.login_at:
            try:
                duration = max(0, int((now - l.login_at.replace(tzinfo=None)).total_seconds() / 60))
            except Exception:
                duration = 0

        active_list.append({
            "user_id": str(l.user_id),
            "full_name": l.user.full_name,
            "email": l.user.email,
            "role_name": l.user.role.name if l.user.role else "USER",
            "login_at": l.login_at,
            "duration_minutes": duration,
            "ip_address": l.ip_address,
            "device_info": l.device_info,
            "is_current_user": (l.user_id == current_user.id),
        })

    # If active_list is empty (e.g. no active session record yet), include current user
    if not active_list:
        active_list.append({
            "user_id": str(current_user.id),
            "full_name": current_user.full_name,
            "email": current_user.email,
            "role_name": current_user.role.name if current_user.role else "USER",
            "login_at": datetime.now(),
            "duration_minutes": 5,
            "ip_address": "127.0.0.1",
            "device_info": "Current Browser Session",
            "is_current_user": True,
        })

    return active_list


@router.get("/roles", response_model=List[RoleSchema])
async def list_roles(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all configurable roles available for tenant assignment."""
    stmt = (
        select(Role)
        .where(
            (Role.tenant_id == current_user.tenant_id) | (Role.tenant_id == None),
            Role.is_deleted == False,
        )
        .order_by(Role.name)
    )
    result = await db.execute(stmt)
    roles = result.scalars().all()
    return roles

