"""Tests for distributed Redis-based rate limiting."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from starlette.responses import Response

from xagent.api.distributed_rate_limiting import (
    RedisRateLimiter,
    DistributedRateLimitMiddleware,
)
from xagent.security.auth import User, UserRole


class TestRedisRateLimiter:
    """Test RedisRateLimiter class."""

    @pytest.fixture
    async def limiter(self):
        """Create rate limiter for testing."""
        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379/0",
            default_rate=10,
            default_burst=10,
            window_seconds=60,
        )
        # Mock Redis client
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        limiter._client = mock_client
        limiter._connected = True
        return limiter

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379/0",
            default_rate=50,
            default_burst=60,
            window_seconds=30,
        )

        assert limiter.default_rate == 50
        assert limiter.default_burst == 60
        assert limiter.window_seconds == 30

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful Redis connection."""
        limiter = RedisRateLimiter(redis_url="redis://localhost:6379/0")

        with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_from_url.return_value = mock_client

            await limiter.connect()

            assert limiter._connected is True
            assert limiter._client is not None

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test Redis connection failure."""
        limiter = RedisRateLimiter(redis_url="redis://localhost:6379/0")

        with patch("redis.asyncio.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                await limiter.connect()

            assert limiter._connected is False

    @pytest.mark.asyncio
    async def test_disconnect(self, limiter):
        """Test Redis disconnection."""
        await limiter.disconnect()

        assert limiter._connected is False
        limiter._client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_rate_limit_allows_request(self, limiter):
        """Test that request is allowed when limit not exceeded."""
        # Mock Lua script execution - allowed=1, remaining=9, reset=now+60
        now = time.time()
        limiter._client.eval = AsyncMock(return_value=[1, 9, int(now + 60)])

        allowed, headers = await limiter.check_rate_limit("test-key")

        assert allowed is True
        assert headers["X-RateLimit-Limit"] == 10
        assert headers["X-RateLimit-Remaining"] == 9

    @pytest.mark.asyncio
    async def test_check_rate_limit_blocks_request(self, limiter):
        """Test that request is blocked when limit exceeded."""
        # Mock Lua script execution - allowed=0, remaining=0, reset=now+60
        now = time.time()
        limiter._client.eval = AsyncMock(return_value=[0, 0, int(now + 60)])

        allowed, headers = await limiter.check_rate_limit("test-key")

        assert allowed is False
        assert headers["X-RateLimit-Remaining"] == 0

    @pytest.mark.asyncio
    async def test_check_rate_limit_when_disconnected(self):
        """Test rate limiting when Redis is disconnected."""
        limiter = RedisRateLimiter(redis_url="redis://localhost:6379/0")
        limiter._connected = False

        allowed, headers = await limiter.check_rate_limit("test-key")

        # Should allow request when Redis is down
        assert allowed is True
        assert "X-RateLimit-Limit" in headers

    @pytest.mark.asyncio
    async def test_check_rate_limit_with_custom_limits(self, limiter):
        """Test rate limiting with custom limit and burst values."""
        now = time.time()
        limiter._client.eval = AsyncMock(return_value=[1, 24, int(now + 60)])

        allowed, headers = await limiter.check_rate_limit(
            "test-key",
            limit=25,
            burst=30,
        )

        assert allowed is True
        assert headers["X-RateLimit-Limit"] == 25

    @pytest.mark.asyncio
    async def test_check_rate_limit_with_cost(self, limiter):
        """Test rate limiting with custom cost."""
        now = time.time()
        limiter._client.eval = AsyncMock(return_value=[1, 7, int(now + 60)])

        allowed, headers = await limiter.check_rate_limit("test-key", cost=3.0)

        assert allowed is True

    @pytest.mark.asyncio
    async def test_check_rate_limit_handles_errors(self, limiter):
        """Test that errors in rate limiting are handled gracefully."""
        limiter._client.eval = AsyncMock(side_effect=Exception("Redis error"))

        allowed, headers = await limiter.check_rate_limit("test-key")

        # Should allow request on error
        assert allowed is True
        assert "X-RateLimit-Limit" in headers

    @pytest.mark.asyncio
    async def test_get_rate_limit_for_role_anonymous(self, limiter):
        """Test rate limit for anonymous users."""
        rate, burst = limiter.get_rate_limit_for_role("anonymous")

        assert rate == 60
        assert burst == 70

    @pytest.mark.asyncio
    async def test_get_rate_limit_for_role_user(self, limiter):
        """Test rate limit for authenticated users."""
        rate, burst = limiter.get_rate_limit_for_role("user")

        assert rate == 100
        assert burst == 120

    @pytest.mark.asyncio
    async def test_get_rate_limit_for_role_admin(self, limiter):
        """Test rate limit for admin users."""
        rate, burst = limiter.get_rate_limit_for_role("admin")

        assert rate == 1000
        assert burst == 1200

    @pytest.mark.asyncio
    async def test_get_rate_limit_for_role_unknown(self, limiter):
        """Test rate limit for unknown role falls back to default."""
        rate, burst = limiter.get_rate_limit_for_role("unknown")

        assert rate == limiter.default_rate
        assert burst == limiter.default_burst

    @pytest.mark.asyncio
    async def test_get_user_stats(self, limiter):
        """Test getting user rate limit stats."""
        limiter._client.hgetall = AsyncMock(
            return_value={"tokens": "5.0", "last_update": "1234567890.0"}
        )

        stats = await limiter.get_user_stats("test-key")

        assert stats is not None
        assert stats["tokens"] == 5.0
        assert stats["last_update"] == 1234567890.0

    @pytest.mark.asyncio
    async def test_get_user_stats_not_found(self, limiter):
        """Test getting stats for non-existent user."""
        limiter._client.hgetall = AsyncMock(return_value={})

        stats = await limiter.get_user_stats("test-key")

        assert stats is None

    @pytest.mark.asyncio
    async def test_get_user_stats_when_disconnected(self):
        """Test getting stats when Redis is disconnected."""
        limiter = RedisRateLimiter(redis_url="redis://localhost:6379/0")
        limiter._connected = False

        stats = await limiter.get_user_stats("test-key")

        assert stats is None

    @pytest.mark.asyncio
    async def test_reset_user_limit(self, limiter):
        """Test resetting user rate limit."""
        limiter._client.delete = AsyncMock(return_value=1)

        result = await limiter.reset_user_limit("test-key")

        assert result is True
        limiter._client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_user_limit_when_disconnected(self):
        """Test resetting limit when Redis is disconnected."""
        limiter = RedisRateLimiter(redis_url="redis://localhost:6379/0")
        limiter._connected = False

        result = await limiter.reset_user_limit("test-key")

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self, limiter):
        """Test cleanup method (Redis auto-expires, so returns 0)."""
        removed = await limiter.cleanup_old_entries()

        assert removed == 0

    @pytest.mark.asyncio
    async def test_make_key(self, limiter):
        """Test Redis key generation."""
        key = limiter._make_key("test-identifier")

        assert key == "xagent:ratelimit:test-identifier"


class TestDistributedRateLimitMiddleware:
    """Test DistributedRateLimitMiddleware class."""

    @pytest.fixture
    async def rate_limiter(self):
        """Create rate limiter for testing."""
        limiter = RedisRateLimiter(
            redis_url="redis://localhost:6379/0",
            default_rate=10,
            default_burst=10,
        )
        mock_client = AsyncMock()
        limiter._client = mock_client
        limiter._connected = True
        return limiter

    @pytest.fixture
    def middleware(self, rate_limiter):
        """Create middleware for testing."""
        app = MagicMock()
        return DistributedRateLimitMiddleware(app, rate_limiter)

    def test_get_client_identifier_from_user(self, middleware):
        """Test client identifier extraction from authenticated user."""
        request = MagicMock(spec=Request)
        user = User(username="testuser", role=UserRole.USER, scopes=["agent:read"])
        request.state.user = user

        identifier = middleware._get_client_identifier(request)

        assert identifier == "user:testuser"

    def test_get_client_identifier_from_ip(self, middleware):
        """Test client identifier extraction from IP address."""
        request = MagicMock(spec=Request)
        request.state.user = None
        request.client.host = "192.168.1.100"
        request.headers.get.return_value = None

        identifier = middleware._get_client_identifier(request)

        assert identifier == "ip:192.168.1.100"

    def test_get_client_identifier_from_forwarded_for(self, middleware):
        """Test client identifier from X-Forwarded-For header."""
        request = MagicMock(spec=Request)
        request.state.user = None
        request.headers.get.return_value = "203.0.113.1, 198.51.100.1"

        identifier = middleware._get_client_identifier(request)

        assert identifier == "ip:203.0.113.1"

    def test_get_user_role_authenticated(self, middleware):
        """Test role extraction for authenticated user."""
        request = MagicMock(spec=Request)
        user = User(username="admin", role=UserRole.ADMIN, scopes=["admin"])
        request.state.user = user

        role = middleware._get_user_role(request)

        assert role == "admin"

    def test_get_user_role_anonymous(self, middleware):
        """Test role extraction for anonymous user."""
        request = MagicMock(spec=Request)
        request.state.user = None

        role = middleware._get_user_role(request)

        assert role == "anonymous"

    @pytest.mark.asyncio
    async def test_dispatch_skips_health_checks(self, middleware):
        """Test that health check endpoints skip rate limiting."""
        request = MagicMock(spec=Request)
        request.url.path = "/health"

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert "X-RateLimit-Limit" not in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_applies_rate_limit(self, middleware, rate_limiter):
        """Test that rate limiting is applied to regular endpoints."""
        request = MagicMock(spec=Request)
        request.url.path = "/goals"
        request.state.user = None
        request.client.host = "192.168.1.100"
        request.headers.get.return_value = None

        # Mock rate limiter to allow request
        now = time.time()
        rate_limiter._client.eval = AsyncMock(return_value=[1, 59, int(now + 60)])

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_blocks_on_rate_limit(self, middleware, rate_limiter):
        """Test that requests are blocked when rate limit is exceeded."""
        request = MagicMock(spec=Request)
        request.url.path = "/goals"
        request.state.user = None
        request.client.host = "192.168.1.100"
        request.headers.get.return_value = None

        # Mock rate limiter to block request
        now = time.time()
        rate_limiter._client.eval = AsyncMock(return_value=[0, 0, int(now + 60)])

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 429
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_different_roles_different_limits(
        self, middleware, rate_limiter
    ):
        """Test that different user roles have different rate limits."""
        # Admin user
        admin_request = MagicMock(spec=Request)
        admin_request.url.path = "/goals"
        admin_user = User(username="admin", role=UserRole.ADMIN, scopes=["admin"])
        admin_request.state.user = admin_user

        # Regular user
        user_request = MagicMock(spec=Request)
        user_request.url.path = "/goals"
        regular_user = User(username="user", role=UserRole.USER, scopes=["agent:read"])
        user_request.state.user = regular_user

        # Mock rate limiter responses
        now = time.time()
        rate_limiter._client.eval = AsyncMock(return_value=[1, 999, int(now + 60)])

        async def call_next(req):
            return Response(content="OK", status_code=200)

        # Get rate limits
        admin_response = await middleware.dispatch(admin_request, call_next)
        
        rate_limiter._client.eval = AsyncMock(return_value=[1, 99, int(now + 60)])
        user_response = await middleware.dispatch(user_request, call_next)

        admin_limit = int(admin_response.headers["X-RateLimit-Limit"])
        user_limit = int(user_response.headers["X-RateLimit-Limit"])

        # Admin should have higher limit
        assert admin_limit > user_limit
        assert admin_limit == 1000
        assert user_limit == 100


@pytest.mark.asyncio
async def test_get_distributed_rate_limiter():
    """Test getting global distributed rate limiter instance."""
    from xagent.api.distributed_rate_limiting import get_distributed_rate_limiter

    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_from_url.return_value = mock_client

        limiter = await get_distributed_rate_limiter("redis://localhost:6379/0")

        assert limiter is not None
        assert limiter._connected is True
