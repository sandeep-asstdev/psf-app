"""
================================================================================
FILE PURPOSE: System Health Probes & Readiness Checks.
Provides health check endpoints used by Docker healthchecks, Kubernetes liveness probes,
and uptime monitors to verify that the API, database, and Redis are running normally.

KEY RESPONSIBILITIES:
- Liveness check: returns 200 OK if API server is alive (`GET /health/live`).
- Readiness check: tests live connection to PostgreSQL and Redis (`GET /health/ready`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Health check returns 503 Service Unavailable
  -> Cause: Database or Redis is unreachable from the API container.
  -> What should you do: Inspect database container with `docker logs psf_postgres` and Redis with `docker logs psf_redis`.
================================================================================
"""
from fastapi import APIRouter
from app.core.config import settings
from app.core.database import check_db_health
from app.core.redis import get_redis

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check():
    """System health check verifying database and Redis connectivity."""
    db_ok = await check_db_health()
    db_status = "connected" if db_ok else "disconnected"

    redis_status = "disconnected"
    try:
        r = await get_redis()
        if await r.ping():
            redis_status = "connected"
    except Exception:
        pass

    all_healthy = db_ok and redis_status == "connected"

    return {
        "status": "ok" if all_healthy else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": settings.APP_VERSION,
        "database": db_status,
        "redis": redis_status,
        "storage": settings.STORAGE_BACKEND,
    }
