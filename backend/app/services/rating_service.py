"""
================================================================================
FILE PURPOSE: OEM Rating Scales & Satisfaction Bands Service.
Maps customer numeric ratings into satisfaction bands using dynamic scale band definitions.
================================================================================
"""
import uuid
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.additional import RatingScale, RatingScaleBand


def _resolve_from_scale_list(bands_list, rating: int) -> Tuple[str, bool, bool]:
    for b in bands_list:
        min_s = b.get("min_score") if isinstance(b, dict) else b.min_score
        max_s = b.get("max_score") if isinstance(b, dict) else b.max_score
        status = b.get("derived_case_status") if isinstance(b, dict) else b.derived_case_status
        is_delight = b.get("is_delight", False) if isinstance(b, dict) else b.is_delight
        is_trigger = b.get("is_complaint_trigger", False) if isinstance(b, dict) else b.is_complaint_trigger

        if min_s <= rating <= max_s:
            return status, is_delight, is_trigger

    return "Dissatisfied", False, True


async def derive_case_status_from_db(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    brand_id: uuid.UUID,
    rating: int,
) -> Tuple[str, bool, bool]:
    """
    Derives case status, is_delight, and is_complaint_trigger
    from the brand's configured RatingScaleBand.
    Returns: (case_status, is_delight, is_complaint_trigger)
    """
    stmt = (
        select(RatingScaleBand)
        .join(RatingScale, RatingScale.id == RatingScaleBand.scale_id)
        .where(
            RatingScale.tenant_id == tenant_id,
            RatingScale.brand_id == brand_id,
            RatingScale.is_active == True,
            RatingScaleBand.min_score <= rating,
            RatingScaleBand.max_score >= rating,
        )
    )
    band = (await db.execute(stmt)).scalar_one_or_none()
    if band:
        return band.derived_case_status, band.is_delight, band.is_complaint_trigger

    # Fallback to configured default scale bands
    from app.services.scoring_service import _BRAND_SCALES_CACHE
    return _resolve_from_scale_list(_BRAND_SCALES_CACHE["HYUN"], rating)


def derive_case_status_memory(
    brand_code_or_name: str,
    rating: int,
) -> Tuple[str, bool, bool]:
    """
    In-memory synchronous version of rating band derivation
    configured per brand guidelines.
    """
    from app.services.scoring_service import _BRAND_SCALES_CACHE

    brand_clean = (brand_code_or_name or "").upper()
    if "TATA" in brand_clean:
        bands = _BRAND_SCALES_CACHE["TATA"]
    elif "MG" in brand_clean:
        bands = _BRAND_SCALES_CACHE["MG"]
    elif "ATHER" in brand_clean:
        bands = _BRAND_SCALES_CACHE["ATHER"]
    else:
        bands = _BRAND_SCALES_CACHE["HYUN"]

    return _resolve_from_scale_list(bands, rating)
