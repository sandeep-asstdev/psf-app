"""
================================================================================
FILE PURPOSE: Redis In-Memory Cache & Pub/Sub Connection Pool.
This file provides an asynchronous Redis client connection used for distributed locking
(preventing duplicate file imports), real-time WebSocket notifications, and transient caching.

KEY RESPONSIBILITIES:
- Manages Redis connection pool and async client lifecycle.
- Provides `get_redis()` helper function to get an active Redis client.
- Provides `close_redis()` helper called during app shutdown to clean up connections.

COMMON ERRORS & TROUBLESHOOTING GUIDE:
- Error: redis.exceptions.ConnectionError: Error connecting to redis:6379
  -> Cause: The Redis container (psf_redis) is down or port is blocked.
  -> What should you do: Run `docker ps` to verify psf_redis is running. Run `docker restart psf_redis` if needed. Check REDIS_URL in .env.
- Error: WebSocket notifications not reaching CREs
  -> Cause: Redis pub/sub channel communication failed.
  -> What should you do: Test Redis by running `docker exec psf_redis redis-cli ping`. Expected response is `PONG`.
================================================================================
"""
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

