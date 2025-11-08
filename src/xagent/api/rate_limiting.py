"""Rate limiting middleware for X-Agent API."""

import time
from collections import defaultdict
from typing import Callable, Dict, Tuple

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Implements a token bucket algorithm for rate limiting requests.
    """

    def __init__(
        self,
        default_rate: int = 100,
        default_burst: int = 120,
        window_seconds: int = 60,
    ):
        """
        Initialize rate limiter.
        
        Args:
            default_rate: Default number of requests allowed per window
            default_burst: Maximum burst size (tokens in bucket)
            window_seconds: Time window in seconds
        """
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.window_seconds = window_seconds
        
        # Storage: {key: (tokens, last_update_time)}
        self._buckets: Dict[str, Tuple[float, float]] = {}
        
        # Rate limits per role/scope
        self.rate_limits = {
            "anonymous": (60, 70),      # 60 req/min, burst 70
            "user": (100, 120),          # 100 req/min, burst 120
            "admin": (1000, 1200),       # 1000 req/min, burst 1200
        }

    def _get_tokens(self, key: str, limit: int, burst: int) -> Tuple[float, float]:
        """
        Get current tokens for a key.
        
        Args:
            key: Rate limit key (e.g., IP address or user ID)
            limit: Rate limit per window
            burst: Maximum burst size
        
        Returns:
            Tuple of (tokens, last_update_time)
        """
        now = time.time()
        
        if key not in self._buckets:
            # New bucket starts full
            self._buckets[key] = (float(burst), now)
            return (float(burst), now)
        
        tokens, last_update = self._buckets[key]
        
        # Calculate tokens to add based on time elapsed
        time_elapsed = now - last_update
        tokens_to_add = (time_elapsed / self.window_seconds) * limit
        
        # Add tokens but don't exceed burst limit
        tokens = min(burst, tokens + tokens_to_add)
        
        return (tokens, now)

    def check_rate_limit(
        self,
        key: str,
        cost: float = 1.0,
        limit: int | None = None,
        burst: int | None = None,
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if request is within rate limit.
        
        Args:
            key: Rate limit key
            cost: Cost of this request in tokens
            limit: Custom rate limit (uses default if None)
            burst: Custom burst size (uses default if None)
        
        Returns:
            Tuple of (allowed, headers) where headers contains rate limit info
        """
        limit = limit or self.default_rate
        burst = burst or self.default_burst
        
        tokens, last_update = self._get_tokens(key, limit, burst)
        
        # Check if we have enough tokens
        if tokens >= cost:
            # Consume tokens
            tokens -= cost
            self._buckets[key] = (tokens, time.time())
            allowed = True
        else:
            # Rate limit exceeded
            allowed = False
        
        # Calculate reset time
        reset_time = int(last_update + self.window_seconds)
        
        # Prepare headers
        headers = {
            "X-RateLimit-Limit": limit,
            "X-RateLimit-Remaining": int(max(0, tokens)),
            "X-RateLimit-Reset": reset_time,
            "X-RateLimit-Window": self.window_seconds,
        }
        
        return (allowed, headers)

    def get_rate_limit_for_role(self, role: str) -> Tuple[int, int]:
        """
        Get rate limit and burst for a role.
        
        Args:
            role: User role (anonymous, user, admin)
        
        Returns:
            Tuple of (rate_limit, burst_size)
        """
        return self.rate_limits.get(role, (self.default_rate, self.default_burst))

    def cleanup_old_entries(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old entries to prevent memory growth.
        
        Args:
            max_age_seconds: Maximum age of entries to keep
        
        Returns:
            Number of entries removed
        """
        now = time.time()
        keys_to_remove = []
        
        for key, (_, last_update) in self._buckets.items():
            if now - last_update > max_age_seconds:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._buckets[key]
        
        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} rate limit entries")
        
        return len(keys_to_remove)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Limits requests based on IP address and user authentication.
    """

    def __init__(self, app, rate_limiter: RateLimiter):
        """
        Initialize middleware.
        
        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
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

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
        
        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/healthz", "/ready", "/metrics"]:
            return await call_next(request)
        
        # Get client identifier and role
        client_id = self._get_client_identifier(request)
        user_role = self._get_user_role(request)
        
        # Get rate limit for role
        limit, burst = self.rate_limiter.get_rate_limit_for_role(user_role)
        
        # Check rate limit
        allowed, headers = self.rate_limiter.check_rate_limit(
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
                }
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
        response = await call_next(request)
        
        # Add rate limit headers to successful response
        for header, value in headers.items():
            response.headers[header] = str(value)
        
        return response


# Global rate limiter instance
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """
    Get global rate limiter instance.
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
