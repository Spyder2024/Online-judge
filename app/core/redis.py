import json
from typing import Any, Optional
import redis.asyncio as redis
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

# Global async connection pool instance initialized during lifespan
redis_pool: Optional[ConnectionPool] = None
redis_client: Optional[Redis] = None


async def init_redis_pool() -> Redis:
    """
    Initialize the Redis async connection pool during application lifespan startup.
    """
    global redis_pool, redis_client
    redis_pool = redis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_POOL_SIZE,
        decode_responses=True,
    )
    redis_client = redis.Redis(connection_pool=redis_pool)
    return redis_client


async def close_redis_pool() -> None:
    """
    Close and disconnect the Redis connection pool during application shutdown.
    """
    global redis_client, redis_pool
    if redis_client is not None:
        await redis_client.aclose()
    if redis_pool is not None:
        await redis_pool.disconnect()


async def get_redis() -> Redis:
    """
    FastAPI dependency yielding the async Redis connection client backed by the pool.
    """
    if redis_client is None:
        raise RuntimeError("Redis client is not initialized. Check lifespan configuration.")
    return redis_client


async def set_cache(key: str, value: Any, expire_seconds: int = 3600) -> bool:
    """
    Set an item in Redis cache with automatic JSON serialization and TTL expiration.
    """
    client = await get_redis()
    serialized = json.dumps(value) if not isinstance(value, str) else value
    return await client.set(key, serialized, ex=expire_seconds)


async def get_cache(key: str) -> Optional[Any]:
    """
    Retrieve an item from Redis cache by key and deserialize from JSON if applicable.
    """
    client = await get_redis()
    data = await client.get(key)
    if data is None:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data


async def delete_cache(key: str) -> int:
    """
    Delete a key or pattern from Redis cache.
    """
    client = await get_redis()
    return await client.delete(key)
