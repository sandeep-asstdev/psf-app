import logging
from typing import Optional
from prisma import Prisma

logger = logging.getLogger("psf.database")

# Global Prisma Client instance
db: Prisma = Prisma(auto_register=True)


async def connect_db() -> None:
    """Connect Prisma client to PostgreSQL database."""
    try:
        if not db.is_connected():
            await db.connect()
            logger.info("Connected successfully to PostgreSQL database via Prisma.")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL database: {e}")
        # In early development or build phase, we allow graceful fallback
        pass


async def disconnect_db() -> None:
    """Disconnect Prisma client."""
    try:
        if db.is_connected():
            await db.disconnect()
            logger.info("Disconnected from PostgreSQL database.")
    except Exception as e:
        logger.error(f"Error disconnecting from database: {e}")
