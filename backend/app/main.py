"""
================================================================================
FILE PURPOSE: FastAPI Application Entry Point & Global Server Configuration.
Initializes the FastAPI application, sets up lifespan event hooks (connecting to DB, Redis, and MinIO),
configures CORS security rules so the frontend can communicate with the backend,
registers all API v1 routers, and provides global exception handlers for database errors.

KEY RESPONSIBILITIES:
- Creates the FastAPI application instance (`app`).
- Manages application startup and shutdown lifecycle hooks (`lifespan`).
- Configures CORS middleware supporting localhost and local IP development.
- Attaches global error handlers ensuring clean error JSON and CORS headers.
- Mounts all API endpoints under `/api/v1`.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: CORS error in browser console: 'No Access-Control-Allow-Origin header is present'
  -> Cause: Request was blocked by CORS policy or an unhandled 500 error crashed before headers were added.
  -> What should you do: Verify `allow_origins` in this file and ensure your frontend URL (e.g. http://localhost:5173) is allowed.
- Error: Server hangs on startup: 'Could not connect to Redis' or DB timeout
  -> Cause: Database or Redis container is stopped.
  -> What should you do: Check container status with `docker ps` and ensure `psf_postgres` and `psf_redis` are healthy.
================================================================================
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
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
    # Startup - Tables strictly managed via Alembic migrations only
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

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

# CORS Middleware - Support explicit origins and local development regex
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Global Exception Handlers ensuring CORS headers and clean human messages
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"Database IntegrityError on {request.method} {request.url.path}: {exc}")
    detail = "Database constraint conflict: A record with this unique code or identifier already exists."
    err_str = str(exc.orig) if hasattr(exc, "orig") else str(exc)
    if "Key (" in err_str and ") already exists" in err_str:
        field_part = err_str.split("Key (")[1].split(") already exists")[0]
        detail = f"Duplicate conflict: ({field_part}) already exists. Please choose a different code."

    origin = request.headers.get("origin")
    headers = {}
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": detail},
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    origin = request.headers.get("origin")
    headers = {}
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["Access-Control-Allow-Methods"] = "*"
        headers["Access-Control-Allow-Headers"] = "*"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Server error: {str(exc)}"},
        headers=headers,
    )


# Security Headers & Redis Rate Limiting Middleware
@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # 1. Rate limiting on sensitive endpoints (bypassed in pytest test execution)
    if request.url.path.endswith("/auth/login") and request.method == "POST" and "PYTEST_CURRENT_TEST" not in os.environ:
        client_ip = request.client.host if request.client else "unknown"
        redis_key = f"rl:login:{client_ip}"
        try:
            r = await get_redis()
            current_hits = await r.incr(redis_key)
            if current_hits == 1:
                await r.expire(redis_key, 60)
            if current_hits > 35:  # 35 login attempts / min limit
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Too many login attempts. Please wait 60 seconds before trying again."},
                    headers={"Retry-After": "60"},
                )
        except Exception:
            pass

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception(f"Unhandled middleware-level exception on {request.method} {request.url.path}: {exc}")
        origin = request.headers.get("origin")
        headers = {}
        if origin:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Allow-Methods"] = "*"
            headers["Access-Control-Allow-Headers"] = "*"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal error: {str(exc)}"},
            headers=headers,
        )

    # 2. Production Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    return response


# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    db_ok = await check_db_health()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "app": settings.APP_NAME,
        "database": "connected" if db_ok else "disconnected",
    }


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
    }
