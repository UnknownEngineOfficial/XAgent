# X-Agent Caching Guide

This guide covers the Redis-based caching layer for X-Agent, designed to optimize memory usage and improve performance.

## Overview

The caching layer provides a high-performance, Redis-based solution for caching frequently accessed data. This reduces database queries, improves response times, and optimizes resource usage.

## Architecture

```
┌──────────────┐
│  X-Agent API │  Application layer
└──────┬───────┘
       │
       │ Cache requests
       ▼
┌──────────────┐
│ RedisCache   │  Caching layer
└──────┬───────┘
       │
       │ Redis protocol
       ▼
┌──────────────┐
│    Redis     │  In-memory data store
└──────────────┘
```

## Features

- **Async Operations**: Full async/await support for high performance
- **Automatic Serialization**: JSON-based serialization/deserialization
- **TTL Support**: Configurable time-to-live for each cache entry
- **Bulk Operations**: Efficient batch get/set operations
- **Pattern Deletion**: Delete multiple keys matching a pattern
- **Cache Statistics**: Built-in metrics for monitoring
- **Decorator Support**: Easy-to-use `@cached` decorator
- **Error Handling**: Graceful degradation when cache is unavailable

## Quick Start

### Basic Usage

```python
from xagent.memory.cache import RedisCache, CacheConfig

# Initialize cache
cache = RedisCache("redis://localhost:6379/0")
await cache.connect()

# Set a value
await cache.set("goals", "goal_123", {"title": "Complete task", "status": "active"}, ttl=300)

# Get a value
goal = await cache.get("goals", "goal_123")

# Delete a value
await cache.delete("goals", "goal_123")

# Clean up
await cache.disconnect()
```

### Using the Decorator

```python
from xagent.memory.cache import cached, CacheConfig

class GoalService:
    def __init__(self, cache: RedisCache):
        self._cache = cache
    
    @cached(category="goals", ttl=CacheConfig.MEDIUM_TTL)
    async def get_goal(self, goal_id: str):
        # This will be cached automatically
        return await self.db.query(Goal).filter_by(id=goal_id).first()
```

## Cache Categories

Use consistent category names to organize cached data:

| Category | Description | TTL | Usage |
|----------|-------------|-----|-------|
| `goal` | Goal objects | 5 min | Individual goals |
| `agent_state` | Agent state snapshots | 1 min | Current agent state |
| `memory` | Memory entries | 10 min | Episodic memory |
| `metric` | Performance metrics | 1 hour | Monitoring data |
| `plan` | Planning results | 5 min | Cached plans |
| `tool_result` | Tool execution results | 10 min | Idempotent tool calls |

## TTL Configuration

Choose appropriate TTL values based on data characteristics:

```python
from xagent.memory.cache import CacheConfig

# Predefined TTL values
CacheConfig.SHORT_TTL    # 60 seconds - frequently changing data
CacheConfig.DEFAULT_TTL  # 300 seconds (5 min) - standard caching
CacheConfig.MEDIUM_TTL   # 600 seconds (10 min) - moderately stable data
CacheConfig.LONG_TTL     # 3600 seconds (1 hour) - stable data
```

## Advanced Features

### Bulk Operations

```python
# Get multiple values at once
goals = await cache.get_many("goals", ["goal_1", "goal_2", "goal_3"])

# Set multiple values at once
await cache.set_many(
    "goals",
    {
        "goal_1": {"title": "Task 1"},
        "goal_2": {"title": "Task 2"},
    },
    ttl=300
)
```

### Pattern Deletion

```python
# Delete all goals for a specific user
await cache.delete_pattern("goals", "user:123:*")

# Delete all expired plans
await cache.delete_pattern("plans", "expired:*")
```

### Counters

```python
# Increment a counter
count = await cache.increment("metrics", "api_calls", amount=1)

# Decrement (use negative amount)
count = await cache.increment("metrics", "queue_size", amount=-1)
```

### Cache Statistics

```python
# Get cache performance metrics
stats = await cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
print(f"Memory usage: {stats['used_memory']}")
print(f"Total commands: {stats['total_commands']}")
```

## Integration with X-Agent Components

### Goal Engine

```python
from xagent.memory.cache import RedisCache, CacheConfig, cached

class GoalEngine:
    def __init__(self, cache: RedisCache):
        self._cache = cache
    
    @cached(category=CacheConfig.PREFIX_GOAL, ttl=CacheConfig.DEFAULT_TTL)
    async def get_goal(self, goal_id: str):
        """Get goal with automatic caching."""
        return await self._fetch_goal_from_db(goal_id)
    
    async def update_goal(self, goal_id: str, updates: dict):
        """Update goal and invalidate cache."""
        await self._update_goal_in_db(goal_id, updates)
        await self._cache.delete(CacheConfig.PREFIX_GOAL, goal_id)
```

### Memory Layer

```python
class MemoryLayer:
    def __init__(self, cache: RedisCache):
        self._cache = cache
    
    async def get_recent_memories(self, limit: int = 10):
        """Get recent memories with caching."""
        cache_key = f"recent:{limit}"
        
        # Check cache
        memories = await self._cache.get(CacheConfig.PREFIX_MEMORY, cache_key)
        if memories:
            return memories
        
        # Fetch from database
        memories = await self._fetch_from_db(limit)
        
        # Cache for 1 minute
        await self._cache.set(
            CacheConfig.PREFIX_MEMORY,
            cache_key,
            memories,
            ttl=CacheConfig.SHORT_TTL
        )
        
        return memories
```

### Planner

```python
class Planner:
    def __init__(self, cache: RedisCache):
        self._cache = cache
    
    async def get_plan(self, goal: str):
        """Get cached plan if available."""
        # Generate cache key from goal
        cache_key = hashlib.md5(goal.encode()).hexdigest()
        
        # Try cache first
        plan = await self._cache.get(CacheConfig.PREFIX_PLAN, cache_key)
        if plan:
            return plan
        
        # Generate new plan
        plan = await self._generate_plan(goal)
        
        # Cache for 5 minutes
        await self._cache.set(
            CacheConfig.PREFIX_PLAN,
            cache_key,
            plan,
            ttl=CacheConfig.DEFAULT_TTL
        )
        
        return plan
```

## Configuration

### Redis URL Format

```python
# Local Redis
redis_url = "redis://localhost:6379/0"

# With authentication
redis_url = "redis://:password@localhost:6379/0"

# Remote Redis
redis_url = "redis://redis.example.com:6379/0"

# Redis Cluster
redis_url = "redis://node1:6379,node2:6379,node3:6379/0"
```

### Environment Variables

```bash
# Set in .env file or environment
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_password
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50
```

### Application Setup

```python
from xagent.config import settings
from xagent.memory.cache import RedisCache

# Initialize in application startup
cache = RedisCache(settings.redis_url)
await cache.connect()

# Store in application state
app.state.cache = cache

# Use in request handlers
@app.get("/goals/{goal_id}")
async def get_goal(goal_id: str, request: Request):
    cache = request.app.state.cache
    
    # Try cache first
    goal = await cache.get("goals", goal_id)
    if goal:
        return goal
    
    # Fetch from database
    goal = await fetch_goal(goal_id)
    
    # Cache for 5 minutes
    await cache.set("goals", goal_id, goal, ttl=300)
    
    return goal
```

## Best Practices

### 1. Cache Invalidation

Always invalidate cache when data changes:

```python
async def update_goal(goal_id: str, updates: dict):
    # Update database
    await db.update_goal(goal_id, updates)
    
    # Invalidate cache
    await cache.delete("goals", goal_id)
    
    # Also invalidate related caches
    await cache.delete_pattern("goals", f"user:{user_id}:*")
```

### 2. Appropriate TTL

Choose TTL based on data characteristics:

- **Frequently changing**: 1 minute or less
- **Moderately stable**: 5-10 minutes
- **Rarely changing**: 1 hour or more
- **Never expires**: Use database instead

### 3. Cache Keys

Use descriptive, hierarchical cache keys:

```python
# Good
cache_key = f"user:{user_id}:goals:active"
cache_key = f"agent:{agent_id}:state:latest"

# Bad
cache_key = "data"
cache_key = "x123"
```

### 4. Error Handling

Cache should degrade gracefully:

```python
try:
    value = await cache.get("goals", goal_id)
    if value:
        return value
except Exception as e:
    logger.warning(f"Cache error: {e}")
    # Continue without cache

# Fetch from database as fallback
return await db.fetch(goal_id)
```

### 5. Monitoring

Monitor cache performance regularly:

```python
# Log cache statistics periodically
async def log_cache_stats():
    stats = await cache.get_stats()
    logger.info(
        f"Cache stats - Hit rate: {stats['hit_rate']}%, "
        f"Memory: {stats['used_memory']}, "
        f"Clients: {stats['connected_clients']}"
    )
```

## Performance Optimization

### 1. Connection Pooling

Redis connection pooling is enabled by default with max 50 connections.

### 2. Pipeline Operations

Use pipelines for multiple operations:

```python
# Instead of multiple individual sets
for i in range(100):
    await cache.set("items", f"item_{i}", data[i])

# Use set_many for better performance
await cache.set_many("items", {f"item_{i}": data[i] for i in range(100)})
```

### 3. Batch Gets

Fetch multiple items at once:

```python
# Efficient
goals = await cache.get_many("goals", goal_ids)

# Inefficient
goals = {}
for goal_id in goal_ids:
    goals[goal_id] = await cache.get("goals", goal_id)
```

### 4. Compression

For large objects, consider compression:

```python
import gzip
import json

def compress(data):
    json_str = json.dumps(data)
    return gzip.compress(json_str.encode())

def decompress(data):
    json_str = gzip.decompress(data).decode()
    return json.loads(json_str)
```

## Monitoring

### Key Metrics

Monitor these cache metrics:

- **Hit Rate**: Percentage of requests served from cache
- **Memory Usage**: Redis memory consumption
- **Eviction Rate**: How often keys are evicted
- **Connection Count**: Number of active connections
- **Command Rate**: Commands per second

### Prometheus Metrics

Add cache metrics to Prometheus:

```python
from prometheus_client import Counter, Gauge, Histogram

cache_hits = Counter('cache_hits_total', 'Total cache hits', ['category'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['category'])
cache_errors = Counter('cache_errors_total', 'Total cache errors', ['operation'])
cache_latency = Histogram('cache_operation_seconds', 'Cache operation latency', ['operation'])
```

### Health Checks

Include cache status in health checks:

```python
@app.get("/health")
async def health_check():
    cache_healthy = False
    try:
        await cache._client.ping()
        cache_healthy = True
    except:
        pass
    
    return {
        "status": "healthy" if cache_healthy else "degraded",
        "cache": "connected" if cache_healthy else "disconnected"
    }
```

## Troubleshooting

### High Memory Usage

1. Check for large objects being cached
2. Review TTL values
3. Implement LRU eviction policy
4. Consider compression for large objects

### Low Hit Rate

1. TTL might be too short
2. Cache keys might not be consistent
3. Data might be too dynamic
4. Review cache invalidation logic

### Connection Errors

1. Verify Redis is running: `redis-cli ping`
2. Check network connectivity
3. Verify credentials
4. Check connection limits

### Slow Performance

1. Enable connection pooling
2. Use bulk operations
3. Check Redis server performance
4. Consider Redis Cluster for scaling

## Testing

### Unit Tests

```python
import pytest
from xagent.memory.cache import RedisCache

@pytest.mark.asyncio
async def test_cache_operations():
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()
    
    # Test set and get
    await cache.set("test", "key1", {"value": 123}, ttl=60)
    result = await cache.get("test", "key1")
    assert result == {"value": 123}
    
    # Test delete
    await cache.delete("test", "key1")
    result = await cache.get("test", "key1")
    assert result is None
    
    await cache.disconnect()
```

### Integration Tests

Test cache with actual Redis instance in CI/CD.

## Migration Guide

### From No Cache

1. Add Redis to infrastructure
2. Initialize RedisCache in application
3. Gradually add caching to hot paths
4. Monitor performance improvements

### From Different Cache

1. Deploy Redis alongside existing cache
2. Implement dual-write to both caches
3. Compare performance
4. Switch read traffic to Redis
5. Remove old cache

## References

- [Redis Documentation](https://redis.io/documentation)
- [redis-py Documentation](https://redis-py.readthedocs.io/)
- [Caching Best Practices](https://redis.io/docs/manual/patterns/)

## Support

For issues with caching:
- GitHub Issues: https://github.com/UnknownEngineOfficial/X-Agent/issues
- Documentation: https://github.com/UnknownEngineOfficial/X-Agent/docs
