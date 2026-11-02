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
        jti = payload.get("jti", user_id_str)
        if await is_token_blacklisted(jti):
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


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is deactivated")
    return current_user


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory restricting endpoints to specific role names."""
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
