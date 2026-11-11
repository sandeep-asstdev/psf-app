"""
================================================================================
FILE PURPOSE: Analytical Reports & Excel Export Endpoints.
Provides endpoints for viewing aggregated dealership performance metrics
and downloading multi-tab Excel analytical workbooks.

KEY RESPONSIBILITIES:
- Returns date-range filtered calling performance KPIs (`GET /reports/summary`).
- Generates and streams downloadable Excel workbook (`GET /reports/export/excel`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 403 Forbidden on reports
  -> Cause: Logged in user does not have `report.view` permission.
  -> What should you do: CRE callers cannot view executive reports; log in as Super Admin, CRE Admin, or Manager.
================================================================================
"""
import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_user, require, PermissionKey
from app.models.auth import User
from app.schemas.reports import ComprehensiveReportResponse
from app.services.report_service import get_comprehensive_report_data, generate_excel_report_stream

router = APIRouter()


@router.get("/summary", response_model=ComprehensiveReportResponse)
async def get_report_summary(
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    cre_id: Optional[uuid.UUID] = None,
    advisor_name: Optional[str] = None,
    service_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(require(PermissionKey.REPORT_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves full aggregated analytics dashboard metrics, trends, and leaderboards."""
    from app.core.permissions import get_user_effective_permissions, DataScope
    eff = await get_user_effective_permissions(db, current_user)
    scope = eff.get("permissions", {}).get(PermissionKey.REPORT_VIEW, DataScope.ALL)
    if not eff.get("is_super_admin", False) and scope == DataScope.ASSIGNED_BRANCHES:
        assigned_branches = [uuid.UUID(b) for b in eff.get("assigned_branches", []) if b]
        if assigned_branches and (not branch_id or branch_id not in assigned_branches):
            branch_id = assigned_branches[0]

    return await get_comprehensive_report_data(
        db=db,
        tenant_id=current_user.tenant_id,
        brand_id=brand_id,
        branch_id=branch_id,
        cre_id=cre_id,
        advisor_name=advisor_name,
        service_type=service_type,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/export/excel")
async def export_report_excel(
    brand_id: Optional[uuid.UUID] = None,
    branch_id: Optional[uuid.UUID] = None,
    cre_id: Optional[uuid.UUID] = None,
    advisor_name: Optional[str] = None,
    service_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(require(PermissionKey.REPORT_EXPORT)),
    db: AsyncSession = Depends(get_db),
):
    """Exports multi-tab executive report to an Excel .xlsx spreadsheet."""
    from app.core.permissions import get_user_effective_permissions, DataScope
    eff = await get_user_effective_permissions(db, current_user)
    scope = eff.get("permissions", {}).get(PermissionKey.REPORT_EXPORT, DataScope.ALL)
    if not eff.get("is_super_admin", False) and scope == DataScope.ASSIGNED_BRANCHES:
        assigned_branches = [uuid.UUID(b) for b in eff.get("assigned_branches", []) if b]
        if assigned_branches and (not branch_id or branch_id not in assigned_branches):
            branch_id = assigned_branches[0]

    report_data = await get_comprehensive_report_data(
        db=db,
        tenant_id=current_user.tenant_id,
        brand_id=brand_id,
        branch_id=branch_id,
        cre_id=cre_id,
        advisor_name=advisor_name,
        service_type=service_type,
        date_from=date_from,
        date_to=date_to,
    )

    stream = generate_excel_report_stream(report_data)
    filename = f"PSF_Analytics_Report_{date.today().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

