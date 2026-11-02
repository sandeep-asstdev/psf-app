import asyncio
import logging
import signal
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(name)s - %(message)s",
)
logger = logging.getLogger("psf.worker")

stop_event = asyncio.Event()


def handle_shutdown(signum, frame):
    logger.info("Shutdown signal received, draining jobs...")
    stop_event.set()


async def run_worker():
    logger.info(f"PSF Background Worker initialized with concurrency {settings.WORKER_CONCURRENCY}")
    logger.info("Listening on queues: default, imports, reminders, notifications")

    # In production/Phase 4+, ARQ or Celery handles Redis-based streaming queues
    while not stop_event.is_set():
        try:
            # Poll or wait for background tasks
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break

    logger.info("Worker stopped gracefully.")


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
