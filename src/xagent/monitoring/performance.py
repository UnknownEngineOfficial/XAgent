"""Performance monitoring and profiling for X-Agent."""

import asyncio
import functools
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Callable

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class PerformanceProfiler:
    """
    Performance profiler for tracking execution times and bottlenecks.
    
    Features:
    - Phase-level timing (perception, interpretation, planning, execution, reflection)
    - Function-level timing with decorators
    - Statistical aggregation (min, max, avg, p95, p99)
    - Bottleneck identification
    - Memory usage tracking (optional)
    - Real-time performance reporting
    """

    def __init__(self) -> None:
        """Initialize performance profiler."""
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._counters: dict[str, int] = defaultdict(int)
        self._active_timers: dict[str, float] = {}
        self._max_samples = 1000  # Keep last N samples per metric
        self._enabled = True

    def enable(self) -> None:
        """Enable profiling."""
        self._enabled = True
        logger.info("Performance profiling enabled")

    def disable(self) -> None:
        """Disable profiling."""
        self._enabled = False
        logger.info("Performance profiling disabled")

    def is_enabled(self) -> bool:
        """Check if profiling is enabled."""
        return self._enabled

    def start_timer(self, name: str) -> None:
        """
        Start a named timer.
        
        Args:
            name: Timer name
        """
        if not self._enabled:
            return
        self._active_timers[name] = time.perf_counter()

    def stop_timer(self, name: str) -> float:
        """
        Stop a named timer and record the duration.
        
        Args:
            name: Timer name
            
        Returns:
            Duration in seconds
        """
        if not self._enabled:
            return 0.0

        start_time = self._active_timers.pop(name, None)
        if start_time is None:
            logger.warning(f"Timer '{name}' was not started")
            return 0.0

        duration = time.perf_counter() - start_time
        self._record_timing(name, duration)
        return duration

    def _record_timing(self, name: str, duration: float) -> None:
        """
        Record a timing measurement.
        
        Args:
            name: Measurement name
            duration: Duration in seconds
        """
        timings = self._timings[name]
        timings.append(duration)

        # Keep only last N samples to prevent memory growth
        if len(timings) > self._max_samples:
            self._timings[name] = timings[-self._max_samples :]

        self._counters[name] += 1

    def increment_counter(self, name: str, value: int = 1) -> None:
        """
        Increment a counter.
        
        Args:
            name: Counter name
            value: Increment value
        """
        if not self._enabled:
            return
        self._counters[name] += value

    @asynccontextmanager
    async def measure_async(self, name: str):
        """
        Context manager for measuring async operations.
        
        Usage:
            async with profiler.measure_async("my_operation"):
                await do_something()
        
        Args:
            name: Operation name
        """
        if not self._enabled:
            yield
            return

        start = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start
            self._record_timing(name, duration)

    def get_stats(self, name: str) -> dict[str, Any]:
        """
        Get statistics for a named measurement.
        
        Args:
            name: Measurement name
            
        Returns:
            Statistics dictionary
        """
        timings = self._timings.get(name, [])
        if not timings:
            return {
                "name": name,
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "total": 0.0,
            }

        sorted_timings = sorted(timings)
        count = len(sorted_timings)
        total = sum(sorted_timings)

        return {
            "name": name,
            "count": count,
            "min": sorted_timings[0],
            "max": sorted_timings[-1],
            "avg": total / count,
            "p50": sorted_timings[int(count * 0.50)],
            "p95": sorted_timings[int(count * 0.95)],
            "p99": sorted_timings[int(count * 0.99)],
            "total": total,
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all measurements.
        
        Returns:
            Dictionary of all statistics
        """
        return {name: self.get_stats(name) for name in self._timings.keys()}

    def get_bottlenecks(self, top_n: int = 10) -> list[tuple[str, float]]:
        """
        Identify the slowest operations.
        
        Args:
            top_n: Number of bottlenecks to return
            
        Returns:
            List of (name, avg_duration) tuples sorted by avg duration
        """
        bottlenecks = []
        for name in self._timings.keys():
            stats = self.get_stats(name)
            bottlenecks.append((name, stats["avg"]))

        bottlenecks.sort(key=lambda x: x[1], reverse=True)
        return bottlenecks[:top_n]

    def get_summary_report(self) -> str:
        """
        Generate a human-readable summary report.
        
        Returns:
            Formatted report string
        """
        lines = ["=" * 80, "PERFORMANCE PROFILE SUMMARY", "=" * 80, ""]

        all_stats = self.get_all_stats()
        if not all_stats:
            lines.append("No performance data collected")
            return "\n".join(lines)

        # Sort by total time
        sorted_stats = sorted(
            all_stats.items(), key=lambda x: x[1]["total"], reverse=True
        )

        # Header
        lines.append(
            f"{'Operation':<40} {'Count':>8} {'Avg(ms)':>10} {'P95(ms)':>10} {'Total(s)':>10}"
        )
        lines.append("-" * 80)

        # Data rows
        for name, stats in sorted_stats:
            lines.append(
                f"{name:<40} {stats['count']:>8} "
                f"{stats['avg']*1000:>10.2f} {stats['p95']*1000:>10.2f} "
                f"{stats['total']:>10.2f}"
            )

        lines.append("")
        lines.append("=" * 80)

        # Bottlenecks section
        lines.append("")
        lines.append("TOP 5 BOTTLENECKS (by average duration):")
        lines.append("-" * 40)
        bottlenecks = self.get_bottlenecks(top_n=5)
        for name, avg_duration in bottlenecks:
            lines.append(f"  {name}: {avg_duration*1000:.2f}ms avg")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all profiling data."""
        self._timings.clear()
        self._counters.clear()
        self._active_timers.clear()
        logger.info("Performance profiling data reset")

    def export_data(self) -> dict[str, Any]:
        """
        Export all profiling data.
        
        Returns:
            Dictionary with all timings and counters
        """
        return {
            "timings": {name: list(values) for name, values in self._timings.items()},
            "counters": dict(self._counters),
            "stats": self.get_all_stats(),
        }


# Global profiler instance
_global_profiler: PerformanceProfiler | None = None


def get_profiler() -> PerformanceProfiler:
    """
    Get or create the global profiler instance.
    
    Returns:
        PerformanceProfiler instance
    """
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def profile_async(name: str | None = None) -> Callable:
    """
    Decorator for profiling async functions.
    
    Usage:
        @profile_async("my_function")
        async def my_function():
            await do_something()
    
    Args:
        name: Optional custom name (defaults to function name)
    """

    def decorator(func: Callable) -> Callable:
        operation_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            profiler = get_profiler()
            if not profiler.is_enabled():
                return await func(*args, **kwargs)

            async with profiler.measure_async(operation_name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def profile_sync(name: str | None = None) -> Callable:
    """
    Decorator for profiling sync functions.
    
    Usage:
        @profile_sync("my_function")
        def my_function():
            do_something()
    
    Args:
        name: Optional custom name (defaults to function name)
    """

    def decorator(func: Callable) -> Callable:
        operation_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profiler = get_profiler()
            if not profiler.is_enabled():
                return func(*args, **kwargs)

            profiler.start_timer(operation_name)
            try:
                return func(*args, **kwargs)
            finally:
                profiler.stop_timer(operation_name)

        return wrapper

    return decorator


class PerformanceBenchmark:
    """
    Utility for running performance benchmarks.
    
    Usage:
        benchmark = PerformanceBenchmark()
        
        async def test_operation():
            await do_something()
        
        results = await benchmark.run(test_operation, iterations=100)
        print(benchmark.format_results(results))
    """

    async def run(
        self, operation: Callable, iterations: int = 100, warmup: int = 10
    ) -> dict[str, Any]:
        """
        Run a performance benchmark.
        
        Args:
            operation: Async operation to benchmark
            iterations: Number of iterations
            warmup: Number of warmup iterations (not counted)
            
        Returns:
            Benchmark results
        """
        logger.info(
            f"Running benchmark: {iterations} iterations + {warmup} warmup iterations"
        )

        # Warmup
        for _ in range(warmup):
            await operation()

        # Actual benchmark
        durations = []
        for _ in range(iterations):
            start = time.perf_counter()
            await operation()
            duration = time.perf_counter() - start
            durations.append(duration)

        # Calculate statistics
        sorted_durations = sorted(durations)
        count = len(sorted_durations)
        total = sum(sorted_durations)

        return {
            "iterations": iterations,
            "warmup": warmup,
            "min": sorted_durations[0],
            "max": sorted_durations[-1],
            "avg": total / count,
            "p50": sorted_durations[int(count * 0.50)],
            "p95": sorted_durations[int(count * 0.95)],
            "p99": sorted_durations[int(count * 0.99)],
            "total": total,
            "throughput": count / total,  # operations per second
        }

    def format_results(self, results: dict[str, Any]) -> str:
        """
        Format benchmark results as a human-readable string.
        
        Args:
            results: Benchmark results
            
        Returns:
            Formatted string
        """
        return (
            f"Benchmark Results:\n"
            f"  Iterations: {results['iterations']} (+ {results['warmup']} warmup)\n"
            f"  Min: {results['min']*1000:.2f}ms\n"
            f"  Max: {results['max']*1000:.2f}ms\n"
            f"  Avg: {results['avg']*1000:.2f}ms\n"
            f"  P50: {results['p50']*1000:.2f}ms\n"
            f"  P95: {results['p95']*1000:.2f}ms\n"
            f"  P99: {results['p99']*1000:.2f}ms\n"
            f"  Total: {results['total']:.2f}s\n"
            f"  Throughput: {results['throughput']:.2f} ops/sec"
        )
