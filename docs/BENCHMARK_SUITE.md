# X-Agent Benchmark Suite

## Overview

Comprehensive performance benchmarking suite for measuring and tracking X-Agent system performance over time.

## Quick Start

```bash
# Run all benchmarks
python scripts/run_benchmarks.py

# Save as baseline
python scripts/run_benchmarks.py --save-baseline

# Compare with baseline
python scripts/run_benchmarks.py --compare benchmark_results/baseline.json
```

## Benchmark Categories

### 1. Cognitive Loop (Target: <50ms iteration)
- Single iteration latency
- Loop throughput (>10 iter/sec)
- End-to-end workflow

### 2. Memory Operations (Target: >100 writes/sec)
- Write performance
- Read latency (<10ms)
- Query efficiency

### 3. Planning (Target: <100ms simple, <500ms complex)
- Planning latency
- Goal decomposition
- LLM integration overhead

### 4. Action Execution (Target: <20ms simple actions)
- Execution latency
- Tool orchestration
- Sandbox performance

### 5. Goal Engine (Target: >1000 goals/sec)
- Creation performance
- Query efficiency (<1ms)
- Hierarchical operations

### 6. Stress Testing (Target: 100+ concurrent ops)
- Concurrent operations
- Long-running stability
- Resource cleanup

## Performance Targets

| Component | Target | Critical |
|-----------|--------|----------|
| Loop Iteration | <50ms | <100ms |
| Memory Write | >100/sec | >50/sec |
| Memory Read | <10ms | <50ms |
| Planning (Simple) | <100ms | <500ms |
| Planning (Complex) | <500ms | <2s |
| Action Execution | <20ms | <100ms |
| Goal Creation | >1000/sec | >100/sec |
| Goal Query | <1ms | <10ms |

## Running Benchmarks

### With pytest

```bash
# All benchmarks
pytest tests/performance/ --benchmark-only

# Specific group
pytest tests/performance/ -k "cognitive_loop" --benchmark-only

# With JSON output
pytest tests/performance/ --benchmark-only \
    --benchmark-json=results.json
```

### With Script

```bash
# Basic run
python scripts/run_benchmarks.py

# With comparison
python scripts/run_benchmarks.py \
    --compare benchmark_results/baseline.json

# Fail on >10% regression
python scripts/run_benchmarks.py \
    --compare benchmark_results/baseline.json \
    --fail-threshold=10
```

## CI/CD Integration

```yaml
# .github/workflows/benchmarks.yml
name: Performance Benchmarks

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -e ".[dev]"
      
      - name: Run benchmarks
        run: |
          python scripts/run_benchmarks.py \
            --compare benchmark_results/baseline.json
      
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmark_results/
```

## Interpreting Results

### Good Performance

✅ Low standard deviation (<10% of mean)  
✅ Min/Max close to Mean  
✅ High OPS (operations per second)  
✅ Meets or beats targets

### Warning Signs

⚠️ High standard deviation (>20%)  
⚠️ Large Min/Max gap  
⚠️ Degrading OPS over time  
⚠️ Exceeds critical thresholds

## Optimization Tips

### Cognitive Loop

```python
# Use batch operations
plans = await asyncio.gather(*[planner.plan(g) for g in goals])

# Cache expensive computations
@cached(ttl=300)
async def get_context():
    return context
```

### Memory

```python
# Batch writes
await memory.add_memories_batch(memories)

# Limit queries
memories = await memory.get_recent_memories(limit=10)
```

### Planning

```python
# Use appropriate complexity
plan = await planner.plan(goal, complexity="low")

# Cache similar plans
if cache_key in plan_cache:
    return plan_cache[cache_key]
```

### Execution

```python
# Parallel execution
results = await asyncio.gather(
    executor.execute(action1),
    executor.execute(action2)
)

# Timeouts
result = await asyncio.wait_for(action, timeout=30)
```

## Monitoring

### Prometheus Metrics

```
xagent_cognitive_loop_iteration_duration_seconds
xagent_memory_operation_duration_seconds
xagent_planning_duration_seconds
xagent_action_execution_duration_seconds
```

### Grafana Dashboard

Import: `config/grafana/performance_dashboard.json`

## Troubleshooting

### Slow Benchmarks

- Reduce iterations: `--benchmark-min-rounds=3`
- Run specific tests: `-k "test_name"`
- Mock expensive dependencies

### Inconsistent Results

- Close other applications
- Check system load
- Run at off-peak times
- Use dedicated hardware

### False Regressions

- Update baseline if intentional
- Check environment differences
- Review threshold (10% default)

## Best Practices

1. ✅ Run benchmarks before releases
2. ✅ Establish baselines early
3. ✅ Set realistic targets
4. ✅ Document changes
5. ✅ Automate checks in CI/CD
6. ✅ Profile before optimizing
7. ✅ Test in production-like env
8. ✅ Monitor in production

---

**Version**: 1.0  
**Last Updated**: 2025-11-12  
**Maintained By**: X-Agent Team
