import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("psf.redis")

redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
    return redis_client


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        try:
            await redis_client.close()
            logger.info("Closed Redis connection.")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")
        finally:
            redis_client = None
