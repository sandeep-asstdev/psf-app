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
