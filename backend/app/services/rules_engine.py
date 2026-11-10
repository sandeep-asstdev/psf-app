"""
================================================================================
FILE PURPOSE: Pure Data-Driven JSON Rules Engine.
Evaluates ordered business rules without arbitrary code execution:
IF conditions (overall score, kpi_tag score, answer, service type, branch, amount)
THEN actions (create complaint with category + severity, assign to role/user, notify, schedule callback, set outcome).
Can run in live mode (persisting complaints/notifications) or in simulation mode (dry run).
================================================================================
"""
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import OutcomeRule
from app.models.complaint import Complaint, ComplaintCategory
from app.models.followup import Reminder
from app.services.notification_service import NotificationService

logger = logging.getLogger("psf.rules_engine")


class RulesEngineService:
    @staticmethod
    def _evaluate_operator(actual: Any, op: str, expected: Any) -> bool:
        if actual is None:
            return False

        op_lower = op.lower().strip()
        try:
            if op_lower in ["==", "=", "equals"]:
                return str(actual).strip().lower() == str(expected).strip().lower()
            elif op_lower in ["!=", "<>", "not_equals"]:
                return str(actual).strip().lower() != str(expected).strip().lower()
            elif op_lower in ["<=", "lte"]:
                return float(actual) <= float(expected)
            elif op_lower in ["<", "lt"]:
                return float(actual) < float(expected)
            elif op_lower in [">=", "gte"]:
                return float(actual) >= float(expected)
            elif op_lower in [">", "gt"]:
                return float(actual) > float(expected)
            elif op_lower in ["in", "contains"]:
                if isinstance(expected, list):
                    return actual in expected or str(actual) in [str(x) for x in expected]
                return str(actual) in str(expected)
            elif op_lower in ["not_in"]:
                if isinstance(expected, list):
                    return actual not in expected and str(actual) not in [str(x) for x in expected]
                return str(actual) not in str(expected)
            elif op_lower == "between" and isinstance(expected, (list, tuple)) and len(expected) == 2:
                return float(expected[0]) <= float(actual) <= float(expected[1])
        except (ValueError, TypeError):
            return False

        return False

    @classmethod
    def match_conditions(cls, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluates rule conditions against the provided context.
        context keys:
        - overall_score: float
        - kpi_scores: Dict[str, float]
        - answers: Dict[str, Any] (or Dict[str, Dict[str, Any]])
        - service_type: str
        - branch_id: str / UUID
        - branch_code: str
        - total_amount: float
        """
        if not conditions:
            return False

        # Condition: overall_score
        if "score" in conditions:
            c = conditions["score"]
            actual = context.get("overall_score")
            if not cls._evaluate_operator(actual, c.get("operator", "<="), c.get("value")):
                return False

        # Condition: kpi_tag score
        if "kpi_tag" in conditions:
            c = conditions["kpi_tag"]
            tag = c.get("tag")
            kpi_scores = context.get("kpi_scores", {})
            actual = kpi_scores.get(tag)
            if not cls._evaluate_operator(actual, c.get("operator", "<="), c.get("value")):
                return False

        # Condition: question answer
        if "answer" in conditions:
            c = conditions["answer"]
            q_key = c.get("question_key")
            answers = context.get("answers", {})
            actual_entry = answers.get(q_key)
            actual_val = actual_entry.get("raw") if isinstance(actual_entry, dict) else actual_entry
            if not cls._evaluate_operator(actual_val, c.get("operator", "=="), c.get("value")):
                return False

        # Condition: service_type
        if "service_type" in conditions:
            c = conditions["service_type"]
            actual = context.get("service_type")
            if not cls._evaluate_operator(actual, c.get("operator", "in"), c.get("value")):
                return False

        # Condition: branch
        if "branch" in conditions:
            c = conditions["branch"]
            actual_code = context.get("branch_code")
            actual_id = str(context.get("branch_id")) if context.get("branch_id") else None
            matched = cls._evaluate_operator(actual_code, c.get("operator", "=="), c.get("value")) or \
                      cls._evaluate_operator(actual_id, c.get("operator", "=="), c.get("value"))
            if not matched:
                return False

        # Condition: amount
        if "amount" in conditions:
            c = conditions["amount"]
            actual = context.get("total_amount")
            if not cls._evaluate_operator(actual, c.get("operator", ">="), c.get("value")):
                return False

        return True

    @classmethod
    async def evaluate_rules(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        brand_id: Optional[uuid.UUID],
        program_id: Optional[uuid.UUID],
        context: Dict[str, Any],
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Fetches enabled OutcomeRule records ordered by priority asc.
        Evaluates each rule. Returns combined action result.
        """
        stmt = (
            select(OutcomeRule)
            .where(
                OutcomeRule.tenant_id == tenant_id,
                OutcomeRule.enabled.is_(True),
            )
            .order_by(OutcomeRule.priority.asc(), OutcomeRule.created_at.asc())
        )
        if brand_id:
            stmt = stmt.where((OutcomeRule.brand_id == brand_id) | (OutcomeRule.brand_id.is_(None)))

        rules = (await db.execute(stmt)).scalars().all()

        matched_rules: List[str] = []
        resulting_outcome: Optional[str] = None
        resulting_complaint: Optional[Dict[str, Any]] = None
        resulting_notifications: List[Dict[str, Any]] = []
        resulting_callback: Optional[Dict[str, Any]] = None

        for rule in rules:
            if cls.match_conditions(rule.conditions, context):
                matched_rules.append(rule.name)
                actions = rule.actions or {}

                # 1. Action: set_outcome
                if "set_outcome" in actions:
                    resulting_outcome = actions["set_outcome"].get("case_status", resulting_outcome)

                # 2. Action: create_complaint
                if "create_complaint" in actions:
                    c_act = actions["create_complaint"]
                    resulting_complaint = {
                        "category": c_act.get("category", "SERVICE_QUALITY"),
                        "severity": c_act.get("severity", "MEDIUM"),
                        "description": c_act.get("description", f"Triggered by outcome rule: {rule.name}"),
                        "assigned_role": actions.get("assign_to", {}).get("role", "SERVICE_MANAGER"),
                    }

                # 3. Action: notify
                if "notify" in actions:
                    n_act = actions["notify"]
                    resulting_notifications.append({
                        "channel": n_act.get("channel", "WHATSAPP"),
                        "recipient": n_act.get("recipient", "CUSTOMER"),
                        "template": n_act.get("template", "feedback_escalation"),
                    })

                # 4. Action: schedule_callback
                if "schedule_callback" in actions:
                    resulting_callback = actions["schedule_callback"]

        # If not dry_run, persist notifications to notification_logs
        if not dry_run and resulting_notifications:
            for n in resulting_notifications:
                await NotificationService.send_notification(
                    db=db,
                    tenant_id=tenant_id,
                    channel=n["channel"],
                    recipient=n.get("recipient", "customer@dealership.com"),
                    template=n.get("template"),
                    payload={"context": context, "matched_rules": matched_rules},
                )

        return {
            "matched_rules": matched_rules,
            "outcome_status": resulting_outcome,
            "complaint": resulting_complaint,
            "notifications": resulting_notifications,
            "callback": resulting_callback,
        }
