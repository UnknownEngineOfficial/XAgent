# Rate Limiting Quick Start Guide

Get started with X-Agent's rate limiting in 5 minutes.

## Prerequisites

- Python 3.10+
- Redis (for distributed rate limiting)
- X-Agent installed

## Option 1: In-Memory Rate Limiting (Quick Start)

Perfect for development and testing.

### 1. Install X-Agent

```bash
pip install -e .
```

### 2. Add to Your Application

```python
from fastapi import FastAPI
from xagent.api.rate_limiting import RateLimiter, RateLimitMiddleware

app = FastAPI()

# Create and configure rate limiter
rate_limiter = RateLimiter(
    default_rate=100,      # 100 requests per minute
    default_burst=120,     # Allow burst of 120 requests
    window_seconds=60      # 60-second window
)

# Add middleware
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

@app.get("/api/data")
async def get_data():
    return {"data": "example"}
```

### 3. Run Your Application

```bash
uvicorn myapp:app --reload
```

### 4. Test It

```bash
# Make requests and observe rate limit headers
for i in {1..150}; do
  curl -i http://localhost:8000/api/data | grep "X-RateLimit"
  sleep 0.1
done
```

You'll see headers like:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699123456
```

## Option 2: Distributed Rate Limiting (Production)

For multi-instance production deployments.

### 1. Start Redis

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or using Docker Compose (recommended)
docker-compose up -d redis
```

### 2. Configure Environment

```bash
# .env file
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 3. Add to Your Application

```python
from fastapi import FastAPI
from xagent.api.distributed_rate_limiting import (
    RedisRateLimiter,
    DistributedRateLimitMiddleware
)
from xagent.config import get_settings

app = FastAPI()

# Get settings
settings = get_settings()

# Create distributed rate limiter
rate_limiter = RedisRateLimiter(
    redis_url=settings.redis_url,
    default_rate=100,
    default_burst=120,
    window_seconds=60
)

# Initialize on startup
@app.on_event("startup")
async def startup():
    await rate_limiter.connect()
    print("✅ Rate limiter connected to Redis")

# Clean up on shutdown
@app.on_event("shutdown")
async def shutdown():
    await rate_limiter.disconnect()

# Add middleware
app.add_middleware(DistributedRateLimitMiddleware, rate_limiter=rate_limiter)

@app.get("/api/data")
async def get_data():
    return {"data": "example"}
```

### 4. Run Your Application

```bash
uvicorn myapp:app --reload
```

### 5. Test Distributed Behavior

Start multiple instances:

```bash
# Terminal 1
uvicorn myapp:app --port 8000

# Terminal 2
uvicorn myapp:app --port 8001

# Terminal 3 - Test both instances
curl http://localhost:8000/api/data  # Request to instance 1
curl http://localhost:8001/api/data  # Request to instance 2
# Rate limits are shared across both instances!
```

## Customizing Rate Limits

### By User Role

```python
# Customize rate limits per role
rate_limiter.rate_limits = {
    "anonymous": (30, 40),      # 30 req/min, burst 40
    "user": (100, 120),          # 100 req/min, burst 120
    "admin": (1000, 1200),       # 1000 req/min, burst 1200
}
```

### By Endpoint

```python
from fastapi import Request

@app.middleware("http")
async def custom_rate_limit(request: Request, call_next):
    # Different costs for different endpoints
    cost = 1.0
    if request.url.path.startswith("/api/expensive"):
        cost = 5.0  # More expensive operations
    
    # Apply rate limiting with custom cost
    # ... (see examples/rate_limiting_example.py for full code)
    
    response = await call_next(request)
    return response
```

## Monitoring

### Check Rate Limit Status

Response headers show current status:

```bash
$ curl -i http://localhost:8000/api/data

HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699123456
X-RateLimit-Window: 60
```

### Handle Rate Limit Exceeded

When rate limited, you'll receive:

```bash
$ curl -i http://localhost:8000/api/data

HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1699123500
Retry-After: 44

{"detail": "Rate limit exceeded. Please try again later."}
```

### Admin Operations (Distributed Only)

Get user stats:
```python
@app.get("/admin/stats/{user_id}")
async def get_stats(user_id: str):
    stats = await rate_limiter.get_user_stats(f"user:{user_id}")
    return stats
```

Reset user limit:
```python
@app.post("/admin/reset/{user_id}")
async def reset_limit(user_id: str):
    success = await rate_limiter.reset_user_limit(f"user:{user_id}")
    return {"reset": success}
```

## Docker Compose Setup

Complete setup with Redis:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0
    depends_on:
      - redis
    command: uvicorn myapp:app --host 0.0.0.0 --port 8000

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

Run with:
```bash
docker-compose up -d
```

## Testing Your Setup

### Python Test Script

```python
import asyncio
import httpx

async def test_rate_limit():
    async with httpx.AsyncClient() as client:
        for i in range(1, 151):
            response = await client.get("http://localhost:8000/api/data")
            
            if response.status_code == 429:
                print(f"✅ Rate limited after {i-1} requests")
                print(f"Retry after: {response.headers['Retry-After']}s")
                break
            
            if i % 10 == 0:
                remaining = response.headers["X-RateLimit-Remaining"]
                print(f"Request {i}: {remaining} remaining")

asyncio.run(test_rate_limit())
```

### Bash Test Script

```bash
#!/bin/bash
for i in {1..150}; do
  response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/data)
  status=$(echo "$response" | tail -n1)
  
  if [ "$status" = "429" ]; then
    echo "Rate limited after $((i-1)) requests"
    break
  fi
  
  if [ $((i % 10)) -eq 0 ]; then
    echo "Request $i: Status $status"
  fi
  
  sleep 0.1
done
```

## Troubleshooting

### Rate Limiting Not Working

1. **Check middleware is added**:
   ```python
   app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
   ```

2. **Verify endpoints aren't exempted**:
   Health check endpoints (`/health`, `/healthz`, `/ready`, `/metrics`) are automatically exempted.

3. **Check Redis connection** (distributed only):
   ```bash
   redis-cli ping  # Should return PONG
   ```

### Redis Connection Errors

1. **Verify Redis is running**:
   ```bash
   docker ps | grep redis
   ```

2. **Check Redis URL**:
   ```bash
   echo $REDIS_HOST
   redis-cli -h $REDIS_HOST ping
   ```

3. **Check logs**:
   ```bash
   docker logs redis
   ```

### Rate Limits Too Restrictive

Increase limits:
```python
rate_limiter = RateLimiter(
    default_rate=500,      # Increase from 100
    default_burst=600,     # Increase from 120
    window_seconds=60
)
```

## Next Steps

- Read the full [Rate Limiting Documentation](RATE_LIMITING.md)
- Explore [Rate Limiting Examples](../examples/rate_limiting_example.py)
- Configure [Monitoring and Alerts](OBSERVABILITY.md)
- Review [Production Best Practices](../README.md#production-deployment)

## Quick Reference

### Rate Limit Headers

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests per window |
| `X-RateLimit-Remaining` | Requests remaining in window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |
| `X-RateLimit-Window` | Window duration in seconds |
| `Retry-After` | Seconds until retry (on 429 only) |

### Default Rate Limits

| Role | Requests/Min | Burst |
|------|-------------|-------|
| Anonymous | 60 | 70 |
| User | 100 | 120 |
| Admin | 1000 | 1200 |

### Exempted Endpoints

- `/health`
- `/healthz`
- `/ready`
- `/metrics`

## Support

Need help? Check:
- [GitHub Issues](https://github.com/UnknownEngineOfficial/X-Agent/issues)
- [Documentation](https://github.com/UnknownEngineOfficial/X-Agent/docs)
- [Examples](../examples/)
