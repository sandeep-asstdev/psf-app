"""
================================================================================
FILE PURPOSE: DMS Data Import & Ingestion Pipeline.
Parses uploaded dealer management system (DMS) files (.xlsx, .xls, .csv),
normalizes dates, cleans phone numbers, resolves Brands and Branches against masters,
creates JobCard and Customer records, and automatically triggers the call allocator.

KEY RESPONSIBILITIES:
- Reads every cell as text to prevent Excel data corruption (lost leading zeros, scientific notation).
- Normalizes 10-digit Indian phone numbers and encrypts them with blind index hashes.
- Validates Brand and Branch against master tables, raising row errors for unknown values.
- Detects duplicate job cards and skips them without aborting the batch.
- Automatically triggers `allocate_queue_items()` to distribute calls equally among present CREs.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Row error: 'Unknown Branch [NAME]'
  -> Cause: The branch name in the file does not match any branch in the database.
  -> What should you do: Ensure the Branch is created under the Brand in the Admin Console or verify file branch spelling.
- Error: Row error: 'Invalid phone number'
  -> Cause: Phone number cell contains less than 10 digits or is unparseable.
  -> What should you do: Verify phone numbers in the DMS file start with digits 6-9 and have 10 valid digits.
================================================================================
"""
import re
import io
import uuid
import hashlib
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.service import ImportBatch, JobCard, ServiceType
from app.models.customer import Customer, Vehicle
from app.models.followup import FollowupQueue
from app.models.tenant import Brand, Branch
from app.models.auth import User, Role, UserScope
from app.core.crypto import encrypt_phone, hash_phone, uuid7
from app.core.security import get_password_hash
from app.services.allocation_service import allocate_queue_items
from app.services.config_resolver import ConfigResolverService
from app.schemas.import_job import (
    ImportPreviewResponse,
    ImportPreviewRow,
    ImportProcessRequest,
    ImportSummaryResponse,
    ImportRowError,
    ImportRowWarning,
    DuplicateSkippedDetail,
    DmsJobCardWebhook,
)


# -------------------------------------------------------------
# Standard 13-Column DMS Field Definitions & Auto-Mapping Aliases
# -------------------------------------------------------------
STANDARD_DMS_FIELDS = [
    "brand",
    "branch",
    "brand_logo",
    "job_card_no",
    "job_card_date",
    "customer_name",
    "contact_number",
    "vin_no",
    "reg_no",
    "model",
    "service_advisor",
    "service_type",
    "total_service_amount",
]

AUTO_MAPPING_RULES: Dict[str, List[str]] = {
    "brand": ["brand", "make", "oem", "brand name", "manufacturer"],
    "branch": ["branch", "workshop", "dealership branch", "location", "outlet", "branch name", "dealer code", "branch code"],
    "brand_logo": ["brand logo", "logo"],
    "job_card_no": ["job card no", "job card number", "job card", "jobcard", "ro no", "ro number", "ro_no", "ro#", "jc no", "repair order", "invoice no", "jobcard no"],
    "job_card_date": ["job card date", "ro date", "jc date", "bill date", "invoice date", "delivery date", "closed date", "date", "service date"],
    "customer_name": ["customer name", "customer", "cust name", "client", "owner", "party name", "customer_name"],
    "contact_number": ["contact number", "mobile no", "mobile number", "phone", "mobile", "contact", "phone number", "cust mobile", "mobile 1", "customer phone", "cell", "contact no"],
    "vin_no": ["vin no", "vin", "vin number", "chassis", "chassis no", "chassis number"],
    "reg_no": ["reg no", "registration no", "registration number", "vehicle no", "car no", "veh reg no", "license plate", "registration"],
    "model": ["model", "vehicle model", "car model", "model name"],
    "service_advisor": ["service advisor", "advisor", "sa name", "sa", "service consultant"],
    "service_type": ["service type", "type of service", "job type", "sub type", "service category"],
    "total_service_amount": ["total service amount", "amount", "total amount", "bill amount", "invoice amount", "net amount", "total bill", "total bill amount", "total service bill"],
}

# Backward compatibility aliases
TARGET_FIELD_ALIASES = {
    "customer_phone": "contact_number",
    "vin": "vin_no",
    "total_amount": "total_service_amount",
}


def compute_file_hash(file_bytes: bytes) -> str:
    """Computes SHA-256 hash of uploaded file contents for idempotent deduplication."""
    return hashlib.sha256(file_bytes).hexdigest()


async def check_duplicate_file_hash(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    file_hash: str,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Checks whether the exact file hash was already ingested for this tenant."""
    stmt = (
        select(ImportBatch)
        .options(selectinload(ImportBatch.uploader))
        .where(
            ImportBatch.tenant_id == tenant_id,
            ImportBatch.file_hash == file_hash,
            ImportBatch.is_deleted == False,
        )
        .order_by(ImportBatch.created_at.desc())
    )
    batch = (await db.execute(stmt)).scalars().first()
    if not batch:
        return False, None

    uploader_name = batch.uploader.full_name if batch.uploader else "Unknown User"
    return True, {
        "batch_id": str(batch.id),
        "file_name": batch.file_name,
        "uploaded_at": batch.created_at.isoformat() if batch.created_at else None,
        "uploaded_by": uploader_name,
        "total_rows": batch.total_rows,
        "success_rows": batch.success_rows,
    }


def normalize_raw_cell_value(val: Any) -> Optional[str]:
    """
    Robust string normalizer:
    Prevents Excel corruption of numbers, floats, and scientific notation (e.g. 9.48E+09).
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val))
        formatted = f"{val:.10f}".rstrip("0").rstrip(".")
        return formatted
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ("nan", "none", "null"):
        return None
    # Handle string-formatted scientific notation like "9.48E+09" or "9.4800000e+09"
    if re.match(r"^[+-]?\d+(\.\d+)?[eE][+-]?\d+$", val_str):
        try:
            f_val = float(val_str)
            if f_val.is_integer():
                return str(int(f_val))
            return f"{f_val:.10f}".rstrip("0").rstrip(".")
        except Exception:
            pass
    return val_str


def parse_uploaded_file(file_bytes: bytes, filename: str) -> Tuple[List[str], List[Dict[str, Any]], int]:
    """
    Parses Excel (.xlsx, .xls) or CSV into sanitized text column headers and rows.
    - Reads all cells as text to avoid Excel number corruption.
    - Handles UTF-8 with BOM (utf-8-sig), UTF-8, and latin-1.
    - Ignores blank rows, merged header artifacts, and empty column names.
    """
    fn_lower = filename.lower()
    df: pd.DataFrame

    if fn_lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    elif fn_lower.endswith(".csv"):
        parsed = False
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, encoding=enc, keep_default_na=False)
                parsed = True
                break
            except UnicodeDecodeError:
                continue
        if not parsed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode CSV file. Please ensure it is saved as UTF-8 or CSV standard format.",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload an Excel (.xlsx/.xls) or CSV file.",
        )

    # 1. Clean headers: strip whitespace, remove unnamed merged columns
    cleaned_columns = []
    valid_cols_idx = []
    for idx, col in enumerate(df.columns):
        col_str = str(col).strip()
        if col_str and not col_str.lower().startswith("unnamed:"):
            cleaned_columns.append(col_str)
            valid_cols_idx.append(idx)

    if not cleaned_columns:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid header columns detected in uploaded file.")

    df = df.iloc[:, valid_cols_idx]
    df.columns = cleaned_columns

    # 2. Normalize every cell through safe text normalizer
    for col in df.columns:
        df[col] = df[col].apply(normalize_raw_cell_value)

    # 3. Filter out completely blank rows
    df.dropna(how="all", inplace=True)
    records = df.to_dict(orient="records")

    # Filter out records where all values are None/empty strings, clean nan values
    filtered_records = []
    for r in records:
        clean_r = {}
        for k, v in r.items():
            if v is None or pd.isna(v) or str(v).strip().lower() in ("nan", "none", "null", ""):
                clean_r[k] = None
            else:
                clean_r[k] = str(v).strip()
        if any(v is not None for v in clean_r.values()):
            filtered_records.append(clean_r)

    return cleaned_columns, filtered_records, len(filtered_records)


def suggest_auto_mapping(detected_columns: List[str]) -> Dict[str, str]:
    """
    Intelligently maps DMS source columns to internal standard fields using aliases.
    Case-insensitive, trims extra spaces and underscores.
    """
    mapping: Dict[str, str] = {}
    normalized_cols: Dict[str, str] = {
        re.sub(r"[\s_]+", " ", str(col)).strip().lower(): col
        for col in detected_columns
    }

    for target_field, aliases in AUTO_MAPPING_RULES.items():
        matched_col = None
        # 1. Exact alias match
        for alias in aliases:
            clean_alias = re.sub(r"[\s_]+", " ", alias).strip().lower()
            if clean_alias in normalized_cols:
                matched_col = normalized_cols[clean_alias]
                break

        # 2. Substring match
        if not matched_col:
            for norm_name, original_col in normalized_cols.items():
                for alias in aliases:
                    clean_alias = re.sub(r"[\s_]+", " ", alias).strip().lower()
                    if clean_alias == norm_name or (len(clean_alias) > 3 and clean_alias in norm_name):
                        matched_col = original_col
                        break
                if matched_col:
                    break

        if matched_col:
            mapping[target_field] = matched_col

    return mapping


# -------------------------------------------------------------
# Row Parsing & Field Normalization Helpers
# -------------------------------------------------------------
def clean_phone_number(raw_phone: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Cleans and standardizes contact number into 10-digit format.
    Strips spaces, dashes, dots, parentheses, +91, and leading 0.
    Returns (cleaned_10_digits, error_reason).
    """
    if raw_phone is None:
        return None, "Contact Number is missing"
    raw_str = normalize_raw_cell_value(raw_phone) or ""
    cleaned = re.sub(r"[^\d]", "", raw_str)

    if len(cleaned) == 12 and cleaned.startswith("91"):
        cleaned = cleaned[2:]
    elif len(cleaned) == 11 and cleaned.startswith("0"):
        cleaned = cleaned[1:]

    if len(cleaned) != 10:
        return None, f"Contact Number '{raw_str}' must be exactly 10 digits (got {len(cleaned)} digits)"
    if cleaned[0] not in "6789":
        return None, f"Contact Number '{raw_str}' must start with 6, 7, 8, or 9"

    return cleaned, None


def parse_date_value(raw_val: Any) -> Tuple[Optional[date], Optional[str], Optional[str]]:
    """
    Parses various date formats from Excel/CSV:
    - dd-mm-yyyy, dd/mm/yyyy, yyyy-mm-dd, real Excel dates.
    Returns (parsed_date, error_reason, warning_reason).
    """
    if raw_val is None:
        return None, "Job Card Date is missing", None

    parsed_dt: Optional[date] = None
    if isinstance(raw_val, (date, datetime)):
        parsed_dt = raw_val.date() if isinstance(raw_val, datetime) else raw_val
    else:
        val_str = str(raw_val).strip()
        # Handle Excel serial integer dates (e.g. 45600)
        if val_str.isdigit() and len(val_str) in (4, 5):
            try:
                serial = int(val_str)
                parsed_dt = (datetime(1899, 12, 30) + timedelta(days=serial)).date()
            except Exception:
                pass

        if not parsed_dt:
            for fmt in (
                "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y",
                "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y",
                "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y"
            ):
                try:
                    parsed_dt = datetime.strptime(val_str, fmt).date()
                    break
                except ValueError:
                    continue

    if not parsed_dt:
        return None, f"Unparseable Job Card Date '{raw_val}'. Accepted: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD", None

    # Date sanity checks (Warnings)
    today = datetime.now().date()
    warning: Optional[str] = None
    if parsed_dt > today:
        warning = f"Job Card Date '{parsed_dt.strftime('%d-%m-%Y')}' is in the future."
    elif (today - parsed_dt).days > 90:
        warning = f"Job Card Date '{parsed_dt.strftime('%d-%m-%Y')}' is older than 90 days ({(today - parsed_dt).days} days old)."

    return parsed_dt, None, warning


def parse_amount_value(raw_val: Any) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Parses amount: strips commas, ₹, Rs., spaces. Must be a number >= 0.
    Returns (decimal_amount, error_reason).
    """
    if raw_val is None or str(raw_val).strip() == "":
        return Decimal("0.0"), None

    raw_str = str(raw_val).strip()
    is_negative = "-" in raw_str
    cleaned = re.sub(r"[^\d\.]", "", raw_str)
    if not cleaned:
        return None, f"Invalid Total Service Amount '{raw_str}': must be a valid positive number"

    try:
        amt = Decimal(cleaned)
        if is_negative:
            amt = -amt
        if amt < 0:
            return None, f"Amount cannot be negative ('{raw_str}')"
        return amt, None
    except Exception:
        return None, f"Invalid Total Service Amount '{raw_str}'"


def normalize_reg_no(raw_val: Any) -> str:
    """Uppercase, remove spaces and dashes."""
    if not raw_val:
        return ""
    return re.sub(r"[\s\-]", "", str(raw_val)).upper()


def normalize_vin(raw_val: Any) -> Tuple[Optional[str], Optional[str]]:
    """Uppercase, remove spaces. Warning if not 17 characters."""
    if not raw_val:
        return None, None
    clean_vin = re.sub(r"\s+", "", str(raw_val)).upper()
    if not clean_vin:
        return None, None
    warning: Optional[str] = None
    if len(clean_vin) != 17:
        warning = f"Vin No '{clean_vin}' has length {len(clean_vin)}, expected 17 characters."
    return clean_vin, warning


def normalize_customer_name(raw_val: Any) -> str:
    """Trim and collapse spaces."""
    if not raw_val:
        return "Customer"
    cleaned = re.sub(r"\s+", " ", str(raw_val)).strip()
    return cleaned.title() if cleaned else "Customer"


# -------------------------------------------------------------
# Master Resolution Helpers
# -------------------------------------------------------------
async def resolve_brand_and_branch(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    raw_brand: Optional[str],
    raw_branch: Optional[str],
    job_card_no: str,
    fallback_brand_id: Optional[uuid.UUID],
    fallback_branch_id: Optional[uuid.UUID],
    all_brands: List[Brand],
    all_branches: List[Branch],
) -> Tuple[Optional[Brand], Optional[Branch], Optional[str]]:
    """
    Resolves Brand and Branch from row values or fallbacks against tenant masters.
    Unknown brand or branch is a ROW ERROR (never auto-create).
    The branch must belong to the brand.
    Returns (brand, branch, error_reason).
    """
    brand_obj: Optional[Brand] = None
    branch_obj: Optional[Branch] = None

    # 1. Resolve Brand
    if raw_brand and str(raw_brand).strip():
        b_clean = str(raw_brand).strip().upper()
        for b in all_brands:
            if b.code.upper() == b_clean or b.name.upper() == b_clean:
                brand_obj = b
                break
            if b_clean in b.name.upper() or b.name.upper() in b_clean:
                brand_obj = b
                break
        if not brand_obj:
            return None, None, f"Unknown Brand '{raw_brand}'"
    elif fallback_brand_id:
        brand_obj = next((b for b in all_brands if b.id == fallback_brand_id), None)

    # 2. Resolve Branch
    if raw_branch and str(raw_branch).strip():
        br_clean = str(raw_branch).strip().upper()
        # Direct code, name, dms_code, or display_name match
        for br in all_branches:
            if br.code.upper() == br_clean or br.name.upper() == br_clean:
                branch_obj = br
                break
            if br.dms_code and br.dms_code.upper() == br_clean:
                branch_obj = br
                break
            if br.display_name and br.display_name.upper() == br_clean:
                branch_obj = br
                break
            # Substring match
            if br_clean in br.name.upper() or br.name.upper() in br_clean:
                branch_obj = br
                break

    # Branch fallback by Job Card No DMS code prefix (e.g. S8211_R2026 -> Hubli, S8827_R2026 -> Gadag)
    if not branch_obj and job_card_no and "_" in job_card_no:
        prefix = job_card_no.split("_")[0].strip().upper()
        for br in all_branches:
            if br.dms_code and br.dms_code.upper() == prefix:
                branch_obj = br
                break

    if not branch_obj and fallback_branch_id:
        branch_obj = next((br for br in all_branches if br.id == fallback_branch_id), None)

    if not branch_obj:
        return None, None, f"Unknown Branch '{raw_branch or 'N/A'}'"

    # If brand was not set in row, infer from branch's brand_id
    if not brand_obj and branch_obj.brand_id:
        brand_obj = next((b for b in all_brands if b.id == branch_obj.brand_id), None)

    if not brand_obj:
        return None, None, f"Unknown Brand for branch '{branch_obj.name}'"

    # Verify branch belongs to brand
    if branch_obj.brand_id and branch_obj.brand_id != brand_obj.id:
        return None, None, f"Branch '{branch_obj.name}' does not belong to Brand '{brand_obj.name}'"

    return brand_obj, branch_obj, None


def check_user_branch_scope(current_user: User, branch_id: uuid.UUID) -> bool:
    """Validates if user has permission scope for this branch."""
    if not current_user.role:
        return False
    if current_user.role.name in ("SUPER_ADMIN", "CRE_ADMIN", "DEALER_ADMIN"):
        return True
    if not current_user.scopes:
        return True
    user_branch_ids = [s.branch_id for s in current_user.scopes if s.branch_id]
    if not user_branch_ids:
        return True
    return branch_id in user_branch_ids


# -------------------------------------------------------------
# Preview Engine (Step 2 Preview)
# -------------------------------------------------------------
async def preview_import(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    current_user: User,
    file_name: str,
    file_bytes: bytes,
    custom_mapping: Optional[Dict[str, str]] = None,
    fallback_brand_id: Optional[uuid.UUID] = None,
    fallback_branch_id: Optional[uuid.UUID] = None,
) -> ImportPreviewResponse:
    """
    Simulates row-level ingestion for the preview screen:
    - Parses file with TEXT preservation.
    - Computes file SHA-256 hash and checks duplicate file uploads.
    - Maps headers using Standard DMS auto-mapper.
    - Validates each row: counts valid, warning, and error rows.
    - Formats the first 20 rows as they will be saved.
    """
    file_hash = compute_file_hash(file_bytes)
    has_dupe_hash, prev_batch_info = await check_duplicate_file_hash(db, tenant_id, file_hash)

    columns, records, total_rows = parse_uploaded_file(file_bytes, file_name)

    # Resolve mapping
    mapping = custom_mapping or suggest_auto_mapping(columns)
    # Re-map alias keys
    resolved_mapping = {}
    for target_key, col_name in mapping.items():
        canonical_key = TARGET_FIELD_ALIASES.get(target_key, target_key)
        resolved_mapping[canonical_key] = col_name

    mapped_cols_set = set(resolved_mapping.values())
    unmapped_headers = [c for c in columns if c not in mapped_cols_set]

    # Pre-cache masters
    all_brands = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id, Brand.is_active == True))).scalars().all()
    all_branches = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id, Branch.is_active == True))).scalars().all()
    all_st = (await db.execute(select(ServiceType).where(ServiceType.tenant_id == tenant_id, ServiceType.is_active == True))).scalars().all()
    st_names = {st.name.strip().upper() for st in all_st}
    st_codes = {st.code.strip().upper() for st in all_st}

    valid_rows_count = 0
    warning_rows_count = 0
    error_rows_count = 0
    preview_rows: List[ImportPreviewRow] = []

    seen_batch_keys = set()

    for row_idx, row in enumerate(records, start=1):
        row_errors: List[ImportRowError] = []
        row_warnings: List[ImportRowWarning] = []

        # 1. Job Card No
        jc_col = resolved_mapping.get("job_card_no")
        raw_jc = row.get(jc_col) if jc_col else None
        jc_no = str(raw_jc).strip() if raw_jc else ""
        if not jc_no:
            row_errors.append(ImportRowError(
                row_number=row_idx,
                column=jc_col or "Job Card No",
                rejected_value=str(raw_jc),
                reason="Job Card No is required but missing or empty",
                fix_hint="Ensure every row contains a unique Job Card / RO Number",
            ))

        # 2. Brand & Branch Matching
        b_col = resolved_mapping.get("brand")
        br_col = resolved_mapping.get("branch")
        raw_b = row.get(b_col) if b_col else None
        raw_br = row.get(br_col) if br_col else None

        brand_obj, branch_obj, bb_err = await resolve_brand_and_branch(
            db, tenant_id, raw_b, raw_br, jc_no, fallback_brand_id, fallback_branch_id, all_brands, all_branches
        )
        if bb_err:
            row_errors.append(ImportRowError(
                row_number=row_idx,
                job_card_no=jc_no,
                column=br_col or "Branch",
                rejected_value=str(raw_br or raw_b),
                reason=bb_err,
                fix_hint="Check that Branch and Brand names match the dealership master catalog in Admin Console",
            ))
        elif branch_obj and not check_user_branch_scope(current_user, branch_obj.id):
            row_errors.append(ImportRowError(
                row_number=row_idx,
                job_card_no=jc_no,
                column="Branch",
                rejected_value=branch_obj.name,
                reason=f"User does not have permission scope to import for branch '{branch_obj.name}'",
                fix_hint="Contact Administrator to assign scope for this workshop branch",
            ))

        # 3. Contact Number
        phone_col = resolved_mapping.get("contact_number")
        raw_phone = row.get(phone_col) if phone_col else None
        clean_phone, phone_err = clean_phone_number(raw_phone)
        if phone_err:
            row_errors.append(ImportRowError(
                row_number=row_idx,
                job_card_no=jc_no,
                column=phone_col or "Contact Number",
                rejected_value=str(raw_phone),
                reason=phone_err,
                fix_hint="Provide a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9",
            ))

        # 4. Job Card Date
        date_col = resolved_mapping.get("job_card_date")
        raw_date = row.get(date_col) if date_col else None
        parsed_date, date_err, date_warn = parse_date_value(raw_date)
        if date_err:
            row_errors.append(ImportRowError(
                row_number=row_idx,
                job_card_no=jc_no,
                column=date_col or "Job Card Date",
                rejected_value=str(raw_date),
                reason=date_err,
                fix_hint="Format date as DD-MM-YYYY or YYYY-MM-DD",
            ))
        elif date_warn:
            row_warnings.append(ImportRowWarning(
                row_number=row_idx,
                job_card_no=jc_no,
                column=date_col or "Job Card Date",
                warning_value=str(raw_date),
                reason=date_warn,
                fix_hint="Verify date accuracy; older or future dates may skew follow-up scheduling",
            ))

        # 5. Customer Name
        cust_col = resolved_mapping.get("customer_name")
        raw_cust = row.get(cust_col) if cust_col else None
        cust_name = normalize_customer_name(raw_cust)

        # 6. Reg No
        reg_col = resolved_mapping.get("reg_no")
        raw_reg = row.get(reg_col) if reg_col else None
        reg_no = normalize_reg_no(raw_reg)
        if not reg_no:
            row_errors.append(ImportRowError(
                row_number=row_idx,
                job_card_no=jc_no,
                column=reg_col or "Reg No",
                rejected_value=str(raw_reg),
                reason="Vehicle Reg No is missing",
                fix_hint="Provide vehicle registration number or temporary chassis number",
            ))

        # 7. Vin No
        vin_col = resolved_mapping.get("vin_no")
        raw_vin = row.get(vin_col) if vin_col else None
        clean_vin, vin_warn = normalize_vin(raw_vin)
        if vin_warn:
            row_warnings.append(ImportRowWarning(
                row_number=row_idx,
                job_card_no=jc_no,
                column=vin_col or "Vin No",
                warning_value=str(raw_vin),
                reason=vin_warn,
                fix_hint="Standard VIN numbers are exactly 17 alphanumeric characters",
            ))

        # 8. Service Type
        st_col = resolved_mapping.get("service_type")
        raw_st = str(row.get(st_col) or "").strip() if st_col else ""
        if raw_st and raw_st.upper() not in st_names and raw_st.upper() not in st_codes:
            row_warnings.append(ImportRowWarning(
                row_number=row_idx,
                job_card_no=jc_no,
                column=st_col or "Service Type",
                warning_value=raw_st,
                reason=f"Service Type '{raw_st}' is not in master dropdowns; will be mapped to 'Unmapped'",
                fix_hint="Admin can add this service type to the master dropdown in Admin Console",
            ))

        # 9. Amount
        amt_col = resolved_mapping.get("total_service_amount")
        raw_amt = row.get(amt_col) if amt_col else None
        clean_amt, amt_err = parse_amount_value(raw_amt)
        if amt_err:
            row_errors.append(ImportRowError(
                row_number=row_idx,
                job_card_no=jc_no,
                column=amt_col or "Total Service Amount",
                rejected_value=str(raw_amt),
                reason=amt_err,
                fix_hint="Remove currency symbols and ensure the number is >= 0",
            ))

        # 10. Duplicate in-file check
        if branch_obj and jc_no:
            dupe_key = (branch_obj.id, jc_no)
            if dupe_key in seen_batch_keys:
                row_warnings.append(ImportRowWarning(
                    row_number=row_idx,
                    job_card_no=jc_no,
                    column="Job Card No",
                    warning_value=jc_no,
                    reason=f"Duplicate Job Card '{jc_no}' within this same file",
                    fix_hint="This duplicate row will be automatically skipped",
                ))
            else:
                seen_batch_keys.add(dupe_key)

        # Status
        if row_errors:
            row_status = "ERROR"
            error_rows_count += 1
        elif row_warnings:
            row_status = "WARNING"
            warning_rows_count += 1
            valid_rows_count += 1
        else:
            row_status = "VALID"
            valid_rows_count += 1

        # Save first 20 preview rows
        if row_idx <= 20:
            preview_rows.append(ImportPreviewRow(
                row_number=row_idx,
                job_card_no=jc_no,
                job_card_date=parsed_date.strftime("%d-%m-%Y") if parsed_date else str(raw_date),
                customer_name=cust_name,
                contact_number=clean_phone or str(raw_phone),
                brand=brand_obj.name if brand_obj else str(raw_b or ""),
                branch=branch_obj.name if branch_obj else str(raw_br or ""),
                reg_no=reg_no,
                vin_no=clean_vin,
                model=str(row.get(resolved_mapping.get("model")) or "Unknown Model"),
                service_advisor=str(row.get(resolved_mapping.get("service_advisor")) or "Unassigned"),
                service_type=raw_st or "Periodic Maintenance Service",
                total_service_amount=float(clean_amt or Decimal("0.0")),
                status=row_status,
                warnings=row_warnings,
                errors=row_errors,
            ))

    legacy_suggested = dict(resolved_mapping)
    for legacy_k, std_k in TARGET_FIELD_ALIASES.items():
        if std_k in resolved_mapping:
            legacy_suggested[legacy_k] = resolved_mapping[std_k]

    return ImportPreviewResponse(
        file_name=file_name,
        file_hash=file_hash,
        has_duplicate_file_hash=has_dupe_hash,
        previous_batch_info=prev_batch_info,
        total_rows=total_rows,
        valid_rows=valid_rows_count,
        warning_rows=warning_rows_count,
        error_rows=error_rows_count,
        detected_columns=columns,
        mapped_headers=resolved_mapping,
        suggested_mapping=legacy_suggested,
        unmapped_headers=unmapped_headers,
        preview_rows=preview_rows,
    )


# -------------------------------------------------------------
# Main Import Pipeline (Step 3 Confirm & Ingest)
# -------------------------------------------------------------
async def process_import(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    file_name: str,
    file_bytes: bytes,
    payload: ImportProcessRequest,
) -> ImportSummaryResponse:
    """
    Executes the Standard DMS Ingestion Pipeline:
    - Verifies file hash uniqueness (refuses duplicate hash unless confirm_duplicate_hash is True).
    - Persists import_batch with file_hash, uploaded_by, total_rows.
    - Validates, deduplicates (identical vs different), upserts customer & vehicle.
    - Matches or creates placeholder service advisors.
    - Unmapped service types stored with warning.
    - Generates Followup Queues (PSF + Hyundai 15-day Happiness Calling).
    - Automatically allocates calls equally across present CREs.
    """
    file_hash = compute_file_hash(file_bytes)
    has_dupe, prev_batch_info = await check_duplicate_file_hash(db, tenant_id, file_hash)
    if has_dupe and not payload.confirm_duplicate_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"This exact file has already been imported previously (Batch #{prev_batch_info['batch_id']} on {prev_batch_info['uploaded_at']} by {prev_batch_info['uploaded_by']}).",
                "file_hash": file_hash,
                "previous_batch": prev_batch_info,
                "requires_confirmation": True,
            },
        )

    columns, records, total_rows = parse_uploaded_file(file_bytes, file_name)

    # 1. Fetch current user
    user_stmt = select(User).options(selectinload(User.role), selectinload(User.scopes)).where(User.id == user_id)
    current_user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 2. Pre-cache masters
    all_brands = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id, Brand.is_active == True))).scalars().all()
    all_branches = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id, Branch.is_active == True))).scalars().all()
    all_st = (await db.execute(select(ServiceType).where(ServiceType.tenant_id == tenant_id, ServiceType.is_active == True))).scalars().all()
    st_by_name = {st.name.strip().upper(): st for st in all_st}
    st_by_code = {st.code.strip().upper(): st for st in all_st}

    # Fetch service advisor role
    sa_role = (await db.execute(
        select(Role).where(
            (Role.tenant_id == tenant_id) | (Role.tenant_id == None),
            Role.name == "SERVICE_ADVISOR",
        )
    )).scalars().first()

    # Pre-cache advisors
    advisors_res = await db.execute(select(User).where(User.tenant_id == tenant_id, User.role_id == sa_role.id if sa_role else False))
    advisors_by_name = {re.sub(r"\s+", " ", u.full_name).strip().upper(): u for u in advisors_res.scalars().all()}

    # Resolve mapping
    mapping = payload.column_mapping or suggest_auto_mapping(columns)
    resolved_mapping = {}
    for target_key, col_name in mapping.items():
        canonical_key = TARGET_FIELD_ALIASES.get(target_key, target_key)
        resolved_mapping[canonical_key] = col_name

    # Create ImportBatch record
    batch = ImportBatch(
        tenant_id=tenant_id,
        uploaded_by=user_id,
        brand_id=payload.brand_id,
        branch_id=payload.branch_id,
        file_name=file_name,
        file_hash=file_hash,
        total_rows=total_rows,
        status="PROCESSING",
    )
    db.add(batch)
    await db.flush()

    success_count = 0
    skipped_count = 0
    skipped_identical_count = 0
    skipped_different_count = 0
    skipped_details: List[DuplicateSkippedDetail] = []
    error_count = 0
    warning_count = 0
    queues_created = 0
    happiness_scheduled = 0

    errors_list: List[ImportRowError] = []
    new_placeholder_advisors: List[str] = []
    unmapped_service_types: List[str] = []
    new_queues: List[FollowupQueue] = []

    seen_batch_keys: Dict[Tuple[uuid.UUID, str], Dict[str, Any]] = {}

    for row_idx, row in enumerate(records, start=1):
        try:
            # 1. Job Card No
            jc_col = resolved_mapping.get("job_card_no")
            raw_jc = row.get(jc_col) if jc_col else None
            jc_no = str(raw_jc).strip() if (raw_jc and str(raw_jc).strip().lower() not in ("nan", "none", "null")) else ""
            if not jc_no:
                error_count += 1
                errors_list.append(ImportRowError(
                    row_number=row_idx,
                    column=jc_col or "Job Card No",
                    rejected_value=str(raw_jc or ""),
                    reason="Missing required Job Card Number",
                    fix_hint="Each row must specify a valid Job Card No",
                ))
                continue

            # 2. Brand & Branch
            b_col = resolved_mapping.get("brand")
            br_col = resolved_mapping.get("branch")
            raw_b = row.get(b_col) if b_col else None
            raw_br = row.get(br_col) if br_col else None

            brand_obj, branch_obj, bb_err = await resolve_brand_and_branch(
                db, tenant_id, raw_b, raw_br, jc_no, payload.brand_id, payload.branch_id, all_brands, all_branches
            )
            if bb_err:
                error_count += 1
                errors_list.append(ImportRowError(
                    row_number=row_idx,
                    job_card_no=jc_no,
                    column=br_col or "Branch",
                    rejected_value=str(raw_br or raw_b),
                    reason=bb_err,
                    fix_hint="Check branch and brand spelling against dealership masters",
                ))
                continue

            # Check branch scope
            if not check_user_branch_scope(current_user, branch_obj.id):
                error_count += 1
                errors_list.append(ImportRowError(
                    row_number=row_idx,
                    job_card_no=jc_no,
                    column="Branch",
                    rejected_value=branch_obj.name,
                    reason=f"User lacks scope permission to import for branch '{branch_obj.name}'",
                    fix_hint="Contact Administrator to expand user permissions",
                ))
                continue

            # Update batch brand/branch reference if currently empty
            if not batch.brand_id:
                batch.brand_id = brand_obj.id
            if not batch.branch_id:
                batch.branch_id = branch_obj.id

            # 3. Contact Number
            phone_col = resolved_mapping.get("contact_number")
            raw_phone = row.get(phone_col) if phone_col else None
            clean_phone, phone_err = clean_phone_number(raw_phone)
            if phone_err:
                error_count += 1
                errors_list.append(ImportRowError(
                    row_number=row_idx,
                    job_card_no=jc_no,
                    column=phone_col or "Contact Number",
                    rejected_value=str(raw_phone),
                    reason=phone_err,
                    fix_hint="Enter a valid 10-digit Indian mobile number (e.g. 9876543210)",
                ))
                continue

            # 4. Job Card Date
            date_col = resolved_mapping.get("job_card_date")
            raw_date = row.get(date_col) if date_col else None
            parsed_date, date_err, date_warn = parse_date_value(raw_date)
            if date_err:
                error_count += 1
                errors_list.append(ImportRowError(
                    row_number=row_idx,
                    job_card_no=jc_no,
                    column=date_col or "Job Card Date",
                    rejected_value=str(raw_date),
                    reason=date_err,
                    fix_hint="Use date format DD-MM-YYYY (e.g. 01-11-2026)",
                ))
                continue
            if date_warn:
                warning_count += 1

            # 5. Customer Name
            cust_col = resolved_mapping.get("customer_name")
            cust_name = normalize_customer_name(row.get(cust_col))

            # 6. Reg No
            reg_col = resolved_mapping.get("reg_no")
            reg_no = normalize_reg_no(row.get(reg_col))
            if not reg_no:
                reg_no = f"TEMP-{jc_no}"

            # 7. Vin No
            vin_col = resolved_mapping.get("vin_no")
            clean_vin, vin_warn = normalize_vin(row.get(vin_col))
            if vin_warn:
                warning_count += 1

            # 8. Model
            model_col = resolved_mapping.get("model")
            model = str(row.get(model_col) or "Unknown Model").strip()

            # 9. Amount
            amt_col = resolved_mapping.get("total_service_amount")
            clean_amt, amt_err = parse_amount_value(row.get(amt_col))
            if amt_err:
                error_count += 1
                errors_list.append(ImportRowError(
                    row_number=row_idx,
                    job_card_no=jc_no,
                    column=amt_col or "Total Service Amount",
                    rejected_value=str(row.get(amt_col)),
                    reason=amt_err,
                    fix_hint="Ensure amount is a non-negative number",
                ))
                continue

            total_amount = clean_amt or Decimal("0.0")

            # 10. Service Type Matching
            st_col = resolved_mapping.get("service_type")
            raw_st = str(row.get(st_col) or "").strip()
            final_service_type = "Unmapped"
            if raw_st:
                matched_st = st_by_name.get(raw_st.upper()) or st_by_code.get(raw_st.upper())
                if matched_st:
                    final_service_type = matched_st.name
                else:
                    final_service_type = "Unmapped"
                    warning_count += 1
                    if raw_st not in unmapped_service_types:
                        unmapped_service_types.append(raw_st)
            else:
                final_service_type = "Periodic Maintenance Service"

            # 11. Service Advisor Matching or Inactive Placeholder Creation
            sa_col = resolved_mapping.get("service_advisor")
            raw_sa = str(row.get(sa_col) or "").strip()
            matched_advisor_id: Optional[uuid.UUID] = None
            final_advisor_name: Optional[str] = raw_sa or None

            if raw_sa:
                norm_sa = re.sub(r"\s+", " ", raw_sa).strip().upper()
                if norm_sa in advisors_by_name:
                    matched_advisor_id = advisors_by_name[norm_sa].id
                    final_advisor_name = advisors_by_name[norm_sa].full_name
                else:
                    # Create inactive placeholder user for unrecognised advisor
                    clean_slug = re.sub(r"[^a-z0-9]", ".", raw_sa.lower()).strip(".")
                    p_email = f"{clean_slug}@placeholder.apexauto.com"
                    pl_user = (await db.execute(select(User).where(User.tenant_id == tenant_id, User.email == p_email))).scalar_one_or_none()
                    if not pl_user and sa_role:
                        pl_user = User(
                            tenant_id=tenant_id,
                            role_id=sa_role.id,
                            email=p_email,
                            hashed_password=get_password_hash("Placeholder@12345"),
                            full_name=raw_sa,
                            is_active=False,
                        )
                        db.add(pl_user)
                        await db.flush()
                        advisors_by_name[norm_sa] = pl_user
                        new_placeholder_advisors.append(raw_sa)

                    if pl_user:
                        matched_advisor_id = pl_user.id
                        final_advisor_name = pl_user.full_name

            # 12. Duplicate Check: In-file & In-Database
            dupe_key = (branch_obj.id, jc_no)
            current_row_data = {
                "date": parsed_date,
                "amount": total_amount,
                "cust_name": cust_name,
                "phone": clean_phone,
                "reg_no": reg_no,
            }

            # Check in-file duplicate
            if dupe_key in seen_batch_keys:
                prev_row = seen_batch_keys[dupe_key]
                diffs = []
                if prev_row["amount"] != total_amount:
                    diffs.append(f"Amount (₹{prev_row['amount']} vs ₹{total_amount})")
                if prev_row["date"] != parsed_date:
                    diffs.append(f"Date ({prev_row['date']} vs {parsed_date})")
                if prev_row["cust_name"] != cust_name:
                    diffs.append(f"Customer ('{prev_row['cust_name']}' vs '{cust_name}')")

                diff_summary = ", ".join(diffs) if diffs else None
                dupe_type = "DIFFERENT" if diffs else "IDENTICAL"

                skipped_count += 1
                if dupe_type == "IDENTICAL":
                    skipped_identical_count += 1
                else:
                    skipped_different_count += 1

                skipped_details.append(DuplicateSkippedDetail(
                    row_number=row_idx,
                    job_card_no=jc_no,
                    branch_name=branch_obj.name,
                    duplicate_type=dupe_type,
                    diff_summary=diff_summary,
                ))
                continue

            seen_batch_keys[dupe_key] = current_row_data

            # Check in-database duplicate
            existing_jc_stmt = (
                select(JobCard)
                .options(selectinload(JobCard.customer), selectinload(JobCard.vehicle))
                .where(
                    JobCard.tenant_id == tenant_id,
                    JobCard.branch_id == branch_obj.id,
                    JobCard.job_card_no == jc_no,
                    JobCard.is_deleted == False,
                )
            )
            existing_jc = (await db.execute(existing_jc_stmt)).scalar_one_or_none()

            if existing_jc:
                diffs = []
                if existing_jc.total_amount != total_amount:
                    diffs.append(f"Amount (₹{existing_jc.total_amount} vs ₹{total_amount})")
                if existing_jc.job_card_date != parsed_date:
                    diffs.append(f"Date ({existing_jc.job_card_date} vs {parsed_date})")
                if existing_jc.customer and existing_jc.customer.name != cust_name:
                    diffs.append(f"Customer ('{existing_jc.customer.name}' vs '{cust_name}')")

                diff_summary = ", ".join(diffs) if diffs else None
                dupe_type = "DIFFERENT" if diffs else "IDENTICAL"

                if payload.duplicate_action == "SKIP":
                    skipped_count += 1
                    if dupe_type == "IDENTICAL":
                        skipped_identical_count += 1
                    else:
                        skipped_different_count += 1

                    skipped_details.append(DuplicateSkippedDetail(
                        row_number=row_idx,
                        job_card_no=jc_no,
                        branch_name=branch_obj.name,
                        duplicate_type=dupe_type,
                        diff_summary=diff_summary,
                    ))
                    continue
                else:
                    # UPDATE existing
                    existing_jc.job_card_date = parsed_date
                    existing_jc.service_advisor_name = final_advisor_name
                    existing_jc.service_advisor_id = matched_advisor_id
                    existing_jc.service_type = final_service_type
                    existing_jc.total_amount = total_amount
                    success_count += 1
                    continue

            # 13. Customer Upsert
            p_hash = hash_phone(clean_phone)
            cust_stmt = select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.phone_hash == p_hash,
                Customer.is_deleted == False,
            )
            customer = (await db.execute(cust_stmt)).scalar_one_or_none()
            if not customer:
                customer = Customer(
                    tenant_id=tenant_id,
                    name=cust_name,
                    phone=encrypt_phone(clean_phone),
                    phone_hash=p_hash,
                )
                db.add(customer)
                await db.flush()

            # 14. Vehicle Upsert
            veh_stmt = select(Vehicle).where(
                Vehicle.tenant_id == tenant_id,
                Vehicle.reg_no == reg_no,
                Vehicle.is_deleted == False,
            )
            vehicle = (await db.execute(veh_stmt)).scalar_one_or_none()
            if not vehicle:
                vehicle = Vehicle(
                    tenant_id=tenant_id,
                    brand_id=brand_obj.id,
                    customer_id=customer.id,
                    reg_no=reg_no,
                    vin=clean_vin,
                    model=model,
                )
                db.add(vehicle)
                await db.flush()

            # 15. Create JobCard
            job_card = JobCard(
                tenant_id=tenant_id,
                brand_id=brand_obj.id,
                branch_id=branch_obj.id,
                customer_id=customer.id,
                vehicle_id=vehicle.id,
                import_batch_id=batch.id,
                job_card_no=jc_no,
                job_card_date=parsed_date,
                service_advisor_name=final_advisor_name,
                service_advisor_id=matched_advisor_id,
                service_type=final_service_type,
                total_amount=total_amount,
                uploaded_by_id=user_id,
            )
            db.add(job_card)
            await db.flush()

            # 16. Create FollowupQueue items from brand's enabled programs
            programs = await ConfigResolverService.get_active_programs_for_brand(db, tenant_id, brand_obj.id)
            if not programs:
                programs = [type('Prog', (), {'id': None, 'code': 'PSF', 'trigger': 'ON_IMPORT', 'channel': 'PHONE'})()]

            for prog in programs:
                trigger = prog.trigger.upper().strip() if prog.trigger else "ON_IMPORT"
                if trigger.startswith("AFTER_DAYS"):
                    match = re.search(r"\d+", trigger)
                    days = int(match.group(0)) if match else 15
                    due_at = datetime.combine(parsed_date + timedelta(days=days), time(10, 0))
                elif trigger == "AFTER_COMPLAINT_CLOSURE":
                    continue
                else: # ON_IMPORT
                    due_at = datetime.combine(parsed_date + timedelta(days=1), time(10, 0))

                queue_item = FollowupQueue(
                    tenant_id=tenant_id,
                    job_card_id=job_card.id,
                    program_id=prog.id if hasattr(prog, 'id') else None,
                    queue_type=prog.code,
                    status="PENDING",
                    assigned_to_id=None,
                    due_at=due_at,
                    attempts=0,
                    contacted_count=0,
                )
                db.add(queue_item)
                new_queues.append(queue_item)
                queues_created += 1
                if prog.code == "HAPPINESS":
                    happiness_scheduled += 1

            success_count += 1

        except Exception as e:
            error_count += 1
            errors_list.append(ImportRowError(
                row_number=row_idx,
                job_card_no=jc_no if "jc_no" in locals() else "N/A",
                reason=str(e),
                fix_hint="Check row values for format discrepancies",
            ))

    # Update Batch record
    batch.processed_rows = total_rows
    batch.success_rows = success_count
    batch.error_rows = error_count
    batch.error_log = {
        "errors": [err.model_dump() for err in errors_list],
        "skipped_identical": skipped_identical_count,
        "skipped_different": skipped_different_count,
        "skipped_details": [d.model_dump() for d in skipped_details],
        "new_placeholder_advisors": new_placeholder_advisors,
        "unmapped_service_types": unmapped_service_types,
    }
    batch.status = "COMPLETED" if error_count < total_rows else "FAILED"
    await db.flush()

    # Automatically divide calls equally among present CREs
    alloc_run = None
    if new_queues:
        alloc_run = await allocate_queue_items(
            db=db,
            tenant_id=tenant_id,
            queue_items=new_queues,
            import_batch_id=batch.id,
            started_by_id=user_id,
            run_type="IMPORT_ALLOCATION",
        )

    await db.commit()

    return ImportSummaryResponse(
        batch_id=batch.id,
        file_name=file_name,
        file_hash=file_hash,
        total_rows=total_rows,
        success_rows=success_count,
        skipped_rows=skipped_count,
        skipped_identical_count=skipped_identical_count,
        skipped_different_count=skipped_different_count,
        skipped_details=skipped_details,
        warning_rows=warning_count,
        error_rows=error_count,
        queues_created=queues_created,
        happiness_scheduled=happiness_scheduled,
        new_placeholder_advisors=new_placeholder_advisors,
        unmapped_service_types=unmapped_service_types,
        errors=errors_list,
        allocation_run_id=alloc_run.id if alloc_run else None,
        allocation_summary=alloc_run.summary if alloc_run else None,
    )


# -------------------------------------------------------------
# Downloadable Error Report (Excel .xlsx)
# -------------------------------------------------------------
def generate_error_report_xlsx(
    file_name: str,
    batch_id: str,
    errors: List[Dict[str, Any]],
) -> bytes:
    """
    Generates a professional Excel (.xlsx) report containing row errors and actionable fix hints.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Import Errors & Fix Hints"

    # Header styling
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bg_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark Blue
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1'),
    )

    headers = ["Row Number", "Job Card No", "Column", "Rejected Value", "Reason", "Fix Hint"]
    ws.append(headers)

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = bg_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for item in errors:
        ws.append([
            item.get("row_number") or item.get("row"),
            item.get("job_card_no") or "N/A",
            item.get("column") or "N/A",
            str(item.get("rejected_value") if item.get("rejected_value") is not None else ""),
            item.get("reason") or "",
            item.get("fix_hint") or "",
        ])

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


# -------------------------------------------------------------
# Sample Template Generator (XLSX & CSV)
# -------------------------------------------------------------
def generate_sample_template(file_format: str = "xlsx") -> Tuple[bytes, str, str]:
    """
    Generates downloadable sample template with the exact 13 Standard DMS headers and 2 example rows.
    Returns (bytes, content_type, filename).
    """
    headers = [
        "Brand",
        "Branch",
        "Brand Logo",
        "Job Card No",
        "Job Card Date",
        "Customer Name",
        "Contact Number",
        "Vin No",
        "Reg No",
        "Model",
        "Service Advisor",
        "Service Type",
        "Total Service Amount",
    ]

    sample_rows = [
        [
            "Hyundai",
            "HYUNDAI HUBLI",
            "",
            "S8211_R202600101",
            "01-11-2026",
            "Ramesh Patil",
            "9876543210",
            "MALBB51BLHM123456",
            "KA25EA1234",
            "Creta",
            "Deepa Hiremath",
            "Periodic Maintenance Service",
            "7500.00",
        ],
        [
            "Tata Motors",
            "TATA MOTORS BELLARY",
            "",
            "T8211_R202600102",
            "02-11-2026",
            "Suresh Deshmukh",
            "9845012345",
            "MAT612051E8A98765",
            "KA34M5678",
            "Nexon",
            "Rajesh Kumar",
            "Running Repair",
            "3200.50",
        ],
    ]

    if file_format.lower() == "csv":
        output = io.StringIO()
        import csv
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(sample_rows)
        return output.getvalue().encode("utf-8-sig"), "text/csv", "Standard_DMS_Template.csv"
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "Standard DMS Template"

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        bg_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")

        ws.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = bg_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row in sample_rows:
            ws.append(row)

        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max(max_len + 4, 15)

        output_bytes = io.BytesIO()
        wb.save(output_bytes)
        return output_bytes.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Standard_DMS_Template.xlsx"


# -------------------------------------------------------------
# Webhook Ingestion & History Listing
# -------------------------------------------------------------
async def create_job_card_from_webhook(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    payload: DmsJobCardWebhook,
) -> Dict[str, Any]:
    """Ingests a single job card via real-time DMS Webhook."""
    # 1. Fetch brand
    brand = (await db.execute(select(Brand).where(Brand.tenant_id == tenant_id, Brand.code == payload.brand_code.upper()))).scalar_one_or_none()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Brand '{payload.brand_code}' not found")

    # 2. Fetch branch
    branch = (await db.execute(select(Branch).where(Branch.tenant_id == tenant_id, Branch.code == payload.branch_code.upper()))).scalar_one_or_none()
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Branch '{payload.branch_code}' not found")

    is_hyundai = "HYUNDAI" in brand.name.upper() or brand.code.upper() in ["HYUN", "HYUNDAI"]

    # 3. Clean phone
    clean_phone, phone_err = clean_phone_number(payload.customer_phone)
    if phone_err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=phone_err)

    # 4. Check duplicate
    existing_jc = (
        await db.execute(
            select(JobCard).where(
                JobCard.tenant_id == tenant_id,
                JobCard.branch_id == branch.id,
                JobCard.job_card_no == payload.job_card_no.strip(),
                JobCard.is_deleted == False,
            )
        )
    ).scalar_one_or_none()
    if existing_jc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job Card '{payload.job_card_no}' already exists in branch '{branch.name}'",
        )

    # 5. Customer upsert
    p_hash = hash_phone(clean_phone)
    customer = (
        await db.execute(
            select(Customer).where(
                Customer.tenant_id == tenant_id,
                Customer.phone_hash == p_hash,
                Customer.is_deleted == False,
            )
        )
    ).scalar_one_or_none()

    if not customer:
        customer = Customer(
            tenant_id=tenant_id,
            name=payload.customer_name.strip(),
            phone=encrypt_phone(clean_phone),
            phone_hash=p_hash,
            alt_phone=encrypt_phone(clean_phone_number(payload.customer_alt_phone)[0]) if payload.customer_alt_phone else None,
            email=payload.customer_email,
        )
        db.add(customer)
        await db.flush()

    # 6. Vehicle upsert
    vehicle = (
        await db.execute(
            select(Vehicle).where(
                Vehicle.tenant_id == tenant_id,
                Vehicle.reg_no == payload.reg_no.strip().upper(),
                Vehicle.is_deleted == False,
            )
        )
    ).scalar_one_or_none()

    if not vehicle:
        vehicle = Vehicle(
            tenant_id=tenant_id,
            brand_id=brand.id,
            customer_id=customer.id,
            reg_no=payload.reg_no.strip().upper(),
            vin=payload.vin.strip() if payload.vin else None,
            model=payload.model.strip(),
            variant=payload.variant,
        )
        db.add(vehicle)
        await db.flush()

    # 7. JobCard
    job_card = JobCard(
        tenant_id=tenant_id,
        brand_id=brand.id,
        branch_id=branch.id,
        customer_id=customer.id,
        vehicle_id=vehicle.id,
        job_card_no=payload.job_card_no.strip(),
        job_card_date=payload.job_card_date,
        service_advisor_name=payload.service_advisor,
        technician_name=payload.technician,
        service_type=payload.service_type or "Periodic Maintenance Service",
        total_amount=payload.total_amount,
        odometer_reading=payload.odometer,
    )
    db.add(job_card)
    await db.flush()

    # 8. Followup Queue from brand's enabled programs
    programs = await ConfigResolverService.get_active_programs_for_brand(db, tenant_id, brand.id)
    if not programs:
        programs = [type('Prog', (), {'id': None, 'code': 'PSF', 'trigger': 'ON_IMPORT', 'channel': 'PHONE'})()]

    created_queue_id = None
    happiness_created = False
    for prog in programs:
        trigger = prog.trigger.upper().strip() if prog.trigger else "ON_IMPORT"
        if trigger.startswith("AFTER_DAYS"):
            match = re.search(r"\d+", trigger)
            days = int(match.group(0)) if match else 15
            due_at = datetime.combine(payload.job_card_date + timedelta(days=days), time(10, 0))
        elif trigger == "AFTER_COMPLAINT_CLOSURE":
            continue
        else:
            due_at = datetime.combine(payload.job_card_date + timedelta(days=1), time(10, 0))

        q_item = FollowupQueue(
            tenant_id=tenant_id,
            job_card_id=job_card.id,
            program_id=prog.id if hasattr(prog, 'id') else None,
            queue_type=prog.code,
            status="PENDING",
            due_at=due_at,
            attempts=0,
            contacted_count=0,
        )
        db.add(q_item)
        await db.flush()
        if created_queue_id is None:
            created_queue_id = str(q_item.id)
        if prog.code == "HAPPINESS":
            happiness_created = True

    await db.commit()

    return {
        "status": "success",
        "job_card_id": str(job_card.id),
        "job_card_no": job_card.job_card_no,
        "customer_id": str(customer.id),
        "queue_id": created_queue_id,
        "psf_queue_id": created_queue_id,
        "happiness_scheduled": happiness_created,
    }


async def list_import_batches(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> List[ImportBatch]:
    """Retrieves previous import batches with uploader and brand/branch details."""
    stmt = (
        select(ImportBatch)
        .options(
            selectinload(ImportBatch.brand),
            selectinload(ImportBatch.branch),
            selectinload(ImportBatch.uploader),
        )
        .where(ImportBatch.tenant_id == tenant_id, ImportBatch.is_deleted == False)
        .order_by(ImportBatch.created_at.desc())
        .limit(limit)
    )
    results = await db.execute(stmt)
    return list(results.scalars().all())
