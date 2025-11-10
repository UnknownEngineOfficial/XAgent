# Rate Limiting in X-Agent

X-Agent provides two rate limiting implementations to control API access and protect the system from abuse.

## Overview

Rate limiting is essential for:
- Preventing API abuse and DDoS attacks
- Ensuring fair resource allocation among users
- Managing system load and maintaining performance
- Enforcing usage quotas for different user tiers

## Available Implementations

### 1. In-Memory Rate Limiter (Basic)

**Location**: `src/xagent/api/rate_limiting.py`

A simple, in-memory token bucket rate limiter suitable for single-instance deployments.

**Features**:
- Token bucket algorithm
- Role-based rate limits (anonymous, user, admin)
- Automatic token replenishment
- Memory cleanup for old entries

**Use Cases**:
- Development and testing
- Single-server deployments
- Simple use cases without high availability requirements

**Example Usage**:

```python
from xagent.api.rate_limiting import RateLimiter, RateLimitMiddleware

# Create rate limiter
rate_limiter = RateLimiter(
    default_rate=100,      # 100 requests per minute
    default_burst=120,     # Allow burst of 120 requests
    window_seconds=60      # 60-second window
)

# Add to FastAPI app
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
```

### 2. Distributed Rate Limiter (Production)

**Location**: `src/xagent/api/distributed_rate_limiting.py`

A Redis-based distributed rate limiter designed for multi-instance production deployments.

**Features**:
- Redis-backed distributed storage
- Atomic operations using Lua scripts
- Works across multiple server instances
- Automatic key expiration
- Graceful fallback when Redis is unavailable
- Per-user statistics and management
- Rate limit reset capability

**Use Cases**:
- Production deployments with multiple servers
- Kubernetes/containerized environments
- High-availability setups
- Systems requiring consistent rate limiting across instances

**Example Usage**:

```python
from xagent.api.distributed_rate_limiting import (
    RedisRateLimiter,
    DistributedRateLimitMiddleware
)

# Create distributed rate limiter
rate_limiter = RedisRateLimiter(
    redis_url="redis://localhost:6379/0",
    default_rate=100,
    default_burst=120,
    window_seconds=60
)

# Connect to Redis
await rate_limiter.connect()

# Add to FastAPI app
app.add_middleware(DistributedRateLimitMiddleware, rate_limiter=rate_limiter)
```

## Rate Limits by Role

Both implementations support role-based rate limiting:

| Role | Requests/Minute | Burst Limit |
|------|----------------|-------------|
| Anonymous | 60 | 70 |
| User | 100 | 120 |
| Admin | 1000 | 1200 |

These limits can be customized by modifying the `rate_limits` dictionary in the rate limiter instance.

## Token Bucket Algorithm

Both implementations use the token bucket algorithm:

1. **Bucket Initialization**: Each user/IP starts with a full bucket of tokens
2. **Token Consumption**: Each request consumes 1 token (customizable)
3. **Token Replenishment**: Tokens are added at a constant rate (requests per window)
4. **Burst Handling**: The bucket has a maximum capacity (burst limit)
5. **Request Blocking**: Requests are blocked when the bucket is empty

## Rate Limit Headers

When rate limiting is active, the following headers are added to responses:

- `X-RateLimit-Limit`: Maximum requests allowed in the time window
- `X-RateLimit-Remaining`: Number of requests remaining
- `X-RateLimit-Reset`: Unix timestamp when the rate limit resets
- `X-RateLimit-Window`: Time window in seconds
- `Retry-After`: (Only on 429 responses) Seconds until the rate limit resets

## HTTP Status Codes

- `200 OK`: Request successful, within rate limits
- `429 Too Many Requests`: Rate limit exceeded

## Configuration

### Environment Variables

Configure Redis connection for distributed rate limiting:

```bash
# Redis configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

### Docker Compose

Example configuration in `docker-compose.yml`:

```yaml
services:
  xagent-api:
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

## Advanced Features (Distributed Limiter Only)

### User Statistics

Get current rate limit statistics for a user:

```python
stats = await rate_limiter.get_user_stats("user:john")
print(f"Tokens: {stats['tokens']}")
print(f"Last update: {stats['last_update']}")
```

### Reset User Limit

Manually reset rate limit for a specific user (admin operation):

```python
await rate_limiter.reset_user_limit("user:john")
```

### Custom Cost per Request

Some operations may consume more tokens:

```python
allowed, headers = await rate_limiter.check_rate_limit(
    key="user:john",
    cost=5.0  # This request costs 5 tokens
)
```

## Monitoring

Rate limiting metrics can be monitored through:

1. **Logs**: Rate limit violations are logged with context
2. **Headers**: Response headers show current limits and remaining quota
3. **Redis**: Direct inspection of Redis keys (distributed limiter only)

### Example Log Entry

```
2025-11-10 18:00:00 [warning] Rate limit exceeded for ip:203.0.113.1 (role: anonymous)
  client_id: ip:203.0.113.1
  role: anonymous
  path: /api/goals
```

## Best Practices

### 1. Choose the Right Implementation

- **Development/Testing**: Use in-memory rate limiter
- **Single Server**: Use in-memory rate limiter
- **Production/Multi-Server**: Use distributed rate limiter

### 2. Configure Appropriate Limits

- Set limits based on expected usage patterns
- Allow higher limits for authenticated users
- Use burst limits to handle traffic spikes
- Monitor and adjust based on actual usage

### 3. Handle Rate Limit Responses

Client applications should:
- Check for 429 status codes
- Read `Retry-After` header
- Implement exponential backoff
- Show user-friendly error messages

### 4. Exempt Health Checks

Both implementations automatically exempt these endpoints:
- `/health`
- `/healthz`
- `/ready`
- `/metrics`

### 5. Monitor Redis Health (Distributed Only)

- Ensure Redis is highly available
- Monitor Redis connection health
- The limiter gracefully allows requests if Redis is down (fail-open)

## Testing

### Unit Tests

Both implementations have comprehensive test suites:

```bash
# Test in-memory rate limiter
pytest tests/unit/test_rate_limiting.py -v

# Test distributed rate limiter
pytest tests/unit/test_distributed_rate_limiting.py -v
```

### Integration Testing

Test rate limiting in your application:

```python
import httpx
import asyncio

async def test_rate_limiting():
    async with httpx.AsyncClient() as client:
        # Make requests until rate limited
        for i in range(150):
            response = await client.get("http://localhost:8000/api/goals")
            
            if response.status_code == 429:
                print(f"Rate limited after {i} requests")
                print(f"Retry after: {response.headers['Retry-After']} seconds")
                break
            
            print(f"Request {i}: {response.headers['X-RateLimit-Remaining']} remaining")
```

## Migration Guide

### From In-Memory to Distributed

1. Install Redis:
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. Update your application code:
   ```python
   # Before
   from xagent.api.rate_limiting import RateLimiter, RateLimitMiddleware
   
   # After
   from xagent.api.distributed_rate_limiting import (
       RedisRateLimiter as RateLimiter,
       DistributedRateLimitMiddleware as RateLimitMiddleware
   )
   ```

3. Initialize with Redis URL:
   ```python
   rate_limiter = RateLimiter(
       redis_url="redis://localhost:6379/0",
       # ... other parameters
   )
   await rate_limiter.connect()
   ```

4. Update deployment configuration to include Redis

## Troubleshooting

### Issue: Rate Limiting Not Working

**Symptoms**: All requests pass through without rate limiting

**Solutions**:
1. Check middleware is added to FastAPI app
2. Verify endpoints are not in the exempt list
3. Check Redis connection (distributed limiter)
4. Review logs for errors

### Issue: Redis Connection Errors (Distributed)

**Symptoms**: Connection errors in logs

**Solutions**:
1. Verify Redis is running: `redis-cli ping`
2. Check Redis URL configuration
3. Ensure network connectivity
4. Check Redis authentication if configured

### Issue: Too Restrictive Limits

**Symptoms**: Legitimate users getting rate limited

**Solutions**:
1. Review and increase rate limits
2. Increase burst capacity
3. Implement user-specific limits
4. Consider longer time windows

### Issue: Memory Growth (In-Memory Only)

**Symptoms**: Increasing memory usage over time

**Solutions**:
1. Use distributed limiter for production
2. Call `cleanup_old_entries()` periodically
3. Set shorter max_age_seconds for cleanup

## Performance Considerations

### In-Memory Limiter

- **Throughput**: Very high (no I/O)
- **Latency**: Sub-millisecond
- **Memory**: O(n) where n is number of unique clients
- **Scalability**: Single instance only

### Distributed Limiter

- **Throughput**: High (Redis is fast)
- **Latency**: 1-5ms (depends on Redis)
- **Memory**: Stored in Redis
- **Scalability**: Horizontal (multiple instances)

## Security Considerations

1. **DDoS Protection**: Rate limiting helps mitigate DDoS attacks
2. **Credential Stuffing**: Limits login attempt frequency
3. **Data Scraping**: Prevents automated data harvesting
4. **Resource Exhaustion**: Protects against resource exhaustion

## Future Enhancements

Potential improvements for future versions:

1. **Dynamic Rate Limits**: Adjust limits based on system load
2. **IP Whitelisting**: Bypass rate limiting for trusted IPs
3. **Custom Rate Limit Strategies**: Per-endpoint limits
4. **Advanced Analytics**: Detailed usage statistics
5. **Machine Learning**: Detect anomalous patterns

## References

- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [HTTP Status Code 429](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)
- [Redis Rate Limiting Patterns](https://redis.io/docs/manual/patterns/rate-limiting/)

## Support

For issues or questions:
- GitHub Issues: https://github.com/UnknownEngineOfficial/X-Agent/issues
- Documentation: https://github.com/UnknownEngineOfficial/X-Agent/docs
