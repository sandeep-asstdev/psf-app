"""
================================================================================
FILE PURPOSE: Notification Service.
Sends notifications via channel (WhatsApp, SMS, Email).
Currently backed by a stub provider that records all dispatched messages in `notification_logs`.
================================================================================
"""
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.additional import NotificationLog

logger = logging.getLogger("psf.notification_service")


class NotificationService:
    @staticmethod
    async def send_notification(
        db: AsyncSession,
        tenant_id: uuid.UUID,
        channel: str,
        recipient: str,
        template: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> NotificationLog:
        """
        Dispatches a notification via stub provider and logs to notification_logs.
        """
        log = NotificationLog(
            tenant_id=tenant_id,
            channel=channel.upper().strip(),
            recipient=recipient.strip(),
            template=template,
            payload=payload,
            status="SENT",
        )
        db.add(log)
        await db.flush()
        logger.info(f"Stub notification dispatched via {channel} to {recipient} (template: {template})")
        return log

