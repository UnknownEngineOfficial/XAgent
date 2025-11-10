"""Distributed Redis-based rate limiting for X-Agent API.

This module provides a distributed rate limiting implementation using Redis,
allowing rate limits to be enforced across multiple server instances.
"""

import time
from collections.abc import Callable
from typing import Any, cast

import redis.asyncio as redis
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class RedisRateLimiter:
    """
    Distributed token bucket rate limiter using Redis.

    This implementation uses Redis atomic operations to ensure rate limiting
    works correctly across multiple server instances.
    """

    def __init__(
        self,
        redis_url: str,
        default_rate: int = 100,
        default_burst: int = 120,
        window_seconds: int = 60,
        key_prefix: str = "xagent:ratelimit",
    ):
        """
        Initialize distributed rate limiter.

        Args:
            redis_url: Redis connection URL
            default_rate: Default number of requests allowed per window
            default_burst: Maximum burst size (tokens in bucket)
            window_seconds: Time window in seconds
            key_prefix: Prefix for Redis keys
        """
        self.redis_url = redis_url
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._client: redis.Redis | None = None
        self._connected = False

        # Rate limits per role/scope
        self.rate_limits = {
            "anonymous": (60, 70),  # 60 req/min, burst 70
            "user": (100, 120),  # 100 req/min, burst 120
            "admin": (1000, 1200),  # 1000 req/min, burst 1200
        }

        # Lua script for atomic rate limiting
        # This ensures thread-safety and works across multiple servers
        self._lua_script = """
        local key = KEYS[1]
        local limit = tonumber(ARGV[1])
        local burst = tonumber(ARGV[2])
        local window = tonumber(ARGV[3])
        local cost = tonumber(ARGV[4])
        local now = tonumber(ARGV[5])
        
        -- Get current bucket state
        local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
        local tokens = tonumber(bucket[1])
        local last_update = tonumber(bucket[2])
        
        -- Initialize if not exists
        if not tokens then
            tokens = burst
            last_update = now
        end
        
        -- Calculate tokens to add based on time elapsed
        local time_elapsed = now - last_update
        local tokens_to_add = (time_elapsed / window) * limit
        tokens = math.min(burst, tokens + tokens_to_add)
        
        -- Check if we have enough tokens
        local allowed = 0
        if tokens >= cost then
            tokens = tokens - cost
            allowed = 1
        end
        
        -- Update bucket state
        redis.call('HMSET', key, 'tokens', tostring(tokens), 'last_update', tostring(now))
        redis.call('EXPIRE', key, window * 2)
        
        -- Return result
        return {allowed, math.floor(tokens), last_update + window}
        """

    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis rate limiter connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect Redis rate limiter: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Redis rate limiter disconnected")

    def _make_key(self, identifier: str) -> str:
        """Create rate limit key for Redis."""
        return f"{self.key_prefix}:{identifier}"

    async def check_rate_limit(
        self,
        key: str,
        cost: float = 1.0,
        limit: int | None = None,
        burst: int | None = None,
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if request is within rate limit using Redis.

        Args:
            key: Rate limit key
            cost: Cost of this request in tokens
            limit: Custom rate limit (uses default if None)
            burst: Custom burst size (uses default if None)

        Returns:
            Tuple of (allowed, headers) where headers contains rate limit info
        """
        if not self._connected or self._client is None:
            logger.warning("Redis not connected, allowing request")
            # Fallback: allow request if Redis is down
            return (True, {
                "X-RateLimit-Limit": limit or self.default_rate,
                "X-RateLimit-Remaining": 0,
                "X-RateLimit-Reset": int(time.time() + self.window_seconds),
                "X-RateLimit-Window": self.window_seconds,
            })

        limit = limit or self.default_rate
        burst = burst or self.default_burst
        redis_key = self._make_key(key)
        now = time.time()

        try:
            # Execute Lua script atomically
            result = await self._client.eval(
                self._lua_script,
                1,  # number of keys
                redis_key,
                str(limit),
                str(burst),
                str(self.window_seconds),
                str(cost),
                str(now),
            )

            allowed = bool(result[0])
            remaining = int(result[1])
            reset_time = int(result[2])

            headers = {
                "X-RateLimit-Limit": limit,
                "X-RateLimit-Remaining": max(0, remaining),
                "X-RateLimit-Reset": reset_time,
                "X-RateLimit-Window": self.window_seconds,
            }

            return (allowed, headers)

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fallback: allow request on error
            return (True, {
                "X-RateLimit-Limit": limit,
                "X-RateLimit-Remaining": 0,
                "X-RateLimit-Reset": int(time.time() + self.window_seconds),
                "X-RateLimit-Window": self.window_seconds,
            })

    def get_rate_limit_for_role(self, role: str) -> tuple[int, int]:
        """
        Get rate limit and burst for a role.

        Args:
            role: User role (anonymous, user, admin)

        Returns:
            Tuple of (rate_limit, burst_size)
        """
        return self.rate_limits.get(role, (self.default_rate, self.default_burst))

    async def get_user_stats(self, key: str) -> dict[str, Any] | None:
        """
        Get current rate limit stats for a user.

        Args:
            key: Rate limit key

        Returns:
            Dictionary with stats or None if not found
        """
        if not self._connected or self._client is None:
            return None

        try:
            redis_key = self._make_key(key)
            data = await self._client.hgetall(redis_key)

            if not data:
                return None

            return {
                "tokens": float(data.get("tokens", 0)),
                "last_update": float(data.get("last_update", 0)),
            }
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return None

    async def reset_user_limit(self, key: str) -> bool:
        """
        Reset rate limit for a user.

        Args:
            key: Rate limit key

        Returns:
            True if successful, False otherwise
        """
        if not self._connected or self._client is None:
            return False

        try:
            redis_key = self._make_key(key)
            await self._client.delete(redis_key)
            logger.info(f"Reset rate limit for {key}")
            return True
        except Exception as e:
            logger.error(f"Error resetting user limit: {e}")
            return False

    async def cleanup_old_entries(self) -> int:
        """
        Clean up expired entries.

        Note: Redis automatically handles expiration via EXPIRE command in the Lua script,
        so this is mostly a no-op but provided for API compatibility.

        Returns:
            Number of entries removed (always 0 as Redis auto-expires)
        """
        # Redis handles expiration automatically
        logger.debug("Cleanup called but Redis handles expiration automatically")
        return 0


class DistributedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Distributed rate limiting middleware for FastAPI using Redis.

    This middleware uses Redis to enforce rate limits across multiple
    server instances, ensuring consistent rate limiting in a distributed environment.
    """

    def __init__(self, app: Any, rate_limiter: RedisRateLimiter) -> None:
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            rate_limiter: RedisRateLimiter instance
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for client.

        Prefers authenticated user ID, falls back to IP address.

        Args:
            request: FastAPI request

        Returns:
            Client identifier string
        """
        # Try to get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        if user and hasattr(user, "username"):
            return f"user:{user.username}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP in list
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"

    def _get_user_role(self, request: Request) -> str:
        """
        Get user role from request.

        Args:
            request: FastAPI request

        Returns:
            User role (anonymous, user, admin)
        """
        user = getattr(request.state, "user", None)
        if user:
            if hasattr(user, "role"):
                role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
                return role_str.lower()
            return "user"
        return "anonymous"

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> Response:
        """
        Process request with distributed rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/healthz", "/ready", "/metrics"]:
            return cast(Response, await call_next(request))

        # Get client identifier and role
        client_id = self._get_client_identifier(request)
        user_role = self._get_user_role(request)

        # Get rate limit for role
        limit, burst = self.rate_limiter.get_rate_limit_for_role(user_role)

        # Check rate limit
        allowed, headers = await self.rate_limiter.check_rate_limit(
            key=client_id,
            cost=1.0,
            limit=limit,
            burst=burst,
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {client_id} (role: {user_role})",
                extra={
                    "client_id": client_id,
                    "role": user_role,
                    "path": request.url.path,
                },
            )

            # Return 429 Too Many Requests
            response = Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
            )

            # Add rate limit headers
            for header, value in headers.items():
                response.headers[header] = str(value)

            # Add Retry-After header
            retry_after = headers["X-RateLimit-Reset"] - int(time.time())
            response.headers["Retry-After"] = str(max(0, retry_after))

            return response

        # Process request
        response = cast(Response, await call_next(request))

        # Add rate limit headers to successful response
        for header, value in headers.items():
            response.headers[header] = str(value)

        return response


# Global distributed rate limiter instance
_distributed_rate_limiter: RedisRateLimiter | None = None


async def get_distributed_rate_limiter(redis_url: str) -> RedisRateLimiter:
    """
    Get global distributed rate limiter instance.

    Args:
        redis_url: Redis connection URL

    Returns:
        RedisRateLimiter instance
    """
    global _distributed_rate_limiter
    if _distributed_rate_limiter is None:
        _distributed_rate_limiter = RedisRateLimiter(redis_url)
        await _distributed_rate_limiter.connect()
    return _distributed_rate_limiter
