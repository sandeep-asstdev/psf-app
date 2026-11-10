"""
================================================================================
FILE PURPOSE: PostgreSQL Database Engine & Session Management.
This file sets up the SQLAlchemy async database connection engine, creates the session
factory (AsyncSessionLocal) for handling database queries asynchronously, and defines
the Base class for all database models. It also provides the `get_db` dependency for FastAPI.

KEY RESPONSIBILITIES:
- Initializes SQLAlchemy async engine using asyncpg connection driver.
- Provides `get_db()` async generator dependency to inject DB sessions into FastAPI routes.
- Defines DeclarativeBase `Base` with shared UUID primary keys and timestamp mixins.
- Provides `check_db_health()` to verify PostgreSQL availability during startup.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: asyncpg.exceptions.CannotConnectNowError or ConnectionRefusedError: [Errno 111] Connection refused
  -> Cause: The PostgreSQL database container (psf_postgres) is stopped or not ready to accept connections.
  -> What should you do: Run `docker ps` to verify psf_postgres is running. Run `docker logs psf_postgres` to check for DB errors. If stopped, run `docker compose up -d postgres`.
- Error: TimeoutError: QueuePool limit of size 20 overflow 10 reached
  -> Cause: Too many database connections opened without being closed (connection leak).
  -> What should you do: Ensure every endpoint uses `Depends(get_db)` so FastAPI automatically closes sessions after the request completes.
================================================================================
"""
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger("psf.database")

# Async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """Verifies that the PostgreSQL database is reachable."""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
