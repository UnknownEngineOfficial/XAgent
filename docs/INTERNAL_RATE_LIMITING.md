# Internal Rate Limiting

This document describes the internal rate limiting system for X-Agent, which prevents resource exhaustion from internal operations.

## Overview

While X-Agent has API-level rate limiting to protect against external request floods, it also needs protection against internal resource exhaustion. The internal rate limiting system provides:

- **Cognitive Loop Rate Limiting**: Prevents runaway cognitive loops from consuming excessive resources
- **Tool Call Rate Limiting**: Limits the frequency of tool executions
- **Memory Operation Rate Limiting**: Prevents excessive memory operations

## Architecture

The internal rate limiting system uses a **token bucket algorithm** with multiple independent buckets:

1. **Iteration Bucket (Per Minute)**: Limits cognitive loop iterations per minute
2. **Iteration Bucket (Per Hour)**: Limits cognitive loop iterations per hour
3. **Tool Call Bucket**: Limits tool executions per minute
4. **Memory Operation Bucket**: Limits memory operations per minute

Each bucket:
- Has a maximum capacity (burst size)
- Refills at a constant rate over time
- Operates independently from other buckets

## Configuration

Configure internal rate limiting in `.env` or via environment variables:

```bash
# Enable/disable internal rate limiting
INTERNAL_RATE_LIMITING_ENABLED=true

# Cognitive loop iteration limits
MAX_ITERATIONS_PER_MINUTE=60     # 1 per second average
MAX_ITERATIONS_PER_HOUR=1000     # Long-term limit

# Tool call limits
MAX_TOOL_CALLS_PER_MINUTE=100    # Up to 100 tool calls/minute

# Memory operation limits
MAX_MEMORY_OPS_PER_MINUTE=200    # Up to 200 memory ops/minute

# Cooldown period when limit is hit
RATE_LIMIT_COOLDOWN=5.0          # Wait 5 seconds
```

## Default Limits

The default configuration provides reasonable limits for most use cases:

| Limit | Default Value | Description |
|-------|---------------|-------------|
| Iterations/Minute | 60 | One cognitive loop iteration per second |
| Iterations/Hour | 1000 | Maximum 1000 iterations per hour |
| Tool Calls/Minute | 100 | Up to 100 tool executions per minute |
| Memory Ops/Minute | 200 | Up to 200 memory operations per minute |
| Cooldown | 5.0 seconds | Wait time when limit is exceeded |

## Usage

### Automatic Integration

The rate limiter is automatically integrated into:

1. **Cognitive Loop** (`src/xagent/core/cognitive_loop.py`)
   - Checks rate limit before each iteration
   - Applies cooldown when limit is reached
   - Logs rate limit events

2. **Executor** (`src/xagent/core/executor.py`)
   - Checks rate limit before tool calls
   - Returns rate-limited response when limit is exceeded

3. **Memory Layer** (`src/xagent/memory/memory_layer.py`)
   - Checks rate limit before memory operations
   - Skips operation when limit is exceeded

### Manual Usage

You can also use the rate limiter manually in your code:

```python
from xagent.core.internal_rate_limiting import get_internal_rate_limiter

# Get the global rate limiter instance
limiter = get_internal_rate_limiter()

# Check if an iteration is allowed
if await limiter.check_iteration_limit():
    # Proceed with iteration
    pass
else:
    # Rate limit was applied (cooldown already happened)
    pass

# Check if a tool call is allowed
if await limiter.check_tool_call_limit():
    # Execute tool
    pass

# Check if a memory operation is allowed
if await limiter.check_memory_operation_limit():
    # Perform memory operation
    pass
```

### Custom Configuration

Configure the rate limiter programmatically:

```python
from xagent.core.internal_rate_limiting import (
    RateLimitConfig,
    configure_internal_rate_limiter,
)

# Create custom configuration
config = RateLimitConfig(
    max_iterations_per_minute=30,
    max_iterations_per_hour=500,
    max_tool_calls_per_minute=50,
    max_memory_ops_per_minute=100,
    cooldown_on_limit=2.0,
)

# Configure global rate limiter
limiter = configure_internal_rate_limiter(config)
```

## Monitoring

### Statistics

Get rate limiting statistics:

```python
from xagent.core.internal_rate_limiting import get_internal_rate_limiter

limiter = get_internal_rate_limiter()

# Get overall statistics
stats = limiter.get_stats()
print(f"Total requests: {stats['total_requests']}")
print(f"Blocked requests: {stats['blocked_requests']}")
print(f"Cooldowns applied: {stats['cooldowns']}")

# Get per-bucket statistics
for bucket_name, bucket_stats in stats['buckets'].items():
    print(f"{bucket_name}: {bucket_stats['available']}/{bucket_stats['capacity']} tokens available")
```

### Bucket Status

Check the status of a specific bucket:

```python
limiter = get_internal_rate_limiter()

# Get status of iteration bucket
status = limiter.get_bucket_status("iteration_per_minute")
print(f"Capacity: {status['capacity']}")
print(f"Available: {status['available']}")
print(f"Refill rate: {status['refill_rate']} tokens/sec")
print(f"Time until full: {status['time_until_full']} seconds")
```

### Logging

Rate limit events are logged at WARNING level:

```
WARNING - Cognitive loop iteration rate limit reached. Waiting 2.3s before next iteration.
WARNING - Tool call rate limit reached. Waiting 1.5s.
WARNING - Memory operation rate limit reached. Waiting 0.8s.
```

Each log includes:
- Available tokens
- Wait time
- Bucket information

## Behavior

### When Rate Limit is Reached

1. **Detection**: The rate limiter detects when tokens are insufficient
2. **Cooldown**: A cooldown period is automatically applied (default: 5 seconds or calculated wait time)
3. **Logging**: The event is logged at WARNING level with details
4. **Return**: The check returns `False` to indicate the operation should not proceed
5. **Recovery**: Tokens refill over time based on the configured rate

### Token Refill

Tokens refill continuously based on the configured rate:

- **Iteration Bucket (per minute)**: Refills at `max_iterations_per_minute / 60` tokens per second
- **Iteration Bucket (per hour)**: Refills at `max_iterations_per_hour / 3600` tokens per second
- **Tool Call Bucket**: Refills at `max_tool_calls_per_minute / 60` tokens per second
- **Memory Operation Bucket**: Refills at `max_memory_ops_per_minute / 60` tokens per second

Example: With `max_iterations_per_minute=60`, tokens refill at 1 token per second.

### Independent Buckets

Each operation type has its own independent bucket:

```python
# These operations use different buckets and don't affect each other
await limiter.check_iteration_limit()      # Uses iteration buckets
await limiter.check_tool_call_limit()      # Uses tool call bucket
await limiter.check_memory_operation_limit()  # Uses memory ops bucket
```

## Performance Impact

The internal rate limiting system has minimal performance impact:

- **Memory**: ~1KB per rate limiter instance
- **CPU**: Negligible (simple arithmetic operations)
- **Latency**: <1ms per check (token bucket calculation)

The cooldown mechanism prevents tight loops when rate limits are exceeded, actually reducing overall resource consumption.

## Best Practices

### 1. Tune Limits for Your Use Case

Adjust limits based on your specific needs:

- **High-throughput**: Increase all limits
- **Resource-constrained**: Decrease all limits
- **Burst-heavy**: Increase burst capacity (bucket capacity)

### 2. Monitor Rate Limit Events

Regularly check rate limiting statistics:

```python
stats = limiter.get_stats()
if stats['blocked_requests'] > stats['total_requests'] * 0.1:
    # More than 10% of requests are being blocked
    # Consider increasing limits
    logger.warning("High rate limit block rate detected")
```

### 3. Set Appropriate Cooldowns

- **Short cooldown** (1-2s): For applications needing high responsiveness
- **Medium cooldown** (5s): Balanced approach (default)
- **Long cooldown** (10-30s): For rate limiting as a backpressure mechanism

### 4. Use Multiple Limit Tiers

The dual iteration limits (per minute and per hour) provide both:
- **Short-term burst protection**: Prevents immediate resource exhaustion
- **Long-term sustained load protection**: Prevents cumulative resource exhaustion

### 5. Test Rate Limits

Test rate limiting behavior under load:

```python
import asyncio
from xagent.core.internal_rate_limiting import InternalRateLimiter, RateLimitConfig

async def test_rate_limiting():
    config = RateLimitConfig(
        max_iterations_per_minute=10,
        cooldown_on_limit=0.1,
    )
    limiter = InternalRateLimiter(config)
    
    # Try 20 iterations (should block after 10)
    for i in range(20):
        allowed = await limiter.check_iteration_limit()
        print(f"Iteration {i+1}: {'Allowed' if allowed else 'Blocked'}")
    
    stats = limiter.get_stats()
    print(f"\nStatistics: {stats}")

asyncio.run(test_rate_limiting())
```

## Troubleshooting

### Rate Limits Too Restrictive

**Symptoms**: Frequent rate limit warnings, operations taking too long

**Solutions**:
1. Increase the limits in configuration
2. Reduce the cooldown period
3. Optimize your code to reduce operation frequency

### Rate Limits Not Working

**Symptoms**: No rate limiting despite configuration

**Solutions**:
1. Verify `INTERNAL_RATE_LIMITING_ENABLED=true`
2. Check that the module is imported correctly
3. Ensure the rate limiter is integrated in your code path

### Uneven Rate Limiting

**Symptoms**: Some operations are rate limited more than others

**Solutions**:
1. Check bucket configurations are balanced
2. Review which operations are consuming which buckets
3. Consider adjusting individual bucket limits

## Testing

Run the internal rate limiting tests:

```bash
# Run all internal rate limiting tests
pytest tests/unit/test_internal_rate_limiting.py -v

# Run specific test class
pytest tests/unit/test_internal_rate_limiting.py::TestInternalRateLimiter -v

# Run with coverage
pytest tests/unit/test_internal_rate_limiting.py --cov=xagent.core.internal_rate_limiting
```

## See Also

- [API Rate Limiting](RATE_LIMITING.md) - External API rate limiting
- [Configuration](../README.md#configuration) - General configuration guide
- [Monitoring](OBSERVABILITY.md) - Monitoring and metrics guide
