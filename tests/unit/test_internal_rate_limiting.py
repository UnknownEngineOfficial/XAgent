"""Tests for internal rate limiting functionality."""

import asyncio
import time

import pytest

from xagent.core.internal_rate_limiting import (
    InternalRateLimiter,
    RateLimitBucket,
    RateLimitConfig,
    configure_internal_rate_limiter,
    get_internal_rate_limiter,
)


class TestRateLimitBucket:
    """Test RateLimitBucket class."""

    def test_initialization(self):
        """Test bucket initialization."""
        bucket = RateLimitBucket(capacity=10, tokens=10.0, refill_rate=1.0)

        assert bucket.capacity == 10
        assert bucket.tokens == 10.0
        assert bucket.refill_rate == 1.0

    def test_consume_success(self):
        """Test successful token consumption."""
        bucket = RateLimitBucket(capacity=10, tokens=10.0, refill_rate=1.0)

        result = bucket.consume(5)

        assert result is True
        assert bucket.tokens == 5.0

    def test_consume_failure(self):
        """Test failed token consumption when insufficient tokens."""
        bucket = RateLimitBucket(capacity=10, tokens=3.0, refill_rate=1.0)

        result = bucket.consume(5)

        assert result is False
        # Allow small tolerance for floating point arithmetic
        assert bucket.tokens == pytest.approx(3.0, abs=0.001)

    def test_token_refill(self):
        """Test that tokens refill over time."""
        bucket = RateLimitBucket(capacity=10, tokens=5.0, refill_rate=10.0)  # 10 tokens/sec

        # Wait for 0.5 seconds (should add 5 tokens)
        time.sleep(0.5)

        available = bucket.available_tokens()

        # Should have refilled to capacity
        assert available >= 9  # Allow some timing tolerance

    def test_refill_does_not_exceed_capacity(self):
        """Test that refill doesn't exceed capacity."""
        bucket = RateLimitBucket(capacity=10, tokens=10.0, refill_rate=10.0)

        # Wait for 1 second
        time.sleep(1.0)

        available = bucket.available_tokens()

        # Should still be at capacity
        assert available == 10

    def test_time_until_available(self):
        """Test calculation of time until tokens are available."""
        bucket = RateLimitBucket(capacity=10, tokens=2.0, refill_rate=1.0)  # 1 token/sec

        # Need 5 tokens, have 2, so need 3 more = 3 seconds
        wait_time = bucket.time_until_available(5)

        assert wait_time == pytest.approx(3.0, rel=0.1)

    def test_time_until_available_when_available(self):
        """Test time_until_available when tokens are already available."""
        bucket = RateLimitBucket(capacity=10, tokens=10.0, refill_rate=1.0)

        wait_time = bucket.time_until_available(5)

        assert wait_time == 0.0


class TestRateLimitConfig:
    """Test RateLimitConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.max_iterations_per_minute == 60
        assert config.max_iterations_per_hour == 1000
        assert config.max_tool_calls_per_minute == 100
        assert config.max_memory_ops_per_minute == 200
        assert config.cooldown_on_limit == 5.0

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            max_iterations_per_minute=30,
            max_iterations_per_hour=500,
            max_tool_calls_per_minute=50,
            max_memory_ops_per_minute=100,
            cooldown_on_limit=2.0,
        )

        assert config.max_iterations_per_minute == 30
        assert config.max_iterations_per_hour == 500
        assert config.max_tool_calls_per_minute == 50
        assert config.max_memory_ops_per_minute == 100
        assert config.cooldown_on_limit == 2.0


class TestInternalRateLimiter:
    """Test InternalRateLimiter class."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        config = RateLimitConfig(
            max_iterations_per_minute=30,
            max_tool_calls_per_minute=50,
        )
        limiter = InternalRateLimiter(config)

        assert limiter.config == config
        assert "iteration_per_minute" in limiter._buckets
        assert "iteration_per_hour" in limiter._buckets
        assert "tool_calls" in limiter._buckets
        assert "memory_ops" in limiter._buckets

    @pytest.mark.asyncio
    async def test_check_iteration_limit_allows_first_request(self):
        """Test that first iteration is allowed."""
        config = RateLimitConfig(max_iterations_per_minute=10)
        limiter = InternalRateLimiter(config)

        result = await limiter.check_iteration_limit()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_iteration_limit_blocks_after_limit(self):
        """Test that iterations are blocked after limit."""
        config = RateLimitConfig(
            max_iterations_per_minute=3,
            max_iterations_per_hour=1000,
            cooldown_on_limit=0.1,  # Short cooldown for testing
        )
        limiter = InternalRateLimiter(config)

        # Use up all tokens
        for _ in range(3):
            result = await limiter.check_iteration_limit()
            assert result is True

        # Next request should be blocked (but will apply cooldown)
        result = await limiter.check_iteration_limit()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_iteration_limit_respects_hour_limit(self):
        """Test that hour limit is also enforced."""
        config = RateLimitConfig(
            max_iterations_per_minute=1000,  # High minute limit
            max_iterations_per_hour=2,  # Low hour limit
            cooldown_on_limit=0.1,
        )
        limiter = InternalRateLimiter(config)

        # Use up hour limit
        for _ in range(2):
            result = await limiter.check_iteration_limit()
            assert result is True

        # Should be blocked by hour limit
        result = await limiter.check_iteration_limit()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_tool_call_limit_allows_first_request(self):
        """Test that first tool call is allowed."""
        config = RateLimitConfig(max_tool_calls_per_minute=10)
        limiter = InternalRateLimiter(config)

        result = await limiter.check_tool_call_limit()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_tool_call_limit_blocks_after_limit(self):
        """Test that tool calls are blocked after limit."""
        config = RateLimitConfig(
            max_tool_calls_per_minute=2,
            cooldown_on_limit=0.1,
        )
        limiter = InternalRateLimiter(config)

        # Use up all tokens
        for _ in range(2):
            result = await limiter.check_tool_call_limit()
            assert result is True

        # Next request should be blocked
        result = await limiter.check_tool_call_limit()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_memory_operation_limit_allows_first_request(self):
        """Test that first memory operation is allowed."""
        config = RateLimitConfig(max_memory_ops_per_minute=10)
        limiter = InternalRateLimiter(config)

        result = await limiter.check_memory_operation_limit()

        assert result is True

    @pytest.mark.asyncio
    async def test_check_memory_operation_limit_blocks_after_limit(self):
        """Test that memory operations are blocked after limit."""
        config = RateLimitConfig(
            max_memory_ops_per_minute=2,
            cooldown_on_limit=0.1,
        )
        limiter = InternalRateLimiter(config)

        # Use up all tokens
        for _ in range(2):
            result = await limiter.check_memory_operation_limit()
            assert result is True

        # Next request should be blocked
        result = await limiter.check_memory_operation_limit()
        assert result is False

    def test_get_stats(self):
        """Test statistics retrieval."""
        config = RateLimitConfig()
        limiter = InternalRateLimiter(config)

        stats = limiter.get_stats()

        assert "total_requests" in stats
        assert "blocked_requests" in stats
        assert "cooldowns" in stats
        assert "buckets" in stats
        assert stats["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_tracks_requests(self):
        """Test that statistics track requests."""
        config = RateLimitConfig(max_iterations_per_minute=10)
        limiter = InternalRateLimiter(config)

        await limiter.check_iteration_limit()
        await limiter.check_tool_call_limit()

        stats = limiter.get_stats()

        assert stats["total_requests"] == 2

    @pytest.mark.asyncio
    async def test_get_stats_tracks_blocks(self):
        """Test that statistics track blocked requests."""
        config = RateLimitConfig(
            max_iterations_per_minute=1,
            max_iterations_per_hour=1000,
            cooldown_on_limit=0.1,
        )
        limiter = InternalRateLimiter(config)

        await limiter.check_iteration_limit()  # Success
        await limiter.check_iteration_limit()  # Blocked

        stats = limiter.get_stats()

        assert stats["blocked_requests"] >= 1
        assert stats["cooldowns"] >= 1

    def test_reset_stats(self):
        """Test statistics reset."""
        config = RateLimitConfig()
        limiter = InternalRateLimiter(config)

        limiter._stats["total_requests"] = 10
        limiter._stats["blocked_requests"] = 5

        limiter.reset_stats()

        stats = limiter.get_stats()
        assert stats["total_requests"] == 0
        assert stats["blocked_requests"] == 0

    def test_get_bucket_status(self):
        """Test bucket status retrieval."""
        config = RateLimitConfig(max_iterations_per_minute=60)
        limiter = InternalRateLimiter(config)

        status = limiter.get_bucket_status("iteration_per_minute")

        assert "capacity" in status
        assert "available" in status
        assert "refill_rate" in status
        assert "time_until_full" in status
        assert status["capacity"] == 60

    def test_get_bucket_status_invalid_bucket(self):
        """Test bucket status with invalid bucket name."""
        config = RateLimitConfig()
        limiter = InternalRateLimiter(config)

        with pytest.raises(ValueError, match="Unknown bucket"):
            limiter.get_bucket_status("invalid_bucket")


class TestGlobalRateLimiter:
    """Test global rate limiter functions."""

    def test_get_internal_rate_limiter(self):
        """Test getting global rate limiter instance."""
        limiter = get_internal_rate_limiter()

        assert isinstance(limiter, InternalRateLimiter)

    def test_get_internal_rate_limiter_singleton(self):
        """Test that global rate limiter is a singleton."""
        limiter1 = get_internal_rate_limiter()
        limiter2 = get_internal_rate_limiter()

        assert limiter1 is limiter2

    def test_configure_internal_rate_limiter(self):
        """Test configuring global rate limiter."""
        config = RateLimitConfig(max_iterations_per_minute=30)

        limiter = configure_internal_rate_limiter(config)

        assert isinstance(limiter, InternalRateLimiter)
        assert limiter.config == config

    def test_configure_internal_rate_limiter_replaces_global(self):
        """Test that configure replaces global instance."""
        config1 = RateLimitConfig(max_iterations_per_minute=30)
        config2 = RateLimitConfig(max_iterations_per_minute=60)

        limiter1 = configure_internal_rate_limiter(config1)
        limiter2 = configure_internal_rate_limiter(config2)

        # Should be different instances
        assert limiter1 is not limiter2
        assert limiter2.config == config2


class TestIntegration:
    """Integration tests for rate limiting."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        config = RateLimitConfig(
            max_iterations_per_minute=5,
            max_iterations_per_hour=1000,
            cooldown_on_limit=0.1,
        )
        limiter = InternalRateLimiter(config)

        # Fire 10 concurrent requests
        tasks = [limiter.check_iteration_limit() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # First 5 should succeed, rest should fail
        successes = sum(1 for r in results if r)
        assert successes == 5

    @pytest.mark.asyncio
    async def test_rate_recovery_after_cooldown(self):
        """Test that rate limit recovers after cooldown."""
        config = RateLimitConfig(
            max_iterations_per_minute=60,  # 1 per second
            max_iterations_per_hour=1000,
            cooldown_on_limit=0.1,
        )
        limiter = InternalRateLimiter(config)

        # Use up 2 tokens
        await limiter.check_iteration_limit()
        await limiter.check_iteration_limit()

        # Wait for refill (2 seconds for 2 tokens at 1/sec rate)
        await asyncio.sleep(2.1)

        # Should be able to make requests again
        result = await limiter.check_iteration_limit()
        assert result is True

    @pytest.mark.asyncio
    async def test_mixed_operation_types(self):
        """Test different operation types are tracked separately."""
        config = RateLimitConfig(
            max_iterations_per_minute=2,
            max_tool_calls_per_minute=2,
            max_memory_ops_per_minute=2,
            max_iterations_per_hour=1000,
            cooldown_on_limit=0.1,
        )
        limiter = InternalRateLimiter(config)

        # Each type should have independent limits
        result1 = await limiter.check_iteration_limit()
        result2 = await limiter.check_tool_call_limit()
        result3 = await limiter.check_memory_operation_limit()

        assert result1 is True
        assert result2 is True
        assert result3 is True

        stats = limiter.get_stats()
        assert stats["total_requests"] == 3
