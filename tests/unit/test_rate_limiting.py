"""Tests for rate limiting functionality."""

import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from starlette.responses import Response

from xagent.api.rate_limiting import RateLimiter, RateLimitMiddleware
from xagent.security.auth import User, UserRole


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(
            default_rate=50,
            default_burst=60,
            window_seconds=30,
        )

        assert limiter.default_rate == 50
        assert limiter.default_burst == 60
        assert limiter.window_seconds == 30

    def test_check_rate_limit_allows_first_request(self):
        """Test that first request is allowed."""
        limiter = RateLimiter(default_rate=10, default_burst=10)

        allowed, headers = limiter.check_rate_limit("test-key")

        assert allowed is True
        assert headers["X-RateLimit-Limit"] == 10
        assert headers["X-RateLimit-Remaining"] == 9

    def test_check_rate_limit_blocks_after_burst(self):
        """Test that requests are blocked after burst is exceeded."""
        limiter = RateLimiter(default_rate=10, default_burst=5)

        # Use up all tokens
        for _ in range(5):
            allowed, _ = limiter.check_rate_limit("test-key")
            assert allowed is True

        # Next request should be blocked
        allowed, headers = limiter.check_rate_limit("test-key")
        assert allowed is False
        assert headers["X-RateLimit-Remaining"] == 0

    def test_check_rate_limit_replenishes_tokens(self):
        """Test that tokens are replenished over time."""
        limiter = RateLimiter(default_rate=60, default_burst=5, window_seconds=60)

        # Use up all tokens
        for _ in range(5):
            limiter.check_rate_limit("test-key")

        # Should be blocked now
        allowed, _ = limiter.check_rate_limit("test-key")
        assert allowed is False

        # Wait for tokens to replenish (1 second = 1 token at 60/min)
        time.sleep(2)

        # Should allow requests again
        allowed, headers = limiter.check_rate_limit("test-key")
        assert allowed is True
        assert headers["X-RateLimit-Remaining"] >= 1

    def test_check_rate_limit_different_keys(self):
        """Test that different keys have independent limits."""
        limiter = RateLimiter(default_rate=10, default_burst=2)

        # Use up tokens for key1
        for _ in range(2):
            limiter.check_rate_limit("key1")

        # key1 should be blocked
        allowed, _ = limiter.check_rate_limit("key1")
        assert allowed is False

        # key2 should still be allowed
        allowed, _ = limiter.check_rate_limit("key2")
        assert allowed is True

    def test_get_rate_limit_for_role_anonymous(self):
        """Test rate limit for anonymous users."""
        limiter = RateLimiter()
        rate, burst = limiter.get_rate_limit_for_role("anonymous")

        assert rate == 60
        assert burst == 70

    def test_get_rate_limit_for_role_user(self):
        """Test rate limit for authenticated users."""
        limiter = RateLimiter()
        rate, burst = limiter.get_rate_limit_for_role("user")

        assert rate == 100
        assert burst == 120

    def test_get_rate_limit_for_role_admin(self):
        """Test rate limit for admin users."""
        limiter = RateLimiter()
        rate, burst = limiter.get_rate_limit_for_role("admin")

        assert rate == 1000
        assert burst == 1200

    def test_cleanup_old_entries(self):
        """Test cleanup of old rate limit entries."""
        limiter = RateLimiter()

        # Create some entries
        limiter.check_rate_limit("key1")
        limiter.check_rate_limit("key2")
        limiter.check_rate_limit("key3")

        # Manually age them
        now = time.time()
        limiter._buckets["key1"] = (5.0, now - 7200)  # 2 hours old
        limiter._buckets["key2"] = (5.0, now - 3700)  # Just over 1 hour
        limiter._buckets["key3"] = (5.0, now - 100)  # Recent

        # Clean up entries older than 1 hour
        removed = limiter.cleanup_old_entries(max_age_seconds=3600)

        assert removed == 2
        assert "key1" not in limiter._buckets
        assert "key2" not in limiter._buckets
        assert "key3" in limiter._buckets


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter for testing."""
        return RateLimiter(default_rate=10, default_burst=10)

    @pytest.fixture
    def middleware(self, rate_limiter):
        """Create middleware for testing."""
        app = MagicMock()
        return RateLimitMiddleware(app, rate_limiter)

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
    async def test_dispatch_applies_rate_limit(self, middleware):
        """Test that rate limiting is applied to regular endpoints."""
        request = MagicMock(spec=Request)
        request.url.path = "/goals"
        request.state.user = None
        request.client.host = "192.168.1.100"
        request.headers.get.return_value = None

        async def call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_blocks_on_rate_limit(self):
        """Test that requests are blocked when rate limit is exceeded."""
        # Create a rate limiter with low limits for testing
        limiter = RateLimiter(default_rate=10, default_burst=5)
        # Override rate limits for anonymous to use the default
        limiter.rate_limits["anonymous"] = (10, 5)

        app = MagicMock()
        test_middleware = RateLimitMiddleware(app, limiter)

        request = MagicMock(spec=Request)
        request.url.path = "/goals"
        request.state.user = None
        request.client.host = "192.168.1.100"
        request.headers.get.return_value = None

        async def call_next(req):
            return Response(content="OK", status_code=200)

        # Use up all tokens (5 burst limit)
        for _ in range(5):
            response = await test_middleware.dispatch(request, call_next)
            assert response.status_code == 200

        # Next request should be blocked
        response = await test_middleware.dispatch(request, call_next)

        assert response.status_code == 429
        assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_different_roles_different_limits(self, middleware):
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

        async def call_next(req):
            return Response(content="OK", status_code=200)

        # Get rate limits
        admin_response = await middleware.dispatch(admin_request, call_next)
        user_response = await middleware.dispatch(user_request, call_next)

        admin_limit = int(admin_response.headers["X-RateLimit-Limit"])
        user_limit = int(user_response.headers["X-RateLimit-Limit"])

        # Admin should have higher limit
        assert admin_limit > user_limit
