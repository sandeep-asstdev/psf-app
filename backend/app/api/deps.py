"""
================================================================================
FILE PURPOSE: FastAPI Route Dependencies & Security Gates.
Provides reusable dependency injection functions for FastAPI endpoints:
retrieving current database session (`get_db`), extracting authenticated user from JWT token
(`get_current_user`), verifying active account status, and enforcing permission checks (`require`).

KEY RESPONSIBILITIES:
- Injects active asynchronous database sessions (`get_db`).
- Validates Bearer JWT access tokens and fetches the requesting User from database (`get_current_user`).
- Enforces role permission checks (`require(PermissionKey.CALL_VIEW)`).
- Enforces multi-permission checks (`require_any`, `require_all`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 401 Unauthorized: 'Not authenticated' or 'Invalid token'
  -> Cause: Missing or expired Authorization Bearer token header in the HTTP request.
  -> What should you do: Log in again at /login or verify the frontend is passing `Authorization: Bearer <token>` in headers.
- Error: HTTP 403 Forbidden: 'Insufficient permissions'
  -> Cause: The user's role does not possess the required permission key.
  -> What should you do: Check the user's role permissions in the Admin Console Role Matrix.
================================================================================
"""
import uuid
import logging
from typing import Optional, List, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import decode_token, is_token_blacklisted
from app.models.auth import User, Role, UserScope
from app.models.tenant import Tenant

logger = logging.getLogger("psf.deps")

# Optional bearer header scheme (we also check httpOnly cookies)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    token_auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract JWT token from Authorization header OR httpOnly 'access_token' cookie.
    Enforces token validity, Redis blacklist status, and fetches user with role and scopes.
    """
    token: Optional[str] = None
    if token_auth and token_auth.credentials:
        token = token_auth.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        # Check blacklist
        jti = payload.get("jti")
        if jti and await is_token_blacklisted(jti):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked/logged out")

        user_id = uuid.UUID(user_id_str)
    except Exception as e:
        logger.warning(f"Failed to authenticate token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user with role, scopes and tenant
    stmt = (
        select(User)
        .options(
            selectinload(User.role),
            selectinload(User.scopes),
            selectinload(User.tenant),
        )
        .where(User.id == user_id, User.is_deleted == False)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user account")

    # Instate tenant_id in request state for convenient tenant scoping downstream
    request.state.tenant_id = user.tenant_id
    request.state.user_id = user.id

    return user


from app.core.permissions import (
    require,
    require_any,
    get_user_effective_permissions,
    apply_data_scope,
    PermissionKey,
    DataScope,
)

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is deactivated")
    return current_user


def require_role(allowed_roles: List[str]) -> Callable:
    """Legacy role checker retained for backward compatibility; prefer data-driven require(PermissionKey)."""
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_role = current_user.role.name.upper() if current_user.role else ""
        if user_role == "SUPER_ADMIN" or user_role in [r.upper() for r in allowed_roles]:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Requires one of roles: {allowed_roles}",
        )
    return role_checker


def require_permissions(required_permissions: List[str]) -> Callable:
    """Dependency factory checking user permission strings."""
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        user_role = current_user.role.name.upper() if current_user.role else ""
        if user_role == "SUPER_ADMIN":
            return current_user

        granted = set(current_user.role.permissions if current_user.role and current_user.role.permissions else [])
        missing = [p for p in required_permissions if p not in granted]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {missing}",
            )
        return current_user
    return permission_checker

