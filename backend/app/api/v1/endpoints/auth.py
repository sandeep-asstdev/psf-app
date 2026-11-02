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
from app.api.deps import get_current_user, get_current_active_user
from app.models.auth import User, Role, LoginLog
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
            jti = payload.get("jti", str(current_user.id))
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
        permissions=current_user.role.permissions if current_user.role else [],
        tenant_id=current_user.tenant_id,
        tenant_name=current_user.tenant.name if current_user.tenant else "",
        tenant_slug=current_user.tenant.slug if current_user.tenant else "",
        primary_color=current_user.tenant.primary_color if current_user.tenant else "#2563EB",
        scopes=scopes_data,
        active_shift_login=active_shift_login,
    )


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
