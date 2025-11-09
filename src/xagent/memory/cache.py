"""
Redis-based caching layer for X-Agent memory optimization.

This module provides a high-performance caching layer using Redis to reduce
database queries and improve response times for frequently accessed data.
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheConfig:
    """Configuration for cache behavior."""

    # Default TTL values (in seconds)
    DEFAULT_TTL = 300  # 5 minutes
    SHORT_TTL = 60  # 1 minute
    MEDIUM_TTL = 600  # 10 minutes
    LONG_TTL = 3600  # 1 hour

    # Cache key prefixes
    PREFIX_GOAL = "goal"
    PREFIX_AGENT_STATE = "agent_state"
    PREFIX_MEMORY = "memory"
    PREFIX_METRIC = "metric"
    PREFIX_PLAN = "plan"
    PREFIX_TOOL_RESULT = "tool_result"


class RedisCache:
    """
    Redis-based cache implementation with async support.

    Features:
    - Async operations for high performance
    - Automatic serialization/deserialization
    - Configurable TTL per key type
    - Cache invalidation support
    - Bulk operations
    - Pattern-based deletion
    """

    def __init__(self, redis_url: str, key_prefix: str = "xagent"):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            key_prefix: Global prefix for all cache keys
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self._client: redis.Redis | None = None
        self._connected = False

    async def connect(self):
        """Establish Redis connection."""
        try:
            self._client = await redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True, max_connections=50
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis cache: {e}")
            self._connected = False
            raise

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Redis cache disconnected")

    def _make_key(self, category: str, key: str) -> str:
        """Create a namespaced cache key."""
        return f"{self.key_prefix}:{category}:{key}"

    def _serialize(self, value: Any) -> str | None:
        """Serialize value to JSON string."""
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize value: {e}")
            return None

    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize value: {e}")
            return None

    async def get(self, category: str, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            category: Cache category (e.g., 'goal', 'agent_state')
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._connected:
            logger.warning("Cache not connected, skipping get")
            return None

        try:
            cache_key = self._make_key(category, key)
            value = await self._client.get(cache_key)

            if value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return self._deserialize(value)

            logger.debug(f"Cache miss: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(
        self, category: str, key: str, value: Any, ttl: int = CacheConfig.DEFAULT_TTL
    ) -> bool:
        """
        Set value in cache.

        Args:
            category: Cache category
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            logger.warning("Cache not connected, skipping set")
            return False

        try:
            cache_key = self._make_key(category, key)
            serialized = self._serialize(value)

            if serialized is None:
                return False

            await self._client.setex(cache_key, ttl, serialized)

            logger.debug(f"Cache set: {cache_key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, category: str, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            category: Cache category
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            logger.warning("Cache not connected, skipping delete")
            return False

        try:
            cache_key = self._make_key(category, key)
            result = await self._client.delete(cache_key)
            logger.debug(f"Cache delete: {cache_key}")
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, category: str, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            category: Cache category
            pattern: Key pattern (e.g., 'user:*')

        Returns:
            Number of keys deleted
        """
        if not self._connected:
            logger.warning("Cache not connected, skipping delete_pattern")
            return 0

        try:
            search_pattern = self._make_key(category, pattern)
            keys = []

            # Use SCAN to avoid blocking Redis
            cursor = 0
            while True:
                cursor, batch = await self._client.scan(cursor, match=search_pattern, count=100)
                keys.extend(batch)
                if cursor == 0:
                    break

            if keys:
                deleted = await self._client.delete(*keys)
                logger.debug(f"Cache delete pattern: {search_pattern} ({deleted} keys)")
                return deleted

            return 0
        except Exception as e:
            logger.error(f"Cache delete_pattern error: {e}")
            return 0

    async def exists(self, category: str, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            category: Cache category
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        if not self._connected:
            return False

        try:
            cache_key = self._make_key(category, key)
            result = await self._client.exists(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False

    async def expire(self, category: str, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            category: Cache category
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._connected:
            return False

        try:
            cache_key = self._make_key(category, key)
            result = await self._client.expire(cache_key, ttl)
            return result
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False

    async def get_many(self, category: str, keys: list[str]) -> dict[str, Any]:
        """
        Get multiple values from cache.

        Args:
            category: Cache category
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs
        """
        if not self._connected or not keys:
            return {}

        try:
            cache_keys = [self._make_key(category, k) for k in keys]
            values = await self._client.mget(cache_keys)

            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)

            logger.debug(f"Cache get_many: {len(result)}/{len(keys)} hits")
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}

    async def set_many(
        self, category: str, items: dict[str, Any], ttl: int = CacheConfig.DEFAULT_TTL
    ) -> bool:
        """
        Set multiple values in cache.

        Args:
            category: Cache category
            items: Dictionary of key-value pairs
            ttl: Time-to-live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._connected or not items:
            return False

        try:
            # Use pipeline for atomic operations
            pipe = self._client.pipeline()

            for key, value in items.items():
                cache_key = self._make_key(category, key)
                serialized = self._serialize(value)
                pipe.setex(cache_key, ttl, serialized)

            await pipe.execute()
            logger.debug(f"Cache set_many: {len(items)} items")
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False

    async def increment(self, category: str, key: str, amount: int = 1) -> int | None:
        """
        Increment a numeric value in cache.

        Args:
            category: Cache category
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment, or None on error
        """
        if not self._connected:
            return None

        try:
            cache_key = self._make_key(category, key)
            result = await self._client.incrby(cache_key, amount)
            return result
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return None

    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary of cache statistics
        """
        if not self._connected:
            return {"connected": False}

        try:
            info = await self._client.info("stats")
            return {
                "connected": True,
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"connected": True, "error": str(e)}

    def _calculate_hit_rate(self, info: dict) -> float:
        """Calculate cache hit rate."""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return round((hits / total) * 100, 2)


def cache_key_from_args(*args, **kwargs) -> str:
    """
    Generate cache key from function arguments.

    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Hash-based cache key
    """
    key_data = f"{args}:{sorted(kwargs.items())}"
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(category: str, ttl: int = CacheConfig.DEFAULT_TTL, key_func=None):
    """
    Decorator to cache function results.

    Args:
        category: Cache category
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key from args

    Example:
        @cached(category="goal", ttl=300)
        async def get_goal(goal_id: str):
            return await db.query(Goal).filter_by(id=goal_id).first()
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get cache instance
            cache = getattr(self, "_cache", None)
            if not cache or not cache._connected:
                # No cache available, call function directly
                return await func(self, *args, **kwargs)

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_key_from_args(*args, **kwargs)

            # Try to get from cache
            cached_value = await cache.get(category, cache_key)
            if cached_value is not None:
                return cached_value

            # Cache miss - call function
            result = await func(self, *args, **kwargs)

            # Store in cache
            await cache.set(category, cache_key, result, ttl)

            return result

        return wrapper

    return decorator
