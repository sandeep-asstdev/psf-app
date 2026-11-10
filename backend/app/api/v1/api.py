"""
================================================================================
FILE PURPOSE: API v1 Central Router Aggregator.
Combines all individual endpoint routers (auth, psf, allocation, complaints, imports, masters, users)
into a single unified `api_router` mounted under the `/api/v1` URL prefix.

KEY RESPONSIBILITIES:
- Mounts authentication routes (`/auth`).
- Mounts PSF calling routes (`/psf`).
- Mounts call allocation and attendance routes (`/allocation`).
- Mounts complaints management routes (`/complaints`).
- Mounts DMS import routes (`/imports`).
- Mounts master data routes (`/masters`).
- Mounts enterprise admin routes (`/admin`).
- Mounts reports and analytics routes (`/reports`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 404 Not Found on an API endpoint
  -> Cause: The endpoint was not included in this central router or path prefix is mismatched.
  -> What should you do: Check this file to ensure the sub-router is registered with `api_router.include_router(...)`.
================================================================================
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.auth import User
from app.api.v1.endpoints import health, auth, users, masters, questionnaires, imports, psf, complaints, reports, admin_console, allocation

api_router = APIRouter()

# Root alias for GET /me/permissions as requested by API spec
@api_router.get("/me/permissions", tags=["Authentication & Shift Logs"])
async def get_my_permissions_root(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.permissions import get_user_effective_permissions
    return await get_user_effective_permissions(db, current_user)

# Core health checks
api_router.include_router(health.router)

# Phase 2: Auth, Multi-Tenancy & User Management
api_router.include_router(auth.router)
api_router.include_router(users.router)

# Dynamic Permissions & Admin Console
api_router.include_router(admin_console.router)

# Phase 3: Masters, Settings & Dynamic Questionnaire Engine
api_router.include_router(masters.router)
api_router.include_router(questionnaires.router)

# Phase 4: DMS Data Import & Calling Allocation
api_router.include_router(imports.router)
api_router.include_router(allocation.router)

# Phase 5: PSF Calling Workspace & Call Console
api_router.include_router(psf.router)

# Phase 6: Complaint Management Lifecycle, SLAs, Reconfirmations, TNPS & Advisor Portal
api_router.include_router(complaints.router)

# Phase 7: Reports, Trends, Productivity & Excel Export
api_router.include_router(reports.router, prefix="/reports", tags=["Reports & Analytics"])
