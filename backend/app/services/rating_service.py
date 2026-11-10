"""
================================================================================
FILE PURPOSE: OEM Rating Scales & Satisfaction Bands Service.
Maps raw customer numeric scores into manufacturer satisfaction bands
(e.g. Delight, Satisfied, Dissatisfied) according to brand guidelines.

KEY RESPONSIBILITIES:
- Defines rating scale rules per OEM (Hyundai 1-10 scale, Tata 1-5 scale).
- Derives overall sentiment from customer answers (`derive_sentiment_from_score`).

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Customer marked Dissatisfied when they gave 9/10
  -> Cause: Incorrect rating scale configuration in database.
  -> What should you do: Review rating scale thresholds in Admin Console -> Rating Scales tab.
================================================================================
"""
import uuid
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.additional import RatingScale, RatingScaleBand


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

    # Fallback heuristic if no scale found
    if rating >= 10:
        return "Delight", True, False
    elif rating == 9:
        # In real Hyundai data, 9 triggers a complaint (e.g. WATSAPP RATING <=9)
        return "Satisfied", False, True
    elif rating >= 6:
        return "Non-Delight", False, True
    else:
        return "Dissatisfied", False, True


def derive_case_status_memory(
    brand_code_or_name: str,
    rating: int,
) -> Tuple[str, bool, bool]:
    """
    In-memory synchronous version of rating band derivation
    supporting Hyundai, Tata Motors, and MG Motors rules directly.
    """
    brand_clean = (brand_code_or_name or "").upper()

    if "TATA" in brand_clean:
        # Tata: 5 Good, 4 Satisfied, 1-3 Dissatisfied
        if rating >= 5:
            return "Delight", True, False
        elif rating == 4:
            return "Satisfied", False, False
        else:
            return "Dissatisfied", False, True

    elif "MG" in brand_clean:
        # MG: 1-8 Dissatisfied/Poor, 9-10 Satisfied
        if rating >= 9:
            return "Satisfied", True, False
        else:
            return "Dissatisfied", False, True

    else:
        # Hyundai (default): 1-5 Poor, 6-8 Average, 9 Satisfied (triggers complaint in real data), 10 Delight
        if rating >= 10:
            return "Delight", True, False
        elif rating == 9:
            return "Satisfied", False, True
        elif rating >= 6:
            return "Non-Delight", False, True
        else:
            return "Dissatisfied", False, True

