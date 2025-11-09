"""Performance tests for X-Agent API using Locust."""

import json
from typing import Any

from locust import HttpUser, between, task


class XAgentAPIUser(HttpUser):
    """Simulates a user interacting with the X-Agent API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = "http://localhost:8000"  # Can be overridden with --host flag

    def on_start(self) -> None:
        """Called when a simulated user starts."""
        # Perform login and get token if authentication is enabled
        # For now, we'll work without authentication in load tests
        pass

    @task(3)
    def get_status(self) -> None:
        """Get agent status (most common operation)."""
        with self.client.get("/status", catch_response=True, name="GET /status") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def list_goals(self) -> None:
        """List all goals."""
        with self.client.get("/goals", catch_response=True, name="GET /goals") as response:
            if response.status_code in (200, 401):  # 401 if auth is required
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def create_goal(self) -> None:
        """Create a new goal."""
        goal_data = {"description": "Performance test goal", "mode": "one_time", "priority": 5}
        with self.client.post(
            "/goals", json=goal_data, catch_response=True, name="POST /goals"
        ) as response:
            if response.status_code in (200, 201, 401):
                if response.status_code in (200, 201):
                    # Store goal ID for later cleanup
                    try:
                        data = response.json()
                        if "id" in data:
                            self.goal_ids = getattr(self, "goal_ids", [])
                            self.goal_ids.append(data["id"])
                    except json.JSONDecodeError:
                        pass
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(1)
    def health_check(self) -> None:
        """Check health endpoint."""
        with self.client.get("/health", catch_response=True, name="GET /health") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def readiness_check(self) -> None:
        """Check readiness endpoint."""
        with self.client.get("/ready", catch_response=True, name="GET /ready") as response:
            if response.status_code in (200, 503):
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    def on_stop(self) -> None:
        """Called when a simulated user stops."""
        # Cleanup created goals if we have any
        goal_ids = getattr(self, "goal_ids", [])
        for goal_id in goal_ids:
            try:
                self.client.delete(f"/goals/{goal_id}")
            except Exception:
                pass  # Best effort cleanup


class XAgentAuthenticatedUser(HttpUser):
    """Simulates an authenticated user with higher load."""

    wait_time = between(0.5, 2)
    host = "http://localhost:8000"
    token: str | None = None

    def on_start(self) -> None:
        """Login and get authentication token."""
        login_data = {"username": "admin", "password": "admin"}  # Default test credentials
        response = self.client.post("/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")

    def _get_headers(self) -> dict[str, str]:
        """Get headers with authentication token."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def authenticated_status(self) -> None:
        """Get status with authentication."""
        self.client.get("/status", headers=self._get_headers(), name="GET /status (auth)")

    @task(3)
    def authenticated_list_goals(self) -> None:
        """List goals with authentication."""
        self.client.get("/goals", headers=self._get_headers(), name="GET /goals (auth)")

    @task(2)
    def authenticated_create_goal(self) -> None:
        """Create goal with authentication."""
        goal_data = {
            "description": "Authenticated performance test goal",
            "mode": "one_time",
            "priority": 5,
        }
        self.client.post(
            "/goals", json=goal_data, headers=self._get_headers(), name="POST /goals (auth)"
        )


class XAgentStressUser(HttpUser):
    """High-frequency user for stress testing."""

    wait_time = between(0.1, 0.5)  # Very short wait times
    host = "http://localhost:8000"

    @task
    def rapid_health_checks(self) -> None:
        """Rapid health check requests."""
        self.client.get("/healthz", name="GET /healthz (stress)")

    @task
    def rapid_status_checks(self) -> None:
        """Rapid status check requests."""
        self.client.get("/status", name="GET /status (stress)")
