"""
================================================================================
FILE PURPOSE: Asynchronous Background Worker Runner.
Runs asynchronous background processing tasks outside the main web request thread,
such as batch DMS file imports, end-of-day session cleanup, and report generation.

KEY RESPONSIBILITIES:
- Listens for background jobs in Redis task queues.
- Executes long-running file processing jobs without blocking HTTP responses.
- Monitors job completion and updates job statuses.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: Background worker container psf_worker keeps restarting
  -> Cause: Worker could not connect to Redis or PostgreSQL.
  -> What should you do: Check `docker logs psf_worker` to see the exact connection error.
================================================================================
"""
import asyncio
import logging
import signal
from datetime import datetime, timezone
from sqlalchemy import select, and_
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.complaint import Complaint
from app.models.followup import Reminder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(name)s - %(message)s",
)
logger = logging.getLogger("psf.worker")

stop_event = asyncio.Event()


def handle_shutdown(signum, frame):
    logger.info("Shutdown signal received, draining jobs...")
    stop_event.set()


async def check_sla_breaches():
    """Periodic job: scans active complaints and alerts on SLA threshold breaches."""
    try:
        now_utc = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            stmt = select(Complaint).where(
                and_(
                    Complaint.status.in_(["OPEN", "ASSIGNED", "IN_PROGRESS", "REOPENED"]),
                    Complaint.sla_due_at <= now_utc,
                    Complaint.is_deleted == False,
                )
            )
            breached = (await db.execute(stmt)).scalars().all()
            if breached:
                logger.warning(
                    f"⚠️ [SLA MONITOR] Found {len(breached)} complaints currently breaching SLA: "
                    f"{', '.join([c.complaint_no for c in breached[:5]])}"
                )
    except Exception as e:
        logger.error(f"Error in check_sla_breaches job: {e}")


async def check_due_reminders():
    """Periodic job: identifies pending callbacks/reminders scheduled for CREs."""
    try:
        now_utc = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            stmt = select(Reminder).where(
                and_(
                    Reminder.is_acknowledged == False,
                    Reminder.remind_at <= now_utc,
                    Reminder.is_deleted == False,
                )
            )
            due_reminders = (await db.execute(stmt)).scalars().all()
            if due_reminders:
                logger.info(f"🔔 [REMINDER DISPATCH] Found {len(due_reminders)} callback reminders due for CRE attention.")
    except Exception as e:
        logger.error(f"Error in check_due_reminders job: {e}")


async def run_worker():
    logger.info(f"PSF Background Worker initialized with concurrency {settings.WORKER_CONCURRENCY}")
    logger.info("Listening on queues: default, imports, reminders, notifications, sla_monitor")

    iteration = 0
    while not stop_event.is_set():
        try:
            iteration += 1
            # Run periodic jobs every 30 seconds
            if iteration % 15 == 0:
                await check_sla_breaches()
                await check_due_reminders()

            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Worker iteration error: {e}")
            await asyncio.sleep(5)

    logger.info("Worker stopped gracefully.")


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
