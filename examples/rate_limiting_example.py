"""
Example: Using Rate Limiting in X-Agent

This example demonstrates how to use both in-memory and distributed
rate limiting in X-Agent API applications.
"""

import asyncio
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Example 1: In-Memory Rate Limiter (Development/Single Server)
# ============================================================


def setup_inmemory_rate_limiting() -> FastAPI:
    """
    Setup FastAPI application with in-memory rate limiting.
    
    Use this for:
    - Development and testing
    - Single-server deployments
    - Simple use cases
    """
    from xagent.api.rate_limiting import RateLimiter, RateLimitMiddleware

    app = FastAPI(title="X-Agent API with In-Memory Rate Limiting")

    # Create rate limiter
    rate_limiter = RateLimiter(
        default_rate=100,  # 100 requests per minute
        default_burst=120,  # Allow burst of 120 requests
        window_seconds=60,  # 60-second window
    )

    # Customize rate limits per role (optional)
    rate_limiter.rate_limits = {
        "anonymous": (30, 40),  # Stricter for anonymous users
        "user": (100, 120),
        "admin": (1000, 1200),
    }

    # Add middleware
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

    @app.get("/")
    async def root():
        return {"message": "Hello from X-Agent with rate limiting"}

    @app.get("/goals")
    async def list_goals():
        # This endpoint is rate limited
        return {"goals": ["goal1", "goal2"]}

    @app.get("/health")
    async def health():
        # Health checks are automatically exempted from rate limiting
        return {"status": "healthy"}

    return app


# Example 2: Distributed Rate Limiter (Production/Multi-Server)
# ==============================================================


async def setup_distributed_rate_limiting() -> FastAPI:
    """
    Setup FastAPI application with distributed Redis-based rate limiting.
    
    Use this for:
    - Production deployments with multiple servers
    - Kubernetes/containerized environments
    - High-availability setups
    """
    from xagent.api.distributed_rate_limiting import (
        DistributedRateLimitMiddleware,
        RedisRateLimiter,
    )
    from xagent.config import get_settings

    app = FastAPI(title="X-Agent API with Distributed Rate Limiting")

    # Get Redis URL from settings
    settings = get_settings()
    redis_url = settings.redis_url

    # Create distributed rate limiter
    rate_limiter = RedisRateLimiter(
        redis_url=redis_url,
        default_rate=100,
        default_burst=120,
        window_seconds=60,
        key_prefix="xagent:ratelimit",
    )

    # Connect to Redis
    await rate_limiter.connect()

    # Customize rate limits (optional)
    rate_limiter.rate_limits = {
        "anonymous": (60, 70),
        "user": (200, 240),  # Higher limits for production
        "admin": (2000, 2400),
    }

    # Add middleware
    app.add_middleware(DistributedRateLimitMiddleware, rate_limiter=rate_limiter)

    @app.get("/")
    async def root():
        return {"message": "Hello from X-Agent with distributed rate limiting"}

    @app.get("/goals")
    async def list_goals(request: Request):
        # This endpoint is rate limited
        # Rate limit headers are automatically added to response
        return {"goals": ["goal1", "goal2"]}

    @app.get("/admin/stats/{user_id}")
    async def get_user_stats(user_id: str):
        """Admin endpoint to check rate limit stats for a user."""
        stats = await rate_limiter.get_user_stats(f"user:{user_id}")
        if stats:
            return {
                "user": user_id,
                "tokens": stats["tokens"],
                "last_update": stats["last_update"],
            }
        return {"user": user_id, "status": "no data"}

    @app.post("/admin/reset/{user_id}")
    async def reset_user_limit(user_id: str):
        """Admin endpoint to reset rate limit for a user."""
        success = await rate_limiter.reset_user_limit(f"user:{user_id}")
        return {
            "user": user_id,
            "reset": success,
            "message": "Rate limit reset" if success else "Failed to reset",
        }

    @app.on_event("shutdown")
    async def shutdown():
        # Clean up Redis connection
        await rate_limiter.disconnect()

    return app


# Example 3: Custom Rate Limiting Logic
# ======================================


def setup_custom_rate_limiting() -> FastAPI:
    """
    Setup FastAPI application with custom rate limiting logic.
    
    This example shows how to:
    - Apply different costs to different operations
    - Customize rate limits per endpoint
    - Add custom exemptions
    """
    from xagent.api.rate_limiting import RateLimiter

    app = FastAPI(title="X-Agent API with Custom Rate Limiting")

    rate_limiter = RateLimiter(
        default_rate=100,
        default_burst=120,
        window_seconds=60,
    )

    @app.middleware("http")
    async def custom_rate_limit_middleware(request: Request, call_next: Any):
        # Skip rate limiting for certain paths
        exempt_paths = ["/health", "/healthz", "/ready", "/metrics", "/docs"]
        if request.url.path in exempt_paths:
            return await call_next(request)

        # Get user info
        user = getattr(request.state, "user", None)
        client_id = f"user:{user.username}" if user else f"ip:{request.client.host}"
        role = user.role.value.lower() if user and hasattr(user, "role") else "anonymous"

        # Determine cost based on endpoint
        cost = 1.0
        if request.url.path.startswith("/api/goals/create"):
            cost = 5.0  # Creating goals costs more
        elif request.url.path.startswith("/api/search"):
            cost = 3.0  # Search operations cost more
        elif request.method == "POST":
            cost = 2.0  # Write operations cost more

        # Get rate limit for role
        limit, burst = rate_limiter.get_rate_limit_for_role(role)

        # Check rate limit
        allowed, headers = rate_limiter.check_rate_limit(
            key=client_id,
            cost=cost,
            limit=limit,
            burst=burst,
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={
                    **{k: str(v) for k, v in headers.items()},
                    "Retry-After": str(headers["X-RateLimit-Reset"] - int(asyncio.get_event_loop().time())),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        for header, value in headers.items():
            response.headers[header] = str(value)

        return response

    @app.get("/")
    async def root():
        return {"message": "Hello with custom rate limiting"}

    @app.post("/api/goals/create")
    async def create_goal():
        # This endpoint costs 5 tokens
        return {"message": "Goal created", "cost": "5 tokens"}

    @app.get("/api/search")
    async def search():
        # This endpoint costs 3 tokens
        return {"message": "Search results", "cost": "3 tokens"}

    @app.post("/api/data")
    async def post_data():
        # POST operations cost 2 tokens
        return {"message": "Data posted", "cost": "2 tokens"}

    return app


# Example 4: Testing Rate Limiting
# =================================


async def test_rate_limiting():
    """
    Example of how to test rate limiting behavior.
    """
    import httpx

    # Start one of the example apps
    # app = setup_inmemory_rate_limiting()
    # Then run with: uvicorn example:app

    async with httpx.AsyncClient() as client:
        base_url = "http://localhost:8000"

        print("Testing rate limiting...\n")

        # Make requests until rate limited
        for i in range(1, 151):
            try:
                response = await client.get(f"{base_url}/goals")

                if response.status_code == 429:
                    print(f"\n❌ Rate limited after {i-1} requests!")
                    print(f"Retry after: {response.headers.get('Retry-After')} seconds")
                    print(f"Reset time: {response.headers.get('X-RateLimit-Reset')}")
                    break

                remaining = response.headers.get("X-RateLimit-Remaining")
                limit = response.headers.get("X-RateLimit-Limit")

                if i % 10 == 0:
                    print(f"Request {i:3d}: {remaining}/{limit} remaining")

            except Exception as e:
                print(f"Error: {e}")
                break


# Example 5: Monitoring Rate Limiting
# ====================================


async def monitor_rate_limiting():
    """
    Example of monitoring rate limiting metrics.
    """
    from xagent.api.distributed_rate_limiting import RedisRateLimiter

    # Create rate limiter
    rate_limiter = RedisRateLimiter(redis_url="redis://localhost:6379/0")
    await rate_limiter.connect()

    # Monitor specific users
    users = ["alice", "bob", "charlie"]

    print("Rate Limiting Status Dashboard")
    print("=" * 60)

    for user in users:
        stats = await rate_limiter.get_user_stats(f"user:{user}")

        if stats:
            print(f"\nUser: {user}")
            print(f"  Tokens remaining: {stats['tokens']:.2f}")
            print(f"  Last update: {stats['last_update']}")
            print(f"  Status: {'🟢 OK' if stats['tokens'] > 10 else '🟡 Low' if stats['tokens'] > 0 else '🔴 Exhausted'}")
        else:
            print(f"\nUser: {user}")
            print(f"  Status: No activity")

    await rate_limiter.disconnect()


# Main execution
# ==============

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "inmemory":
            # Run with in-memory rate limiting
            app = setup_inmemory_rate_limiting()
            import uvicorn

            print("Starting X-Agent API with in-memory rate limiting...")
            print("Try: curl http://localhost:8000/goals")
            uvicorn.run(app, host="0.0.0.0", port=8000)

        elif mode == "distributed":
            # Run with distributed rate limiting

            async def run_distributed():
                app = await setup_distributed_rate_limiting()
                import uvicorn

                print("Starting X-Agent API with distributed rate limiting...")
                print("Try: curl http://localhost:8000/goals")
                # Note: uvicorn.run doesn't work well with async setup
                # Use: uvicorn example:app instead
                return app

            app = asyncio.run(run_distributed())

        elif mode == "test":
            # Test rate limiting
            asyncio.run(test_rate_limiting())

        elif mode == "monitor":
            # Monitor rate limiting
            asyncio.run(monitor_rate_limiting())

        else:
            print("Usage:")
            print("  python rate_limiting_example.py inmemory   # Run with in-memory rate limiting")
            print("  python rate_limiting_example.py distributed # Run with distributed rate limiting")
            print("  python rate_limiting_example.py test       # Test rate limiting")
            print("  python rate_limiting_example.py monitor    # Monitor rate limiting")
    else:
        print("X-Agent Rate Limiting Examples")
        print("=" * 60)
        print("\nAvailable examples:")
        print("  1. In-Memory Rate Limiting (Development)")
        print("  2. Distributed Rate Limiting (Production)")
        print("  3. Custom Rate Limiting Logic")
        print("  4. Testing Rate Limiting")
        print("  5. Monitoring Rate Limiting")
        print("\nUsage:")
        print("  python rate_limiting_example.py inmemory")
        print("  python rate_limiting_example.py distributed")
        print("  python rate_limiting_example.py test")
        print("  python rate_limiting_example.py monitor")
