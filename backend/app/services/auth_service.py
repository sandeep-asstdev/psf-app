import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_password
from app.models.auth import User, LoginLog
from app.models.tenant import Tenant

logger = logging.getLogger("psf.auth_service")


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """Verify user email and password."""
    stmt = (
        select(User)
        .options(
            selectinload(User.role),
            selectinload(User.scopes),
            selectinload(User.tenant),
        )
        .where(User.email == email.lower().strip(), User.is_deleted == False)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def record_login(
    db: AsyncSession,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    device_info: Optional[str] = None,
) -> LoginLog:
    """Record an attendance-style login event."""
    log = LoginLog(
        tenant_id=user.tenant_id,
        user_id=user.id,
        login_at=datetime.now(timezone.utc),
        ip_address=ip_address,
        user_agent=user_agent,
        device_info=device_info,
        status="SUCCESS",
    )
    db.add(log)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(log)
    return log


async def record_logout(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[LoginLog]:
    """Find the most recent active login log for the user and record shift logout."""
    stmt = (
        select(LoginLog)
        .where(
            LoginLog.user_id == user_id,
            LoginLog.logout_at == None,
        )
        .order_by(LoginLog.login_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    log = result.scalar_one_or_none()

    if log:
        now = datetime.now(timezone.utc)
        log.logout_at = now
        duration = int((now - log.login_at.replace(tzinfo=timezone.utc if log.login_at.tzinfo is None else log.login_at.tzinfo)).total_seconds())
        log.duration_seconds = max(0, duration)
        log.status = "LOGGED_OUT"
        await db.commit()
        await db.refresh(log)
        return log
    return None
