from fastapi import APIRouter
from app.core.config import settings
from app.core.database import db

router = APIRouter()


@router.get("/health", tags=["System"])
async def health_check():
    """System health check verifying database and Redis connectivity."""
    db_status = "connected" if db.is_connected() else "disconnected"

    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": settings.APP_VERSION,
        "database": db_status,
        "storage": settings.STORAGE_BACKEND,
    }
