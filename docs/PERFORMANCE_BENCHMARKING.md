# Performance Benchmarking Guide for X-Agent

This guide provides comprehensive information on performance profiling, benchmarking, and optimization for X-Agent.

## Table of Contents

1. [Overview](#overview)
2. [Performance Profiler](#performance-profiler)
3. [Benchmarking Utilities](#benchmarking-utilities)
4. [Integration with Cognitive Loop](#integration-with-cognitive-loop)
5. [Best Practices](#best-practices)
6. [Common Bottlenecks](#common-bottlenecks)
7. [Optimization Strategies](#optimization-strategies)

---

## Overview

X-Agent includes a comprehensive performance profiling system that enables:

- **Phase-level timing** - Track time spent in each cognitive loop phase
- **Function-level profiling** - Measure individual function performance
- **Statistical analysis** - Calculate min, max, avg, percentiles (p50, p95, p99)
- **Bottleneck identification** - Automatically identify slow operations
- **Benchmarking** - Compare performance across different implementations
- **Production monitoring** - Export metrics to Prometheus/Grafana

### Key Components

- `PerformanceProfiler` - Main profiling engine
- `PerformanceBenchmark` - Benchmarking utilities
- `@profile_async` / `@profile_sync` - Function decorators
- `measure_async` - Context manager for async operations

---

## Performance Profiler

### Basic Usage

```python
from xagent.monitoring.performance import get_profiler

# Get the global profiler instance
profiler = get_profiler()
profiler.enable()

# Start a timer
profiler.start_timer("my_operation")

# ... do work ...

# Stop the timer
duration = profiler.stop_timer("my_operation")
print(f"Operation took {duration*1000:.2f}ms")

# Get statistics
stats = profiler.get_stats("my_operation")
print(f"Average: {stats['avg']*1000:.2f}ms")
print(f"P95: {stats['p95']*1000:.2f}ms")
```

### Context Manager

For async operations, use the context manager:

```python
async def my_async_function():
    profiler = get_profiler()
    
    async with profiler.measure_async("database_query"):
        # Query execution
        await db.query("SELECT * FROM users")
    
    async with profiler.measure_async("api_call"):
        # API call
        await api.fetch_data()
```

### Function Decorators

Automatically profile functions with decorators:

```python
from xagent.monitoring.performance import profile_async, profile_sync

@profile_async("user_authentication")
async def authenticate_user(username: str, password: str):
    # Authentication logic
    await verify_credentials(username, password)
    return generate_token()

@profile_sync("data_processing")
def process_data(data: list) -> list:
    # Data processing logic
    return [transform(item) for item in data]
```

### Getting Statistics

```python
# Get stats for a specific operation
stats = profiler.get_stats("my_operation")
print(f"Count: {stats['count']}")
print(f"Min: {stats['min']*1000:.2f}ms")
print(f"Max: {stats['max']*1000:.2f}ms")
print(f"Avg: {stats['avg']*1000:.2f}ms")
print(f"P50 (median): {stats['p50']*1000:.2f}ms")
print(f"P95: {stats['p95']*1000:.2f}ms")
print(f"P99: {stats['p99']*1000:.2f}ms")
print(f"Total: {stats['total']:.2f}s")

# Get all statistics
all_stats = profiler.get_all_stats()
for operation, stats in all_stats.items():
    print(f"{operation}: avg={stats['avg']*1000:.2f}ms")
```

### Identifying Bottlenecks

```python
# Get top 10 slowest operations
bottlenecks = profiler.get_bottlenecks(top_n=10)
for name, avg_duration in bottlenecks:
    print(f"{name}: {avg_duration*1000:.2f}ms avg")
```

### Summary Report

Generate a comprehensive report:

```python
report = profiler.get_summary_report()
print(report)
```

Output example:

```
================================================================================
PERFORMANCE PROFILE SUMMARY
================================================================================

Operation                                   Count    Avg(ms)    P95(ms)   Total(s)
--------------------------------------------------------------------------------
phase.planning                                 10      20.11      20.15       0.20
phase.execution                                10      15.12      15.15       0.15
phase.interpretation                           10      10.10      10.13       0.10
phase.reflection                               10       8.11       8.14       0.08
phase.perception                               10       5.11       5.16       0.05

================================================================================

TOP 5 BOTTLENECKS (by average duration):
----------------------------------------
  phase.planning: 20.11ms avg
  phase.execution: 15.12ms avg
  phase.interpretation: 10.10ms avg
  phase.reflection: 8.11ms avg
  phase.perception: 5.11ms avg

================================================================================
```

### Export Data

```python
# Export all profiling data for analysis
data = profiler.export_data()
print(f"Timings: {len(data['timings'])} operations")
print(f"Counters: {len(data['counters'])} counters")

# Can be saved to JSON for offline analysis
import json
with open("profile_data.json", "w") as f:
    json.dump(data, f, indent=2)
```

---

## Benchmarking Utilities

### Running Benchmarks

```python
from xagent.monitoring.performance import PerformanceBenchmark

benchmark = PerformanceBenchmark()

async def operation_to_test():
    # Your async operation
    await process_data()

# Run benchmark with 100 iterations and 10 warmup runs
results = await benchmark.run(
    operation_to_test,
    iterations=100,
    warmup=10
)

# Print formatted results
print(benchmark.format_results(results))
```

Output example:

```
Benchmark Results:
  Iterations: 100 (+ 10 warmup)
  Min: 5.12ms
  Max: 6.48ms
  Avg: 5.45ms
  P50: 5.42ms
  P95: 5.98ms
  P99: 6.32ms
  Total: 0.55s
  Throughput: 183.21 ops/sec
```

### Comparing Implementations

```python
# Benchmark implementation A
async def implementation_a():
    # Original implementation
    pass

results_a = await benchmark.run(implementation_a, iterations=100)
print("Implementation A:")
print(benchmark.format_results(results_a))

# Benchmark implementation B
async def implementation_b():
    # Optimized implementation
    pass

results_b = await benchmark.run(implementation_b, iterations=100)
print("\nImplementation B:")
print(benchmark.format_results(results_b))

# Compare
speedup = results_b['avg'] / results_a['avg']
print(f"\nSpeedup: {speedup:.2f}x")
```

---

## Integration with Cognitive Loop

### Profiling Cognitive Loop Phases

The cognitive loop has 5 phases that can be profiled:

1. **Perception** - Gathering inputs
2. **Interpretation** - Understanding context
3. **Planning** - Creating action plans
4. **Execution** - Executing actions
5. **Reflection** - Learning from results

```python
from xagent.monitoring.performance import get_profiler

profiler = get_profiler()
profiler.enable()

# In cognitive_loop.py, wrap each phase:

# Phase 1: Perception
profiler.start_timer("phase.perception")
perception_data = await self._perceive()
profiler.stop_timer("phase.perception")

# Phase 2: Interpretation
profiler.start_timer("phase.interpretation")
context = await self._interpret(perception_data)
profiler.stop_timer("phase.interpretation")

# Phase 3: Planning
profiler.start_timer("phase.planning")
plan = await self._plan(context)
profiler.stop_timer("phase.planning")

# Phase 4: Execution
profiler.start_timer("phase.execution")
result = await self._execute(plan)
profiler.stop_timer("phase.execution")

# Phase 5: Reflection
profiler.start_timer("phase.reflection")
await self._reflect(result)
profiler.stop_timer("phase.reflection")
```

### Analyzing Phase Performance

```python
# After running the loop
phases = [
    "phase.perception",
    "phase.interpretation",
    "phase.planning",
    "phase.execution",
    "phase.reflection",
]

total_time = 0
phase_times = []

for phase in phases:
    stats = profiler.get_stats(phase)
    total_time += stats['total']
    phase_times.append((phase, stats['total']))

print("Cognitive Loop Phase Analysis:")
print("-" * 60)
for phase, time in phase_times:
    percentage = (time / total_time * 100) if total_time > 0 else 0
    print(f"{phase.split('.')[-1]:<15} {time*1000:>8.2f}ms ({percentage:>5.1f}%)")
```

---

## Best Practices

### 1. Enable Profiling Selectively

Don't profile everything in production:

```python
from xagent.config import settings

profiler = get_profiler()
if settings.enable_profiling:
    profiler.enable()
else:
    profiler.disable()
```

### 2. Use Appropriate Sample Sizes

```python
# For development/testing
results = await benchmark.run(operation, iterations=10, warmup=2)

# For production benchmarks
results = await benchmark.run(operation, iterations=100, warmup=10)

# For release testing
results = await benchmark.run(operation, iterations=1000, warmup=50)
```

### 3. Reset Between Tests

```python
# Start fresh for each test suite
profiler.reset()

# Run test
await run_test()

# Get results
report = profiler.get_summary_report()

# Reset for next test
profiler.reset()
```

### 4. Profile Critical Paths Only

Focus on operations that:
- Are called frequently
- Are known to be slow
- Handle external I/O (database, API calls)
- Are on the critical path

### 5. Export for Analysis

```python
# Export after each run
data = profiler.export_data()

# Save with timestamp
import time
timestamp = int(time.time())
with open(f"profile_{timestamp}.json", "w") as f:
    json.dump(data, f)
```

---

## Common Bottlenecks

### 1. Planning Phase

**Symptom**: `phase.planning` has high average duration (>100ms)

**Causes**:
- Complex LLM calls
- Large context processing
- Inefficient plan generation

**Solutions**:
- Cache similar plans
- Reduce context size
- Parallel plan generation
- Use faster LLM models

### 2. Execution Phase

**Symptom**: `phase.execution` dominates total time (>50%)

**Causes**:
- Slow tool execution
- Synchronous I/O operations
- Lack of parallelization

**Solutions**:
- Parallelize independent actions
- Use async I/O
- Implement tool caching
- Optimize tool implementations

### 3. Memory Operations

**Symptom**: Memory-related operations are slow

**Causes**:
- Large data serialization
- Slow database queries
- Cache misses

**Solutions**:
- Use Redis for hot data
- Implement pagination
- Optimize queries
- Increase cache hit rate

### 4. LLM API Calls

**Symptom**: High latency on LLM operations

**Causes**:
- Network latency
- Large prompts
- Sequential calls

**Solutions**:
- Batch requests when possible
- Reduce prompt size
- Use streaming responses
- Cache common responses

---

## Optimization Strategies

### 1. Async/Await Optimization

```python
# Bad: Sequential execution
result1 = await operation1()
result2 = await operation2()
result3 = await operation3()

# Good: Parallel execution
results = await asyncio.gather(
    operation1(),
    operation2(),
    operation3()
)
```

### 2. Caching

```python
from functools import lru_cache

# For sync functions
@lru_cache(maxsize=128)
def expensive_computation(x):
    # Expensive calculation
    return result

# For async functions with Redis
async def get_data(key):
    # Try cache first
    cached = await redis.get(key)
    if cached:
        return cached
    
    # Compute if not cached
    result = await expensive_operation()
    await redis.set(key, result, expire=3600)
    return result
```

### 3. Database Optimization

```python
# Bad: N+1 queries
for user in users:
    profile = await db.query("SELECT * FROM profiles WHERE user_id=?", user.id)

# Good: Single batch query
user_ids = [user.id for user in users]
profiles = await db.query(
    "SELECT * FROM profiles WHERE user_id IN (?)",
    user_ids
)
```

### 4. Connection Pooling

```python
# Use connection pools for databases
pool = await asyncpg.create_pool(
    dsn="postgresql://...",
    min_size=10,
    max_size=50
)

# Use session pooling for HTTP
async with aiohttp.ClientSession() as session:
    # Reuse session for multiple requests
    await session.get(url1)
    await session.get(url2)
```

### 5. Lazy Loading

```python
# Don't load everything upfront
class Agent:
    def __init__(self):
        self._expensive_resource = None
    
    async def get_expensive_resource(self):
        if self._expensive_resource is None:
            self._expensive_resource = await load_resource()
        return self._expensive_resource
```

---

## Performance Targets

### Development

- Cognitive loop iteration: < 200ms (avg)
- Planning phase: < 50ms (p95)
- Execution phase: < 100ms (p95)
- Memory operations: < 10ms (p95)

### Production

- Cognitive loop iteration: < 500ms (p95)
- Planning phase: < 200ms (p95)
- Execution phase: < 300ms (p95)
- Memory operations: < 50ms (p95)
- Overall throughput: > 10 tasks/minute

---

## Monitoring Integration

### Prometheus Metrics

Export profiling data to Prometheus:

```python
from xagent.monitoring.metrics import MetricsCollector

metrics = MetricsCollector()

# Record profiling data
profiler = get_profiler()
stats = profiler.get_stats("phase.planning")

metrics.record_cognitive_loop(
    duration=stats['avg'],
    status="success"
)
```

### Grafana Dashboards

Create dashboards to visualize:
- Phase timing trends
- Bottleneck identification
- Percentile distributions
- Throughput over time

---

## Troubleshooting

### High P99 Latency

If p99 latency is much higher than average:
1. Check for outliers in the data
2. Look for external dependencies (APIs, databases)
3. Investigate GC pauses or resource contention
4. Consider adding circuit breakers

### Memory Growth

If memory usage increases over time:
1. Check profiler sample limits (`_max_samples`)
2. Reset profiler periodically in long-running processes
3. Look for memory leaks in profiled code

### Inaccurate Measurements

If measurements seem off:
1. Verify profiler is enabled
2. Check for timer start/stop mismatches
3. Ensure adequate warmup iterations
4. Profile on production-like hardware

---

## Example: Full Profiling Session

```python
import asyncio
from xagent.monitoring.performance import get_profiler, PerformanceBenchmark

async def full_profiling_session():
    # 1. Set up profiler
    profiler = get_profiler()
    profiler.enable()
    profiler.reset()
    
    # 2. Run workload
    print("Running workload...")
    for i in range(10):
        profiler.start_timer("iteration")
        
        # Simulate work
        await asyncio.sleep(0.01)
        profiler.start_timer("sub_task")
        await asyncio.sleep(0.005)
        profiler.stop_timer("sub_task")
        
        profiler.stop_timer("iteration")
    
    # 3. Get summary
    print("\n" + profiler.get_summary_report())
    
    # 4. Identify bottlenecks
    print("\nBottlenecks:")
    for name, duration in profiler.get_bottlenecks(top_n=5):
        print(f"  {name}: {duration*1000:.2f}ms")
    
    # 5. Run benchmark
    print("\nRunning benchmark...")
    benchmark = PerformanceBenchmark()
    
    async def test_operation():
        await asyncio.sleep(0.01)
    
    results = await benchmark.run(test_operation, iterations=50, warmup=5)
    print(benchmark.format_results(results))
    
    # 6. Export data
    data = profiler.export_data()
    print(f"\nExported {len(data['timings'])} timing metrics")

if __name__ == "__main__":
    asyncio.run(full_profiling_session())
```

---

## See Also

- [Observability Guide](./OBSERVABILITY.md)
- [Monitoring Guide](../README.md#monitoring)
- [Performance Demo](../examples/performance_profiling_demo.py)
- [Cognitive Loop Documentation](./COGNITIVE_LOOP.md)

---

**Last Updated**: 2025-11-12  
**Version**: 1.0.0
