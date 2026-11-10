"""
================================================================================
FILE PURPOSE: DMS File Upload, Sample Template & Error Report Endpoints.
Provides endpoints for uploading dealer management system files (.xlsx, .xls, .csv),
downloading standard 13-column sample templates, and downloading Excel row error reports.

KEY RESPONSIBILITIES:
- Receives uploaded file, processes job cards, and auto-allocates to CREs (`POST /imports/upload-and-process`).
- Downloads standard 13-column sample template in .xlsx or .csv (`GET /imports/template/sample`).
- Downloads row error Excel report for failed rows in a batch (`GET /imports/batches/{id}/error-report`).
- Lists recent import batch history (`GET /imports/batches`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: HTTP 400 Bad Request: 'Duplicate file upload'
  -> Cause: The exact same file was already imported previously.
  -> What should you do: Tick 'Confirm duplicate upload' in the UI or upload a new file.
================================================================================
"""
import json
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_active_user, require, PermissionKey
from app.models.auth import User
from app.models.service import ImportBatch
from app.schemas.import_job import (
    ImportPreviewResponse,
    ImportProcessRequest,
    ImportSummaryResponse,
    ImportBatchResponse,
    DmsJobCardWebhook,
)
from app.services.import_service import (
    parse_uploaded_file,
    suggest_auto_mapping,
    preview_import,
    process_import,
    generate_error_report_xlsx,
    generate_sample_template,
    create_job_card_from_webhook,
    list_import_batches,
)

router = APIRouter(prefix="/imports", tags=["DMS Data Import & Job Card Ingestion"])


@router.post("/preview", response_model=ImportPreviewResponse)
async def preview_file_mapping(
    file: UploadFile = File(...),
    brand_id: Optional[uuid.UUID] = Form(None),
    branch_id: Optional[uuid.UUID] = Form(None),
    column_mapping: Optional[str] = Form(None),
    current_user: User = Depends(require(PermissionKey.JOBCARD_IMPORT)),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Analyzes an uploaded Excel or CSV file without persisting.
    - Validates text formatting (protecting against Excel scientific notation / phone damage).
    - Checks for duplicate file hash across previous imports.
    - Resolves headers using Standard DMS auto-mapper.
    - Simulates row-level validation: returns counts of valid, warning, and error rows.
    - Returns the first 20 preview rows as they will be saved.
    """
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    custom_mapping: Optional[Dict[str, str]] = None
    if column_mapping:
        try:
            custom_mapping = json.loads(column_mapping)
        except Exception:
            pass

    return await preview_import(
        db=db,
        tenant_id=current_user.tenant_id,
        current_user=current_user,
        file_name=file.filename or "uploaded_file.xlsx",
        file_bytes=file_bytes,
        custom_mapping=custom_mapping,
        fallback_brand_id=brand_id,
        fallback_branch_id=branch_id,
    )


@router.post("/upload-and-process", response_model=ImportSummaryResponse)
async def upload_and_process_jobs(
    file: UploadFile = File(...),
    file_hash: Optional[str] = Form(None),
    confirm_duplicate_hash: bool = Form(False),
    brand_id: Optional[uuid.UUID] = Form(None),
    branch_id: Optional[uuid.UUID] = Form(None),
    column_mapping: str = Form("{}", description="JSON string of target_field -> file_column"),
    allocation_mode: str = Form("ROUND_ROBIN"),
    duplicate_action: str = Form("SKIP"),
    current_user: User = Depends(require(PermissionKey.JOBCARD_IMPORT)),
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Executes full DMS ingestion pipeline:
    - Verifies file hash uniqueness; warns on duplicate hash unless confirmed.
    - Validates, deduplicates (reporting Identical vs Different), encrypts customer phones.
    - Creates JobCard records and auto-populates Followup Queues (PSF + Hyundai 15-day Happiness Calling).
    - Automatically allocates calls equally across present CREs.
    """
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    try:
        mapping_dict = json.loads(column_mapping) if column_mapping else {}
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid column_mapping JSON string.")

    process_request = ImportProcessRequest(
        file_hash=file_hash,
        confirm_duplicate_hash=confirm_duplicate_hash,
        brand_id=brand_id,
        branch_id=branch_id,
        column_mapping=mapping_dict,
        allocation_mode=allocation_mode,
        duplicate_action=duplicate_action,
    )

    summary = await process_import(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        file_name=file.filename or "uploaded_file.xlsx",
        file_bytes=file_bytes,
        payload=process_request,
    )

    return summary


@router.get("/template/sample")
async def download_sample_template(
    format: str = Query("xlsx", regex="^(xlsx|csv)$"),
    current_user: User = Depends(require(PermissionKey.JOBCARD_IMPORT)),
):
    """
    Downloads the official Standard DMS 13-Column import template in Excel (.xlsx) or CSV format.
    Includes 2 realistic example rows.
    """
    content, media_type, filename = generate_sample_template(format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/batches/{batch_id}/error-report")
async def download_batch_error_report(
    batch_id: uuid.UUID,
    current_user: User = Depends(require(PermissionKey.JOBCARD_IMPORT)),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates and downloads a detailed Excel (.xlsx) error report for a specific import batch.
    Includes Row Number, Job Card No, Column, Rejected Value, Reason, and Actionable Fix Hint.
    """
    stmt = select(ImportBatch).where(
        ImportBatch.id == batch_id,
        ImportBatch.tenant_id == current_user.tenant_id,
        ImportBatch.is_deleted == False,
    )
    batch = (await db.execute(stmt)).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import batch not found.")

    error_log = batch.error_log or {}
    errors = error_log.get("errors", [])
    if not errors:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No row errors logged for this import batch.")

    report_bytes = generate_error_report_xlsx(batch.file_name, str(batch.id), errors)
    filename = f"Import_Errors_Batch_{str(batch.id)[:8]}.xlsx"

    return Response(
        content=report_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/webhook", status_code=status.HTTP_201_CREATED)
async def dms_realtime_webhook(
    payload: DmsJobCardWebhook,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Direct REST API / Webhook endpoint for live DMS invoice integration.
    Automatically enqueues follow-up calling and schedules Hyundai Happiness Campaign.
    """
    result = await create_job_card_from_webhook(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
    )
    return result


@router.get("/batches", response_model=List[ImportBatchResponse])
async def get_import_batches(
    limit: int = 20,
    current_user: User = Depends(require(PermissionKey.JOBCARD_VIEW)),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves previous DMS import batches with status, counts, and error audits."""
    batches = await list_import_batches(db, current_user.tenant_id, limit=limit)
    response_items = []
    for b in batches:
        response_items.append(
            ImportBatchResponse(
                id=b.id,
                tenant_id=b.tenant_id,
                brand_id=b.brand_id,
                brand_name=b.brand.name if b.brand else None,
                branch_id=b.branch_id,
                branch_name=b.branch.name if b.branch else None,
                file_name=b.file_name,
                file_hash=b.file_hash,
                total_rows=b.total_rows,
                processed_rows=b.processed_rows,
                success_rows=b.success_rows,
                error_rows=b.error_rows,
                status=b.status,
                error_log=b.error_log,
                uploaded_by=b.uploaded_by,
                uploader_name=b.uploader.full_name if b.uploader else None,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
        )
    return response_items
