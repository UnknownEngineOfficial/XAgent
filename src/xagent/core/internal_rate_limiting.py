"""Internal rate limiting for cognitive loop and agent operations.

This module provides rate limiting to prevent resource exhaustion from
internal operations like cognitive loop iterations, tool executions, and
memory operations.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limits."""

    max_iterations_per_minute: int = 60
    max_iterations_per_hour: int = 1000
    max_tool_calls_per_minute: int = 100
    max_memory_ops_per_minute: int = 200
    cooldown_on_limit: float = 5.0  # seconds to wait when limit is hit


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting."""

    capacity: int
    tokens: float
    last_refill: float = field(default_factory=time.time)
    refill_rate: float = 1.0  # tokens per second

    def consume(self, amount: int = 1) -> bool:
        """
        Try to consume tokens.

        Args:
            amount: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        self._refill()

        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def available_tokens(self) -> int:
        """Get number of available tokens."""
        self._refill()
        return int(self.tokens)

    def time_until_available(self, amount: int = 1) -> float:
        """
        Calculate time until specified tokens are available.

        Args:
            amount: Number of tokens needed

        Returns:
            Time in seconds until tokens are available
        """
        self._refill()

        if self.tokens >= amount:
            return 0.0

        tokens_needed = amount - self.tokens
        return tokens_needed / self.refill_rate


class InternalRateLimiter:
    """
    Rate limiter for internal agent operations.

    Prevents resource exhaustion by limiting:
    - Cognitive loop iterations
    - Tool executions
    - Memory operations
    """

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        """
        Initialize internal rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()

        # Create buckets for different operation types
        self._buckets: dict[str, RateLimitBucket] = {
            "iteration_per_minute": RateLimitBucket(
                capacity=self.config.max_iterations_per_minute,
                tokens=float(self.config.max_iterations_per_minute),
                refill_rate=self.config.max_iterations_per_minute / 60.0,
            ),
            "iteration_per_hour": RateLimitBucket(
                capacity=self.config.max_iterations_per_hour,
                tokens=float(self.config.max_iterations_per_hour),
                refill_rate=self.config.max_iterations_per_hour / 3600.0,
            ),
            "tool_calls": RateLimitBucket(
                capacity=self.config.max_tool_calls_per_minute,
                tokens=float(self.config.max_tool_calls_per_minute),
                refill_rate=self.config.max_tool_calls_per_minute / 60.0,
            ),
            "memory_ops": RateLimitBucket(
                capacity=self.config.max_memory_ops_per_minute,
                tokens=float(self.config.max_memory_ops_per_minute),
                refill_rate=self.config.max_memory_ops_per_minute / 60.0,
            ),
        }

        # Statistics
        self._stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "cooldowns": 0,
        }

    async def check_iteration_limit(self) -> bool:
        """
        Check if cognitive loop iteration is allowed.

        Returns:
            True if iteration is allowed, False otherwise
        """
        self._stats["total_requests"] += 1

        # Check both minute and hour limits
        minute_ok = self._buckets["iteration_per_minute"].consume()
        hour_ok = self._buckets["iteration_per_hour"].consume()

        if not minute_ok or not hour_ok:
            self._stats["blocked_requests"] += 1

            # Calculate cooldown
            wait_time_minute = self._buckets["iteration_per_minute"].time_until_available()
            wait_time_hour = self._buckets["iteration_per_hour"].time_until_available()
            wait_time = max(wait_time_minute, wait_time_hour)

            logger.warning(
                f"Cognitive loop iteration rate limit reached. "
                f"Waiting {wait_time:.1f}s before next iteration.",
                extra={
                    "minute_tokens": self._buckets["iteration_per_minute"].available_tokens(),
                    "hour_tokens": self._buckets["iteration_per_hour"].available_tokens(),
                    "wait_time": wait_time,
                },
            )

            # Apply cooldown
            self._stats["cooldowns"] += 1
            await asyncio.sleep(min(wait_time, self.config.cooldown_on_limit))

            # Restore tokens that weren't consumed
            if not minute_ok:
                self._buckets["iteration_per_minute"].tokens += 1
            if not hour_ok:
                self._buckets["iteration_per_hour"].tokens += 1

            return False

        return True

    async def check_tool_call_limit(self) -> bool:
        """
        Check if tool call is allowed.

        Returns:
            True if tool call is allowed, False otherwise
        """
        self._stats["total_requests"] += 1

        if not self._buckets["tool_calls"].consume():
            self._stats["blocked_requests"] += 1

            wait_time = self._buckets["tool_calls"].time_until_available()

            logger.warning(
                f"Tool call rate limit reached. Waiting {wait_time:.1f}s.",
                extra={
                    "available_tokens": self._buckets["tool_calls"].available_tokens(),
                    "wait_time": wait_time,
                },
            )

            self._stats["cooldowns"] += 1
            await asyncio.sleep(min(wait_time, self.config.cooldown_on_limit))

            # Restore token
            self._buckets["tool_calls"].tokens += 1
            return False

        return True

    async def check_memory_operation_limit(self) -> bool:
        """
        Check if memory operation is allowed.

        Returns:
            True if memory operation is allowed, False otherwise
        """
        self._stats["total_requests"] += 1

        if not self._buckets["memory_ops"].consume():
            self._stats["blocked_requests"] += 1

            wait_time = self._buckets["memory_ops"].time_until_available()

            logger.warning(
                f"Memory operation rate limit reached. Waiting {wait_time:.1f}s.",
                extra={
                    "available_tokens": self._buckets["memory_ops"].available_tokens(),
                    "wait_time": wait_time,
                },
            )

            self._stats["cooldowns"] += 1
            await asyncio.sleep(min(wait_time, self.config.cooldown_on_limit))

            # Restore token
            self._buckets["memory_ops"].tokens += 1
            return False

        return True

    def get_stats(self) -> dict[str, Any]:
        """
        Get rate limiting statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            **self._stats,
            "buckets": {
                name: {
                    "capacity": bucket.capacity,
                    "available": bucket.available_tokens(),
                    "refill_rate": bucket.refill_rate,
                }
                for name, bucket in self._buckets.items()
            },
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "cooldowns": 0,
        }

    def get_bucket_status(self, bucket_name: str) -> dict[str, Any]:
        """
        Get status of a specific bucket.

        Args:
            bucket_name: Name of the bucket

        Returns:
            Dictionary with bucket status
        """
        if bucket_name not in self._buckets:
            raise ValueError(f"Unknown bucket: {bucket_name}")

        bucket = self._buckets[bucket_name]
        return {
            "capacity": bucket.capacity,
            "available": bucket.available_tokens(),
            "refill_rate": bucket.refill_rate,
            "time_until_full": (bucket.capacity - bucket.tokens) / bucket.refill_rate
            if bucket.tokens < bucket.capacity
            else 0.0,
        }


# Global rate limiter instance
_internal_rate_limiter: InternalRateLimiter | None = None


def get_internal_rate_limiter() -> InternalRateLimiter:
    """
    Get global internal rate limiter instance.

    Returns:
        InternalRateLimiter instance
    """
    global _internal_rate_limiter
    if _internal_rate_limiter is None:
        _internal_rate_limiter = InternalRateLimiter()
    return _internal_rate_limiter


def configure_internal_rate_limiter(config: RateLimitConfig) -> InternalRateLimiter:
    """
    Configure global internal rate limiter.

    Args:
        config: Rate limit configuration

    Returns:
        Configured InternalRateLimiter instance
    """
    global _internal_rate_limiter
    _internal_rate_limiter = InternalRateLimiter(config)
    return _internal_rate_limiter
