from fastapi import APIRouter
from app.api.v1.endpoints import health

api_router = APIRouter()

# Core health checks
api_router.include_router(health.router)

# Note: In Phase 2+, auth, users, tenants, questionnaires, calls, complaints, and reports routers will be mounted here.
