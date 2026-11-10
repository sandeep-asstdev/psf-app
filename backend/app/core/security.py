"""
================================================================================
FILE PURPOSE: Password Hashing & JWT Authentication Tokens.
This file handles securing passwords with Passlib Bcrypt hashing and creating / decoding
JSON Web Tokens (JWT) for user authentication sessions.

KEY RESPONSIBILITIES:
- Hashes plain-text passwords securely using bcrypt with automatic salting (`get_password_hash`).
- Verifies entered login passwords against stored database hashes (`verify_password`).
- Generates JWT Access Tokens (short-lived) and Refresh Tokens (long-lived) (`create_access_token`).
- Decodes and validates JWT signatures (`decode_token`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: jwt.exceptions.ExpiredSignatureError: Signature has expired
  -> Cause: The user's access token has timed out (default 60 minutes).
  -> What should you do: The frontend should automatically refresh the token using /auth/refresh or redirect the user to /login to log in again.
- Error: jwt.exceptions.InvalidTokenError: Could not validate credentials
  -> Cause: The token is malformed or signed with a different SECRET_KEY.
  -> What should you do: Ensure SECRET_KEY has not changed in .env. Log out and log in again with valid credentials.
================================================================================
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt

# Fix for passlib compatibility with newer bcrypt versions
if not hasattr(bcrypt, "__about__"):
    class _BcryptAbout:
        __version__ = getattr(bcrypt, "__version__", "4.0.1")
    bcrypt.__about__ = _BcryptAbout()

from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger("psf.security")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for a plain password."""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT refresh token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise


async def blacklist_token(token_jti: str, expire_seconds: int = 3600 * 24) -> None:
    """Add a token JTI / signature to Redis blacklist upon logout."""
    try:
        r = await get_redis()
        await r.setex(f"blacklist:token:{token_jti}", expire_seconds, "1")
    except Exception as e:
        logger.error(f"Failed to blacklist token in Redis: {e}")


async def is_token_blacklisted(token_jti: str) -> bool:
    """Check if token JTI is blacklisted."""
    try:
        r = await get_redis()
        exists = await r.exists(f"blacklist:token:{token_jti}")
        return exists > 0
    except Exception as e:
        logger.error(f"Error checking token blacklist in Redis: {e}")
        return False
