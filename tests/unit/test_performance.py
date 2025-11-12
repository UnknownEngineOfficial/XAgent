"""Tests for performance monitoring and profiling."""

import asyncio

import pytest

from xagent.monitoring.performance import (
    PerformanceBenchmark,
    PerformanceProfiler,
    get_profiler,
    profile_async,
    profile_sync,
)


@pytest.fixture
def profiler():
    """Create a fresh profiler for each test."""
    p = PerformanceProfiler()
    p.enable()
    yield p
    p.reset()


class TestPerformanceProfiler:
    """Test performance profiler functionality."""

    def test_enable_disable(self, profiler):
        """Test enabling and disabling profiler."""
        assert profiler.is_enabled()
        
        profiler.disable()
        assert not profiler.is_enabled()
        
        profiler.enable()
        assert profiler.is_enabled()

    def test_timer_basic(self, profiler):
        """Test basic timer functionality."""
        profiler.start_timer("test_operation")
        # Simulate some work
        import time
        time.sleep(0.01)  # 10ms
        duration = profiler.stop_timer("test_operation")
        
        assert duration >= 0.01
        assert duration < 0.02  # Should be close to 10ms
        
        stats = profiler.get_stats("test_operation")
        assert stats["count"] == 1
        assert stats["avg"] >= 0.01

    def test_timer_multiple_calls(self, profiler):
        """Test timer with multiple calls."""
        for i in range(5):
            profiler.start_timer("repeated_op")
            import time
            time.sleep(0.005)  # 5ms
            profiler.stop_timer("repeated_op")
        
        stats = profiler.get_stats("repeated_op")
        assert stats["count"] == 5
        assert stats["avg"] >= 0.005
        assert stats["min"] >= 0.005

    def test_timer_nested(self, profiler):
        """Test nested timers."""
        profiler.start_timer("outer")
        import time
        time.sleep(0.005)
        
        profiler.start_timer("inner")
        time.sleep(0.005)
        profiler.stop_timer("inner")
        
        time.sleep(0.005)
        profiler.stop_timer("outer")
        
        outer_stats = profiler.get_stats("outer")
        inner_stats = profiler.get_stats("inner")
        
        assert outer_stats["avg"] > inner_stats["avg"]
        assert outer_stats["avg"] >= 0.015

    def test_timer_not_started(self, profiler):
        """Test stopping a timer that wasn't started."""
        duration = profiler.stop_timer("never_started")
        assert duration == 0.0

    @pytest.mark.asyncio
    async def test_measure_async(self, profiler):
        """Test async context manager for measuring."""
        async def async_operation():
            await asyncio.sleep(0.01)
        
        async with profiler.measure_async("async_op"):
            await async_operation()
        
        stats = profiler.get_stats("async_op")
        assert stats["count"] == 1
        assert stats["avg"] >= 0.01

    @pytest.mark.asyncio
    async def test_measure_async_multiple(self, profiler):
        """Test async measurement with multiple calls."""
        async def async_operation():
            await asyncio.sleep(0.005)
        
        for _ in range(3):
            async with profiler.measure_async("multi_async_op"):
                await async_operation()
        
        stats = profiler.get_stats("multi_async_op")
        assert stats["count"] == 3
        assert stats["avg"] >= 0.005

    def test_increment_counter(self, profiler):
        """Test counter functionality."""
        profiler.increment_counter("test_counter")
        profiler.increment_counter("test_counter", 5)
        profiler.increment_counter("test_counter", 3)
        
        # Counter is stored internally but not in get_stats
        assert profiler._counters["test_counter"] == 9

    def test_get_stats_empty(self, profiler):
        """Test getting stats for non-existent measurement."""
        stats = profiler.get_stats("nonexistent")
        assert stats["count"] == 0
        assert stats["avg"] == 0.0

    def test_get_stats_statistics(self, profiler):
        """Test statistical calculations."""
        # Record known values
        profiler._record_timing("test_stats", 0.001)  # 1ms
        profiler._record_timing("test_stats", 0.002)  # 2ms
        profiler._record_timing("test_stats", 0.003)  # 3ms
        profiler._record_timing("test_stats", 0.004)  # 4ms
        profiler._record_timing("test_stats", 0.005)  # 5ms
        
        stats = profiler.get_stats("test_stats")
        assert stats["count"] == 5
        assert stats["min"] == 0.001
        assert stats["max"] == 0.005
        assert stats["avg"] == 0.003
        assert stats["total"] == 0.015

    def test_get_all_stats(self, profiler):
        """Test getting all statistics."""
        profiler._record_timing("op1", 0.001)
        profiler._record_timing("op2", 0.002)
        profiler._record_timing("op3", 0.003)
        
        all_stats = profiler.get_all_stats()
        assert len(all_stats) == 3
        assert "op1" in all_stats
        assert "op2" in all_stats
        assert "op3" in all_stats

    def test_get_bottlenecks(self, profiler):
        """Test bottleneck identification."""
        profiler._record_timing("fast_op", 0.001)
        profiler._record_timing("slow_op", 0.100)
        profiler._record_timing("medium_op", 0.010)
        
        bottlenecks = profiler.get_bottlenecks(top_n=3)
        assert len(bottlenecks) == 3
        assert bottlenecks[0][0] == "slow_op"  # Slowest
        assert bottlenecks[1][0] == "medium_op"
        assert bottlenecks[2][0] == "fast_op"  # Fastest

    def test_get_summary_report(self, profiler):
        """Test summary report generation."""
        profiler._record_timing("op1", 0.001)
        profiler._record_timing("op2", 0.002)
        
        report = profiler.get_summary_report()
        assert "PERFORMANCE PROFILE SUMMARY" in report
        assert "op1" in report
        assert "op2" in report
        assert "TOP 5 BOTTLENECKS" in report

    def test_get_summary_report_empty(self, profiler):
        """Test summary report with no data."""
        report = profiler.get_summary_report()
        assert "No performance data collected" in report

    def test_reset(self, profiler):
        """Test resetting profiler data."""
        profiler._record_timing("test_op", 0.001)
        profiler.increment_counter("test_counter")
        
        assert len(profiler._timings) > 0
        assert len(profiler._counters) > 0
        
        profiler.reset()
        
        assert len(profiler._timings) == 0
        assert len(profiler._counters) == 0

    def test_max_samples_limit(self, profiler):
        """Test that profiler limits sample storage."""
        profiler._max_samples = 10
        
        for i in range(20):
            profiler._record_timing("test_limit", 0.001)
        
        assert len(profiler._timings["test_limit"]) == 10

    def test_export_data(self, profiler):
        """Test exporting profiling data."""
        profiler._record_timing("op1", 0.001)
        profiler._record_timing("op2", 0.002)
        profiler.increment_counter("counter1", 5)
        
        data = profiler.export_data()
        assert "timings" in data
        assert "counters" in data
        assert "stats" in data
        assert "op1" in data["timings"]
        assert "counter1" in data["counters"]

    def test_disabled_profiler(self, profiler):
        """Test that disabled profiler doesn't record data."""
        profiler.disable()
        
        profiler.start_timer("disabled_op")
        profiler.stop_timer("disabled_op")
        
        stats = profiler.get_stats("disabled_op")
        assert stats["count"] == 0


class TestProfileDecorators:
    """Test profile decorators."""

    @pytest.mark.asyncio
    async def test_profile_async_decorator(self):
        """Test async profile decorator."""
        profiler = get_profiler()
        profiler.enable()
        profiler.reset()
        
        @profile_async("test_async_decorated")
        async def async_function():
            await asyncio.sleep(0.01)
            return "result"
        
        result = await async_function()
        assert result == "result"
        
        stats = profiler.get_stats("test_async_decorated")
        assert stats["count"] == 1
        assert stats["avg"] >= 0.01

    @pytest.mark.asyncio
    async def test_profile_async_decorator_default_name(self):
        """Test async profile decorator with default name."""
        profiler = get_profiler()
        profiler.enable()
        profiler.reset()
        
        @profile_async()
        async def my_async_function():
            await asyncio.sleep(0.005)
        
        await my_async_function()
        
        # Check that a timing was recorded with the function's module.name
        all_stats = profiler.get_all_stats()
        assert len(all_stats) > 0

    def test_profile_sync_decorator(self):
        """Test sync profile decorator."""
        profiler = get_profiler()
        profiler.enable()
        profiler.reset()
        
        @profile_sync("test_sync_decorated")
        def sync_function():
            import time
            time.sleep(0.01)
            return "result"
        
        result = sync_function()
        assert result == "result"
        
        stats = profiler.get_stats("test_sync_decorated")
        assert stats["count"] == 1
        assert stats["avg"] >= 0.01

    def test_profile_sync_decorator_default_name(self):
        """Test sync profile decorator with default name."""
        profiler = get_profiler()
        profiler.enable()
        profiler.reset()
        
        @profile_sync()
        def my_sync_function():
            import time
            time.sleep(0.005)
        
        my_sync_function()
        
        # Check that a timing was recorded
        all_stats = profiler.get_all_stats()
        assert len(all_stats) > 0

    @pytest.mark.asyncio
    async def test_profile_async_disabled(self):
        """Test that disabled profiler doesn't affect decorated functions."""
        profiler = get_profiler()
        profiler.disable()
        profiler.reset()
        
        @profile_async("test_disabled")
        async def async_function():
            await asyncio.sleep(0.001)
            return "result"
        
        result = await async_function()
        assert result == "result"
        
        stats = profiler.get_stats("test_disabled")
        assert stats["count"] == 0


class TestPerformanceBenchmark:
    """Test performance benchmark utility."""

    @pytest.mark.asyncio
    async def test_benchmark_basic(self):
        """Test basic benchmark functionality."""
        benchmark = PerformanceBenchmark()
        
        async def test_operation():
            await asyncio.sleep(0.001)
        
        results = await benchmark.run(test_operation, iterations=10, warmup=2)
        
        assert results["iterations"] == 10
        assert results["warmup"] == 2
        assert results["avg"] >= 0.001
        assert results["min"] <= results["avg"] <= results["max"]
        assert results["throughput"] > 0

    @pytest.mark.asyncio
    async def test_benchmark_format_results(self):
        """Test benchmark results formatting."""
        benchmark = PerformanceBenchmark()
        
        async def test_operation():
            await asyncio.sleep(0.001)
        
        results = await benchmark.run(test_operation, iterations=5, warmup=1)
        formatted = benchmark.format_results(results)
        
        assert "Benchmark Results:" in formatted
        assert "Iterations: 5" in formatted
        assert "Throughput:" in formatted

    @pytest.mark.asyncio
    async def test_benchmark_statistics(self):
        """Test benchmark statistical calculations."""
        benchmark = PerformanceBenchmark()
        
        # Consistent operation for predictable results
        async def test_operation():
            await asyncio.sleep(0.001)
        
        results = await benchmark.run(test_operation, iterations=100, warmup=10)
        
        # P50 should be close to avg for consistent operations
        assert abs(results["p50"] - results["avg"]) < results["avg"] * 0.5
        
        # P95 should be higher than avg
        assert results["p95"] >= results["avg"]
        
        # P99 should be higher than P95
        assert results["p99"] >= results["p95"]


class TestGlobalProfiler:
    """Test global profiler instance."""

    def test_get_profiler_singleton(self):
        """Test that get_profiler returns the same instance."""
        profiler1 = get_profiler()
        profiler2 = get_profiler()
        assert profiler1 is profiler2

    def test_get_profiler_state_persistence(self):
        """Test that profiler state persists across calls."""
        profiler1 = get_profiler()
        profiler1.reset()
        profiler1._record_timing("persistent_op", 0.001)
        
        profiler2 = get_profiler()
        stats = profiler2.get_stats("persistent_op")
        assert stats["count"] == 1
