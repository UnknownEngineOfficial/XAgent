"""Performance profiling demonstration for X-Agent."""

import asyncio

from xagent.monitoring.performance import (
    PerformanceBenchmark,
    get_profiler,
    profile_async,
    profile_sync,
)


async def simulate_cognitive_loop():
    """Simulate a cognitive loop iteration with profiling."""
    profiler = get_profiler()
    profiler.enable()
    
    print("🧠 Simulating Cognitive Loop with Performance Profiling...")
    print()
    
    # Simulate 10 iterations of the cognitive loop
    for iteration in range(10):
        # Phase 1: Perception
        profiler.start_timer("phase.perception")
        await asyncio.sleep(0.005)  # Simulate perception work
        profiler.stop_timer("phase.perception")
        
        # Phase 2: Interpretation
        profiler.start_timer("phase.interpretation")
        await asyncio.sleep(0.010)  # Simulate interpretation work
        profiler.stop_timer("phase.interpretation")
        
        # Phase 3: Planning
        profiler.start_timer("phase.planning")
        await asyncio.sleep(0.020)  # Simulate planning work (slower)
        profiler.stop_timer("phase.planning")
        
        # Phase 4: Execution
        profiler.start_timer("phase.execution")
        await asyncio.sleep(0.015)  # Simulate execution work
        profiler.stop_timer("phase.execution")
        
        # Phase 5: Reflection
        profiler.start_timer("phase.reflection")
        await asyncio.sleep(0.008)  # Simulate reflection work
        profiler.stop_timer("phase.reflection")
        
        profiler.increment_counter("iterations")
    
    print(f"✅ Completed {iteration + 1} iterations")
    print()
    return profiler


async def demonstrate_async_decorators():
    """Demonstrate async function profiling with decorators."""
    print("🎯 Demonstrating Async Function Profiling...")
    print()
    
    profiler = get_profiler()
    profiler.enable()
    
    @profile_async("decorated_operation")
    async def async_operation(duration: float):
        """Simulated async operation."""
        await asyncio.sleep(duration)
    
    # Call the decorated function multiple times
    for i in range(5):
        duration = 0.01 * (i + 1)  # Increasing duration
        await async_operation(duration)
    
    print("✅ Completed decorated function calls")
    print()


def demonstrate_sync_decorators():
    """Demonstrate sync function profiling with decorators."""
    print("⚡ Demonstrating Sync Function Profiling...")
    print()
    
    profiler = get_profiler()
    profiler.enable()
    
    @profile_sync("sync_computation")
    def compute_fibonacci(n: int) -> int:
        """Compute Fibonacci number (inefficient recursive version for demo)."""
        if n <= 1:
            return n
        return compute_fibonacci(n - 1) + compute_fibonacci(n - 2)
    
    # Call the decorated function
    results = []
    for i in range(5):
        n = 10 + i * 2  # 10, 12, 14, 16, 18
        result = compute_fibonacci(n)
        results.append((n, result))
    
    print("✅ Completed sync function calls")
    print()


async def demonstrate_context_manager():
    """Demonstrate profiling with context manager."""
    print("📊 Demonstrating Context Manager Profiling...")
    print()
    
    profiler = get_profiler()
    profiler.enable()
    
    # Measure different database operations
    async with profiler.measure_async("database.query"):
        await asyncio.sleep(0.015)
        print("  📦 Executed database query")
    
    async with profiler.measure_async("database.update"):
        await asyncio.sleep(0.020)
        print("  ✏️  Executed database update")
    
    async with profiler.measure_async("database.index"):
        await asyncio.sleep(0.030)
        print("  🔍 Rebuilt database index")
    
    print()


async def demonstrate_benchmarking():
    """Demonstrate performance benchmarking."""
    print("🏃 Demonstrating Performance Benchmarking...")
    print()
    
    benchmark = PerformanceBenchmark()
    
    async def fast_operation():
        """Fast operation for benchmarking."""
        await asyncio.sleep(0.001)
    
    async def medium_operation():
        """Medium speed operation for benchmarking."""
        await asyncio.sleep(0.005)
    
    async def slow_operation():
        """Slow operation for benchmarking."""
        await asyncio.sleep(0.010)
    
    # Benchmark fast operation
    print("  🚀 Benchmarking fast operation...")
    results = await benchmark.run(fast_operation, iterations=50, warmup=5)
    print(benchmark.format_results(results))
    print()
    
    # Benchmark medium operation
    print("  ⏱️  Benchmarking medium operation...")
    results = await benchmark.run(medium_operation, iterations=20, warmup=3)
    print(benchmark.format_results(results))
    print()
    
    # Benchmark slow operation
    print("  🐌 Benchmarking slow operation...")
    results = await benchmark.run(slow_operation, iterations=10, warmup=2)
    print(benchmark.format_results(results))
    print()


def print_performance_report():
    """Print comprehensive performance report."""
    profiler = get_profiler()
    
    print("=" * 80)
    print("📈 PERFORMANCE ANALYSIS REPORT")
    print("=" * 80)
    print()
    
    # Print summary report
    print(profiler.get_summary_report())
    print()
    
    # Print top bottlenecks
    print("🔴 TOP 10 BOTTLENECKS:")
    print("-" * 40)
    bottlenecks = profiler.get_bottlenecks(top_n=10)
    for i, (name, avg_duration) in enumerate(bottlenecks, 1):
        print(f"{i:2d}. {name:<35} {avg_duration*1000:>8.2f}ms")
    print()
    
    # Print phase-specific analysis
    print("🧠 COGNITIVE LOOP PHASE ANALYSIS:")
    print("-" * 40)
    phases = [
        "phase.perception",
        "phase.interpretation",
        "phase.planning",
        "phase.execution",
        "phase.reflection",
    ]
    
    total_phase_time = 0.0
    phase_stats = []
    
    for phase in phases:
        stats = profiler.get_stats(phase)
        if stats["count"] > 0:
            total_phase_time += stats["total"]
            phase_stats.append((phase, stats))
    
    for phase, stats in phase_stats:
        percentage = (stats["total"] / total_phase_time * 100) if total_phase_time > 0 else 0
        print(
            f"  {phase.split('.')[-1]:<15} "
            f"{stats['avg']*1000:>6.2f}ms avg  "
            f"{stats['total']*1000:>8.2f}ms total  "
            f"({percentage:>5.1f}%)"
        )
    print()


async def main():
    """Run all demonstrations."""
    print()
    print("🎪 X-AGENT PERFORMANCE PROFILING DEMONSTRATION")
    print("=" * 80)
    print()
    
    # 1. Simulate cognitive loop with profiling
    await simulate_cognitive_loop()
    
    # 2. Demonstrate async decorators
    await demonstrate_async_decorators()
    
    # 3. Demonstrate sync decorators
    demonstrate_sync_decorators()
    
    # 4. Demonstrate context manager
    await demonstrate_context_manager()
    
    # 5. Demonstrate benchmarking
    await demonstrate_benchmarking()
    
    # 6. Print comprehensive report
    print_performance_report()
    
    # 7. Show recommendations
    print("💡 PERFORMANCE RECOMMENDATIONS:")
    print("-" * 40)
    profiler = get_profiler()
    bottlenecks = profiler.get_bottlenecks(top_n=3)
    
    if bottlenecks:
        print("  Based on the profiling data, consider optimizing:")
        for i, (name, avg_duration) in enumerate(bottlenecks, 1):
            print(f"  {i}. {name} (avg: {avg_duration*1000:.2f}ms)")
    else:
        print("  No significant bottlenecks detected!")
    
    print()
    print("=" * 80)
    print("✅ Performance profiling demonstration complete!")
    print()
    
    # Export profiling data
    data = profiler.export_data()
    print(f"📊 Collected {len(data['timings'])} timing metrics")
    print(f"📊 Collected {len(data['counters'])} counter metrics")
    print()


if __name__ == "__main__":
    asyncio.run(main())
