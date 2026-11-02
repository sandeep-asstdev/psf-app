import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import check_db_health, engine, Base
from app.core.redis import get_redis, close_redis
from app.core.storage import init_storage_buckets
from app.api.v1.api import api_router
import app.models  # ensure models are registered

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("psf.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Auto-create tables if running in container/development mode
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLAlchemy metadata verified/created successfully.")
    except Exception as e:
        logger.warning(f"Could not initialize tables automatically (migrations will handle this): {e}")

    # Redis check
    try:
        r = await get_redis()
        await r.ping()
        logger.info("Connected successfully to Redis.")
    except Exception as e:
        logger.warning(f"Could not connect to Redis at startup: {e}")

    # Storage buckets check
    try:
        await init_storage_buckets()
    except Exception as e:
        logger.warning(f"Storage buckets init skipped: {e}")

    yield

    # Shutdown
    logger.info("Shutting down PSF Application...")
    await engine.dispose()
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }
