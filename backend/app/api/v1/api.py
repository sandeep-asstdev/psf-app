from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, users

api_router = APIRouter()

# Core health checks
api_router.include_router(health.router)

# Phase 2: Auth, Multi-Tenancy & User Management
api_router.include_router(auth.router)
api_router.include_router(users.router)
