"""
================================================================================
FILE PURPOSE: Configurable Scoring & Outcome Service.
Supports all answer types: YES_NO, YES_NO_NA, RATING (min/max/labels), NPS_0_10,
SINGLE_SELECT, MULTI_SELECT, TEXT, NUMBER, FILE_UPLOAD.
Computes 0-100 normalized scores, KPI tag aggregations, overall result by config
(chosen question, average, weighted average, NPS), and maps to dynamic outcome bands.
================================================================================
"""
import uuid
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.questionnaire import Questionnaire, Question
from app.models.additional import RatingScale, RatingScaleBand

logger = logging.getLogger("psf.scoring_service")


# Brand default scales cache to prevent repeated DB lookups during batch processing
_BRAND_SCALES_CACHE: Dict[str, List[Dict[str, Any]]] = {
    "HYUN": [
        {"min_score": 10, "max_score": 10, "label": "Delight", "derived_case_status": "Delight", "is_delight": True, "is_complaint_trigger": False},
        {"min_score": 9, "max_score": 9, "label": "Satisfied (Actionable)", "derived_case_status": "Satisfied", "is_delight": False, "is_complaint_trigger": True},
        {"min_score": 6, "max_score": 8, "label": "Non-Delight", "derived_case_status": "Non-Delight", "is_delight": False, "is_complaint_trigger": True},
        {"min_score": 1, "max_score": 5, "label": "Dissatisfied", "derived_case_status": "Dissatisfied", "is_delight": False, "is_complaint_trigger": True},
    ],
    "TATA": [
        {"min_score": 5, "max_score": 5, "label": "Delight", "derived_case_status": "Delight", "is_delight": True, "is_complaint_trigger": False},
        {"min_score": 4, "max_score": 4, "label": "Satisfied", "derived_case_status": "Satisfied", "is_delight": False, "is_complaint_trigger": False},
        {"min_score": 1, "max_score": 3, "label": "Dissatisfied", "derived_case_status": "Dissatisfied", "is_delight": False, "is_complaint_trigger": True},
    ],
    "MG": [
        {"min_score": 9, "max_score": 10, "label": "Satisfied", "derived_case_status": "Satisfied", "is_delight": True, "is_complaint_trigger": False},
        {"min_score": 1, "max_score": 8, "label": "Dissatisfied", "derived_case_status": "Dissatisfied", "is_delight": False, "is_complaint_trigger": True},
    ],
    "ATHER": [
        {"min_score": 9, "max_score": 10, "label": "Promoter (Delight)", "derived_case_status": "Delight", "is_delight": True, "is_complaint_trigger": False},
        {"min_score": 7, "max_score": 8, "label": "Passive", "derived_case_status": "Satisfied", "is_delight": False, "is_complaint_trigger": False},
        {"min_score": 0, "max_score": 6, "label": "Detractor", "derived_case_status": "Dissatisfied", "is_delight": False, "is_complaint_trigger": True},
    ],
}


class ScoringService:
    @staticmethod
    def normalize_single_answer(
        q_type: str,
        raw_val: Any,
        rating_min: Optional[int] = None,
        rating_max: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[float], Any]:
        """
        Normalizes any supported question answer type to a 0-100 float score and cleaned raw value.
        Supported types:
        - YES_NO, YES_NO_NA
        - RATING, rating_5, rating_10
        - NPS_0_10, nps_10
        - SINGLE_SELECT, MULTI_SELECT
        - TEXT, NUMBER, FILE_UPLOAD
        """
        if raw_val is None:
            return None, None

        # If answer was already wrapped as {"raw": ..., "score": ...}
        if isinstance(raw_val, dict) and "raw" in raw_val:
            raw_unwrapped = raw_val["raw"]
            if "score" in raw_val and raw_val["score"] is not None:
                return float(raw_val["score"]), raw_unwrapped
            raw_val = raw_unwrapped

        type_lower = (q_type or "yes_no").lower()

        # 1. YES_NO and YES_NO_NA
        if type_lower in ["yes_no", "yes_no_na"]:
            str_val = str(raw_val).strip().lower()
            if str_val in ["true", "yes", "1", "y"]:
                return 100.0, "Yes"
            elif str_val in ["false", "no", "0", "n"]:
                return 0.0, "No"
            elif str_val in ["na", "n/a", "not applicable", "none"]:
                return None, "NA"
            return None, str(raw_val)

        # 2. NPS 0 to 10
        elif type_lower in ["nps_0_10", "nps_10"]:
            try:
                num = float(raw_val)
                clamped = max(0.0, min(10.0, num))
                return round(clamped * 10.0, 2), int(clamped) if clamped.is_integer() else clamped
            except (ValueError, TypeError):
                return None, raw_val

        # 3. RATING (configurable min/max, e.g. 1-5 or 1-10)
        elif type_lower in ["rating", "rating_5", "rating_10"]:
            r_min = rating_min if rating_min is not None else (1 if type_lower != "nps_10" else 0)
            r_max = rating_max if rating_max is not None else (5 if type_lower == "rating_5" else 10)
            try:
                num = float(raw_val)
                clamped = max(float(r_min), min(float(r_max), num))
                if r_max == r_min:
                    score = 100.0
                elif r_min == 1:
                    score = (clamped / float(r_max)) * 100.0
                else:
                    score = ((clamped - float(r_min)) / (float(r_max) - float(r_min))) * 100.0
                return round(score, 2), int(clamped) if clamped.is_integer() else clamped
            except (ValueError, TypeError):
                return None, raw_val

        # 4. SINGLE_SELECT
        elif type_lower == "single_select":
            str_val = str(raw_val).strip()
            score: Optional[float] = None
            if options and isinstance(options, dict):
                # options can map value -> score weight
                scores_map = options.get("scores") or options
                if isinstance(scores_map, dict) and str_val in scores_map:
                    try:
                        score = float(scores_map[str_val])
                    except (ValueError, TypeError):
                        pass
            return score, str_val

        # 5. MULTI_SELECT
        elif type_lower == "multi_select":
            val_list = raw_val if isinstance(raw_val, list) else [str(raw_val)]
            return None, val_list

        # 6. NUMBER
        elif type_lower == "number":
            try:
                num = float(raw_val)
                return None, num
            except (ValueError, TypeError):
                return None, raw_val

        # 7. TEXT & FILE_UPLOAD
        else:
            return None, str(raw_val)

    @classmethod
    def process_and_normalize_answers(
        cls,
        raw_answers: Dict[str, Any],
        questions: List[Question],
    ) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[float]]]:
        """
        Normalizes all submitted answers against the question definitions.
        Returns:
        - normalized_answers: {key: {"raw": raw, "score": score, "reason": opt_reason}}
        - kpi_score_buckets: {kpi_tag: [score1, score2, ...]}
        """
        q_map = {q.key: q for q in questions}
        normalized: Dict[str, Dict[str, Any]] = {}
        kpi_buckets: Dict[str, List[float]] = {}

        for key, val in raw_answers.items():
            reason = None
            if isinstance(val, dict):
                reason = val.get("reason")
                raw_item = val.get("raw", val)
            else:
                raw_item = val

            q = q_map.get(key)
            q_type = q.type if q else "yes_no"
            r_min = getattr(q, "rating_min", None)
            r_max = getattr(q, "rating_max", None)
            options = getattr(q, "options", None)

            score, cleaned_raw = cls.normalize_single_answer(
                q_type=q_type,
                raw_val=raw_item,
                rating_min=r_min,
                rating_max=r_max,
                options=options,
            )

            entry = {"raw": cleaned_raw, "score": score}
            if reason:
                entry["reason"] = reason
            normalized[key] = entry

            # Collect into KPI tag bucket
            if score is not None and q:
                kpi_tag = getattr(q, "kpi_tag", None) or "SERVICE_QUALITY"
                kpi_buckets.setdefault(kpi_tag, []).append(score)

        return normalized, kpi_buckets

    @classmethod
    def calculate_overall_result(
        cls,
        normalized_answers: Dict[str, Dict[str, Any]],
        questions: List[Question],
        method: str = "WEIGHTED_AVERAGE",
        chosen_question_key: Optional[str] = None,
    ) -> Tuple[float, Optional[int], Optional[str]]:
        """
        Calculates overall CSAT (0-100), NPS score (0-10), and NPS category
        using configurable method: CHOSEN_QUESTION | AVERAGE | WEIGHTED_AVERAGE | NPS.
        """
        q_map = {q.key: q for q in questions}
        nps_rating: Optional[int] = None
        nps_category: Optional[str] = None

        # Look for NPS question if any
        for key, item in normalized_answers.items():
            q = q_map.get(key)
            q_type = (q.type or "").lower() if q else ""
            if q_type in ["nps_10", "nps_0_10"] or "nps" in key.lower():
                try:
                    raw_val = item.get("raw")
                    if raw_val is not None:
                        nps_rating = int(float(raw_val))
                except (ValueError, TypeError):
                    pass

        if nps_rating is not None:
            if nps_rating >= 9:
                nps_category = "PROMOTER"
            elif nps_rating >= 7:
                nps_category = "PASSIVE"
            else:
                nps_category = "DETRACTOR"

        method_upper = (method or "WEIGHTED_AVERAGE").upper()

        # 1. CHOSEN_QUESTION
        if method_upper == "CHOSEN_QUESTION" and chosen_question_key:
            chosen = normalized_answers.get(chosen_question_key)
            if chosen and chosen.get("score") is not None:
                return round(float(chosen["score"]), 2), nps_rating, nps_category

        # 2. AVERAGE
        if method_upper == "AVERAGE":
            scores = [float(a["score"]) for a in normalized_answers.values() if a.get("score") is not None]
            if scores:
                return round(sum(scores) / len(scores), 2), nps_rating, nps_category
            return 100.0, nps_rating, nps_category

        # 3. NPS
        if method_upper == "NPS" and nps_rating is not None:
            return float(nps_rating * 10), nps_rating, nps_category

        # 4. WEIGHTED_AVERAGE (default)
        total_weighted = Decimal("0.0")
        total_weight = Decimal("0.0")

        for key, item in normalized_answers.items():
            score = item.get("score")
            if score is None:
                continue
            q = q_map.get(key)
            weight = Decimal(str(getattr(q, "weight", 1.0) or 1.0))
            total_weighted += Decimal(str(score)) * weight
            total_weight += weight

        if total_weight > Decimal("0.0"):
            overall_csat = float(round(total_weighted / total_weight, 2))
        else:
            overall_csat = 100.0

        return overall_csat, nps_rating, nps_category

    @classmethod
    async def resolve_bands_and_outcome(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        brand_id: Optional[uuid.UUID],
        brand_code: Optional[str],
        overall_score: float,
        raw_rating: Optional[int] = None,
    ) -> Tuple[str, bool, bool]:
        """
        Maps score / rating to outcome status (Delight, Satisfied, Non-Delight, Dissatisfied),
        is_delight flag, and is_complaint_trigger flag using dynamic RatingScaleBand in DB.
        """
        # If raw_rating is provided (e.g. 1-10 or 1-5 rating), check DB scale bands directly
        if brand_id:
            stmt = (
                select(RatingScaleBand)
                .join(RatingScale, RatingScale.id == RatingScaleBand.scale_id)
                .where(
                    RatingScale.tenant_id == tenant_id,
                    RatingScale.brand_id == brand_id,
                    RatingScale.is_active.is_(True),
                )
            )
            bands = (await db.execute(stmt)).scalars().all()
            if bands:
                # Determine comparison value: raw rating if available, else scaled to max_rating
                max_r = max(b.max_score for b in bands)
                compare_val = raw_rating if raw_rating is not None else int(round((overall_score / 100.0) * max_r))
                for b in bands:
                    if b.min_score <= compare_val <= b.max_score:
                        return b.derived_case_status, b.is_delight, b.is_complaint_trigger

        # Fallback to cached brand scales
        b_key = (brand_code or "HYUN").upper()
        if "TATA" in b_key:
            cache_bands = _BRAND_SCALES_CACHE["TATA"]
            comp = raw_rating if raw_rating is not None else int(round((overall_score / 100.0) * 5))
        elif "MG" in b_key:
            cache_bands = _BRAND_SCALES_CACHE["MG"]
            comp = raw_rating if raw_rating is not None else int(round((overall_score / 100.0) * 10))
        elif "ATHER" in b_key:
            cache_bands = _BRAND_SCALES_CACHE["ATHER"]
            comp = raw_rating if raw_rating is not None else int(round((overall_score / 100.0) * 10))
        else:
            cache_bands = _BRAND_SCALES_CACHE["HYUN"]
            comp = raw_rating if raw_rating is not None else int(round((overall_score / 100.0) * 10))

        for b in cache_bands:
            if b["min_score"] <= comp <= b["max_score"]:
                return b["derived_case_status"], b["is_delight"], b["is_complaint_trigger"]

        return "Satisfied", False, False
