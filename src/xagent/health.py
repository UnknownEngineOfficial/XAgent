"""
Health Check Module for X-Agent

Provides health and readiness endpoints for monitoring and orchestration.
Can be run as a standalone HTTP server or integrated into existing APIs.
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from xagent.config import Settings

logger = logging.getLogger(__name__)

# Global settings instance
_settings = Settings()


class HealthStatus(str, Enum):
    """Health check status values"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """
    Health check coordinator for X-Agent.

    Checks various dependencies and system components.
    """

    def __init__(self) -> None:
        self.start_time = datetime.now(timezone.utc)

    def check_redis(self) -> tuple[bool, str | None]:
        """Check Redis connectivity"""
        try:
            import redis

            if not _settings.redis_host:
                return True, "Redis not configured (optional)"

            client = redis.Redis(
                host=_settings.redis_host,
                port=_settings.redis_port,
                db=_settings.redis_db,
                password=_settings.redis_password if _settings.redis_password else None,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            client.ping()
            return True, None
        except ImportError:
            return True, "Redis client not installed (optional)"
        except Exception as e:
            return False, f"Redis connection failed: {str(e)}"

    def check_postgres(self) -> tuple[bool, str | None]:
        """Check PostgreSQL connectivity"""
        try:
            import psycopg

            if not _settings.postgres_host:
                return True, "PostgreSQL not configured (optional)"

            conn_str = _settings.postgres_url
            with psycopg.connect(conn_str, connect_timeout=2) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True, None
        except ImportError:
            return True, "PostgreSQL client not installed (optional)"
        except Exception as e:
            return False, f"PostgreSQL connection failed: {str(e)}"

    def check_chromadb(self) -> tuple[bool, str | None]:
        """Check ChromaDB connectivity"""
        try:
            import chromadb

            # ChromaDB client initialization is lightweight
            # Just instantiating the client verifies the library is available
            # and can be imported without errors
            chromadb.Client()
            return True, None
        except ImportError:
            return True, "ChromaDB not installed (optional)"
        except Exception as e:
            # ChromaDB failures are non-critical
            return True, f"ChromaDB warning: {str(e)}"

    def get_health(self) -> dict[str, Any]:
        """
        Get comprehensive health status.

        Returns:
            Health status dictionary with component checks
        """
        checks = {
            "redis": self.check_redis(),
            "postgres": self.check_postgres(),
            "chromadb": self.check_chromadb(),
        }

        # Determine overall status
        failed = [name for name, (ok, _) in checks.items() if not ok]

        if not failed:
            status = HealthStatus.HEALTHY
        else:
            status = HealthStatus.UNHEALTHY

        uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime_seconds,
            "checks": {
                name: {"status": "ok" if ok else "failed", "message": msg}
                for name, (ok, msg) in checks.items()
            },
            "version": "0.1.0",
        }

    def get_readiness(self) -> dict[str, Any]:
        """
        Get readiness status (ready to serve traffic).

        Returns:
            Readiness status dictionary
        """
        health = self.get_health()

        # Service is ready if status is healthy or degraded
        ready = health["status"] in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]

        return {
            "ready": ready,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": health["status"],
        }

    def get_liveness(self) -> dict[str, Any]:
        """
        Get liveness status (process is alive).

        Returns:
            Liveness status dictionary
        """
        return {
            "alive": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
        }


def main() -> None:
    """
    Run health check as standalone HTTP server.

    Provides endpoints:
    - GET /health - Comprehensive health check
    - GET /healthz - Liveness probe
    - GET /ready - Readiness probe
    """
    import argparse
    from http.server import BaseHTTPRequestHandler, HTTPServer

    parser = argparse.ArgumentParser(description="X-Agent Health Check Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    health_checker = HealthCheck()

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                response = health_checker.get_health()
                status_code = 200 if response["status"] == HealthStatus.HEALTHY else 503
            elif self.path == "/healthz":
                response = health_checker.get_liveness()
                status_code = 200
            elif self.path == "/ready":
                response = health_checker.get_readiness()
                status_code = 200 if response["ready"] else 503
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode())

        def log_message(self, format: str, *args: Any) -> None:
            # Use logger instead of print
            logger.info(format % args)

    server = HTTPServer((args.host, args.port), HealthHandler)
    print(f"Health check server running on http://{args.host}:{args.port}")
    print("Endpoints:")
    print(f"  - http://{args.host}:{args.port}/health - Full health check")
    print(f"  - http://{args.host}:{args.port}/healthz - Liveness probe")
    print(f"  - http://{args.host}:{args.port}/ready - Readiness probe")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down health check server...")
        server.shutdown()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    )
    main()
