# X-Agent API Documentation

**Version**: 0.1.0  
**Base URL**: `http://localhost:8000`  
**Last Updated**: 2025-11-08

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
   - [Authentication Endpoints](#authentication-endpoints)
   - [Agent Control Endpoints](#agent-control-endpoints)
   - [Goal Management Endpoints](#goal-management-endpoints)
   - [Health & Monitoring Endpoints](#health--monitoring-endpoints)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Examples](#examples)

---

## Overview

The X-Agent API provides a RESTful interface for interacting with an autonomous AI agent. The agent can:

- Accept and work on goals autonomously
- Decompose complex goals into sub-goals
- Execute actions using integrated tools
- Provide real-time status updates
- Learn from feedback and adapt strategies

### Key Features

- **RESTful Design**: Standard HTTP methods and status codes
- **JWT Authentication**: Secure token-based authentication
- **Real-time Updates**: WebSocket support for streaming events
- **OpenAPI/Swagger**: Interactive API documentation at `/docs`
- **Production Ready**: Health checks, metrics, and distributed tracing

---

## Authentication

The X-Agent API uses JWT (JSON Web Token) based authentication with role-based access control.

### Authentication Flow

1. **Login**: POST to `/auth/login` with username and password
2. **Receive Token**: Get a JWT access token in response
3. **Use Token**: Include token in `Authorization` header for subsequent requests

### Token Format

```
Authorization: Bearer <your-jwt-token>
```

### User Roles

- **USER**: Standard user with basic access
- **ADMIN**: Administrative user with full access including token creation

### Token Scopes

- `agent:read` - Read agent status and goals
- `agent:write` - Control agent and create/modify goals
- `admin` - Administrative operations

---

## API Endpoints

### Authentication Endpoints

#### POST /auth/login

Login and receive an access token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "username": "john",
    "role": "user",
    "scopes": ["agent:read", "agent:write"]
  }
}
```

**Note**: This is a demo endpoint. In production, credentials should be validated against a secure database.

---

#### POST /auth/token

Create a new access token (Admin only).

**Authentication**: Required (Admin role)

**Request Body:**
```json
{
  "username": "string",
  "role": "user",
  "expires_hours": 24
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "username": "newuser",
    "role": "user",
    "scopes": ["agent:read", "agent:write"]
  }
}
```

---

#### GET /auth/me

Get current authenticated user information.

**Authentication**: Required

**Response:** `200 OK`
```json
{
  "username": "john",
  "role": "user",
  "scopes": ["agent:read", "agent:write"]
}
```

---

### Agent Control Endpoints

#### GET /

Root endpoint with API information.

**Response:** `200 OK`
```json
{
  "name": "X-Agent API",
  "version": "0.1.0",
  "status": "operational"
}
```

---

#### GET /status

Get current agent status.

**Authentication**: Required (scope: `agent:read`)

**Response:** `200 OK`
```json
{
  "status": "running",
  "state": {
    "active_goals": 2,
    "completed_goals": 15,
    "total_iterations": 342,
    "uptime_seconds": 3600
  }
}
```

**Possible Status Values:**
- `running` - Agent is actively processing
- `idle` - Agent is waiting for goals
- `stopped` - Agent is stopped
- `error` - Agent encountered an error

---

#### POST /agent/start

Start the agent's cognitive loop.

**Authentication**: Required (scope: `agent:write`)

**Response:** `200 OK`
```json
{
  "status": "started",
  "message": "Agent started successfully"
}
```

---

#### POST /agent/stop

Stop the agent's cognitive loop.

**Authentication**: Required (scope: `agent:write`)

**Response:** `200 OK`
```json
{
  "status": "stopped",
  "message": "Agent stopped successfully"
}
```

---

#### POST /agent/command

Send a command to the agent.

**Authentication**: Required (scope: `agent:write`)

**Request Body:**
```json
{
  "command": "Add authentication to the API"
}
```

**Response:** `200 OK`
```json
{
  "status": "received",
  "message": "Command received and queued for processing"
}
```

---

#### POST /agent/feedback

Provide feedback to the agent about its current work.

**Authentication**: Required (scope: `agent:write`)

**Request Body:**
```json
{
  "feedback": "The implementation looks good, but add error handling"
}
```

**Response:** `200 OK`
```json
{
  "status": "received",
  "message": "Feedback received and will be considered"
}
```

---

### Goal Management Endpoints

#### POST /goals

Create a new goal for the agent.

**Authentication**: Required (scope: `agent:write`)

**Request Body:**
```json
{
  "description": "Build a REST API for user management",
  "mode": "goal_oriented",
  "priority": 8,
  "completion_criteria": [
    "All endpoints implemented",
    "Tests pass with 90%+ coverage",
    "API documentation complete"
  ]
}
```

**Field Descriptions:**
- `description` (required): Clear description of the goal
- `mode` (optional): `"goal_oriented"` (default) or `"continuous"`
  - `goal_oriented`: Goal completes when criteria are met
  - `continuous`: Goal runs indefinitely (e.g., monitoring)
- `priority` (optional): Integer 1-10, default 5 (1=lowest, 10=highest)
- `completion_criteria` (optional): List of success criteria

**Response:** `200 OK`
```json
{
  "status": "created",
  "goal": {
    "id": "goal-abc123",
    "description": "Build a REST API for user management",
    "mode": "goal_oriented",
    "priority": 8,
    "status": "pending",
    "completion_criteria": [
      "All endpoints implemented",
      "Tests pass with 90%+ coverage",
      "API documentation complete"
    ],
    "created_at": "2025-11-08T13:00:00Z",
    "sub_goals": []
  }
}
```

---

#### GET /goals

List all goals.

**Authentication**: Required (scope: `agent:read`)

**Query Parameters:**
- `status` (optional): Filter by status (`pending`, `in_progress`, `completed`, `failed`, `blocked`)
- `mode` (optional): Filter by mode (`goal_oriented`, `continuous`)

**Response:** `200 OK`
```json
{
  "total": 10,
  "goals": [
    {
      "id": "goal-abc123",
      "description": "Build a REST API for user management",
      "status": "in_progress",
      "priority": 8,
      "mode": "goal_oriented",
      "created_at": "2025-11-08T13:00:00Z",
      "sub_goals": ["goal-def456", "goal-ghi789"]
    },
    {
      "id": "goal-jkl012",
      "description": "Monitor system health",
      "status": "in_progress",
      "priority": 5,
      "mode": "continuous",
      "created_at": "2025-11-08T12:00:00Z",
      "sub_goals": []
    }
  ]
}
```

---

#### GET /goals/{goal_id}

Get details of a specific goal.

**Authentication**: Required (scope: `agent:read`)

**Path Parameters:**
- `goal_id`: Unique goal identifier

**Response:** `200 OK`
```json
{
  "id": "goal-abc123",
  "description": "Build a REST API for user management",
  "status": "in_progress",
  "priority": 8,
  "mode": "goal_oriented",
  "completion_criteria": [
    "All endpoints implemented",
    "Tests pass with 90%+ coverage",
    "API documentation complete"
  ],
  "created_at": "2025-11-08T13:00:00Z",
  "updated_at": "2025-11-08T14:30:00Z",
  "parent_id": null,
  "sub_goals": [
    {
      "id": "goal-def456",
      "description": "Design API endpoints",
      "status": "completed"
    },
    {
      "id": "goal-ghi789",
      "description": "Implement authentication",
      "status": "in_progress"
    }
  ],
  "progress": {
    "completed_sub_goals": 3,
    "total_sub_goals": 5,
    "percentage": 60
  }
}
```

**Error Response:** `404 Not Found`
```json
{
  "detail": "Goal not found"
}
```

---

### Health & Monitoring Endpoints

#### GET /health

Comprehensive health check with dependency status.

**Response:** `200 OK` (all healthy) or `503 Service Unavailable` (unhealthy)

```json
{
  "status": "healthy",
  "timestamp": "2025-11-08T13:00:00Z",
  "service": "x-agent-api",
  "version": "0.1.0",
  "dependencies": {
    "redis": {
      "status": "healthy",
      "latency_ms": 2.3
    },
    "postgres": {
      "status": "healthy",
      "latency_ms": 5.1
    },
    "chromadb": {
      "status": "healthy",
      "latency_ms": 8.7
    }
  }
}
```

**Unhealthy Response:** `503 Service Unavailable`
```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-08T13:00:00Z",
  "service": "x-agent-api",
  "version": "0.1.0",
  "dependencies": {
    "redis": {
      "status": "unhealthy",
      "error": "Connection timeout"
    },
    "postgres": {
      "status": "healthy",
      "latency_ms": 5.1
    }
  }
}
```

---

#### GET /healthz

Kubernetes-style liveness probe. Simple check that the service is running.

**Response:** `200 OK`
```json
{
  "status": "ok"
}
```

---

#### GET /ready

Kubernetes-style readiness probe. Checks if the service is ready to accept traffic.

**Response:** `200 OK` (ready) or `503 Service Unavailable` (not ready)

```json
{
  "status": "ready"
}
```

---

#### GET /metrics

Prometheus-compatible metrics endpoint.

**Response:** `200 OK` (plain text, Prometheus format)
```
# HELP x_agent_api_requests_total Total API requests
# TYPE x_agent_api_requests_total counter
x_agent_api_requests_total{method="GET",endpoint="/goals",status="200"} 145
x_agent_api_requests_total{method="POST",endpoint="/goals",status="200"} 23

# HELP x_agent_cognitive_loop_iterations_total Total cognitive loop iterations
# TYPE x_agent_cognitive_loop_iterations_total counter
x_agent_cognitive_loop_iterations_total 342

# HELP x_agent_goals_total Total goals by status
# TYPE x_agent_goals_total gauge
x_agent_goals_total{status="pending"} 2
x_agent_goals_total{status="in_progress"} 3
x_agent_goals_total{status="completed"} 15
```

---

## Data Models

### Goal

```typescript
{
  id: string;              // Unique identifier (e.g., "goal-abc123")
  description: string;     // Human-readable goal description
  mode: "goal_oriented" | "continuous";  // Goal completion behavior
  status: "pending" | "in_progress" | "completed" | "failed" | "blocked";
  priority: number;        // 1-10, higher = more important
  completion_criteria: string[];  // List of success criteria
  created_at: string;      // ISO 8601 timestamp
  updated_at: string;      // ISO 8601 timestamp
  parent_id: string | null;  // Parent goal ID (null for top-level)
  sub_goals: Goal[];       // Child goals
}
```

### Goal Status

- **pending**: Goal created but not yet started
- **in_progress**: Agent is actively working on this goal
- **completed**: Goal successfully completed
- **failed**: Goal failed and cannot be completed
- **blocked**: Goal is blocked waiting for dependencies

### Goal Mode

- **goal_oriented**: Traditional goal that completes when criteria are met
- **continuous**: Long-running goal that runs indefinitely (e.g., monitoring, maintenance)

---

## Error Handling

The API uses standard HTTP status codes:

### Success Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully

### Client Error Codes

- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error

### Server Error Codes

- `500 Internal Server Error` - Unexpected server error
- `503 Service Unavailable` - Service temporarily unavailable

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Validation Error Response

```json
{
  "detail": [
    {
      "loc": ["body", "priority"],
      "msg": "ensure this value is less than or equal to 10",
      "type": "value_error.number.not_le"
    }
  ]
}
```

---

## Rate Limiting

**Status**: Planned  
**Implementation**: To be added in future release

Rate limiting will protect the API from abuse:
- Default: 100 requests per minute per IP
- Authenticated users: 1000 requests per minute
- Admin users: 10000 requests per minute

Rate limit headers will be included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699459200
```

---

## Examples

### Complete Workflow Example

#### 1. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john",
    "password": "secret"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "username": "john",
    "role": "user",
    "scopes": ["agent:read", "agent:write"]
  }
}
```

#### 2. Create a Goal

```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST http://localhost:8000/goals \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build a user authentication system",
    "mode": "goal_oriented",
    "priority": 9,
    "completion_criteria": [
      "User registration endpoint working",
      "Login endpoint with JWT tokens",
      "Password hashing implemented",
      "Tests pass with 90%+ coverage"
    ]
  }'
```

Response:
```json
{
  "status": "created",
  "goal": {
    "id": "goal-abc123",
    "description": "Build a user authentication system",
    "mode": "goal_oriented",
    "priority": 9,
    "status": "pending",
    "completion_criteria": [
      "User registration endpoint working",
      "Login endpoint with JWT tokens",
      "Password hashing implemented",
      "Tests pass with 90%+ coverage"
    ],
    "created_at": "2025-11-08T13:00:00Z",
    "sub_goals": []
  }
}
```

#### 3. Start the Agent

```bash
curl -X POST http://localhost:8000/agent/start \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "status": "started",
  "message": "Agent started successfully"
}
```

#### 4. Check Goal Status

```bash
curl -X GET http://localhost:8000/goals/goal-abc123 \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "id": "goal-abc123",
  "description": "Build a user authentication system",
  "status": "in_progress",
  "priority": 9,
  "mode": "goal_oriented",
  "completion_criteria": [
    "User registration endpoint working",
    "Login endpoint with JWT tokens",
    "Password hashing implemented",
    "Tests pass with 90%+ coverage"
  ],
  "created_at": "2025-11-08T13:00:00Z",
  "updated_at": "2025-11-08T13:05:00Z",
  "parent_id": null,
  "sub_goals": [
    {
      "id": "goal-def456",
      "description": "Design authentication database schema",
      "status": "completed"
    },
    {
      "id": "goal-ghi789",
      "description": "Implement user registration endpoint",
      "status": "in_progress"
    }
  ],
  "progress": {
    "completed_sub_goals": 1,
    "total_sub_goals": 4,
    "percentage": 25
  }
}
```

#### 5. Provide Feedback

```bash
curl -X POST http://localhost:8000/agent/feedback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "feedback": "Great progress! Make sure to use bcrypt for password hashing"
  }'
```

Response:
```json
{
  "status": "received",
  "message": "Feedback received and will be considered"
}
```

#### 6. List All Goals

```bash
curl -X GET http://localhost:8000/goals \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "total": 1,
  "goals": [
    {
      "id": "goal-abc123",
      "description": "Build a user authentication system",
      "status": "in_progress",
      "priority": 9,
      "mode": "goal_oriented",
      "created_at": "2025-11-08T13:00:00Z",
      "sub_goals": ["goal-def456", "goal-ghi789", "goal-jkl012", "goal-mno345"]
    }
  ]
}
```

#### 7. Check Health

```bash
curl -X GET http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-08T13:30:00Z",
  "service": "x-agent-api",
  "version": "0.1.0",
  "dependencies": {
    "redis": {
      "status": "healthy",
      "latency_ms": 2.1
    },
    "postgres": {
      "status": "healthy",
      "latency_ms": 4.8
    },
    "chromadb": {
      "status": "healthy",
      "latency_ms": 7.9
    }
  }
}
```

---

## Python Client Example

```python
import requests
from typing import Dict, Any

class XAgentClient:
    """Python client for X-Agent API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token = None
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login and store access token."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"username": username, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data["access_token"]
        return data
    
    def _headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        if not self.token:
            raise ValueError("Not authenticated. Call login() first.")
        return {"Authorization": f"Bearer {self.token}"}
    
    def create_goal(
        self,
        description: str,
        mode: str = "goal_oriented",
        priority: int = 5,
        completion_criteria: list[str] = None
    ) -> Dict[str, Any]:
        """Create a new goal."""
        response = requests.post(
            f"{self.base_url}/goals",
            headers=self._headers(),
            json={
                "description": description,
                "mode": mode,
                "priority": priority,
                "completion_criteria": completion_criteria or []
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_goals(self, status: str = None) -> Dict[str, Any]:
        """List all goals, optionally filtered by status."""
        params = {"status": status} if status else {}
        response = requests.get(
            f"{self.base_url}/goals",
            headers=self._headers(),
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_goal(self, goal_id: str) -> Dict[str, Any]:
        """Get details of a specific goal."""
        response = requests.get(
            f"{self.base_url}/goals/{goal_id}",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def start_agent(self) -> Dict[str, Any]:
        """Start the agent."""
        response = requests.post(
            f"{self.base_url}/agent/start",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def stop_agent(self) -> Dict[str, Any]:
        """Stop the agent."""
        response = requests.post(
            f"{self.base_url}/agent/stop",
            headers=self._headers()
        )
        response.raise_for_status()
        return response.json()
    
    def send_feedback(self, feedback: str) -> Dict[str, Any]:
        """Send feedback to the agent."""
        response = requests.post(
            f"{self.base_url}/agent/feedback",
            headers=self._headers(),
            json={"feedback": feedback}
        )
        response.raise_for_status()
        return response.json()


# Usage example
if __name__ == "__main__":
    # Initialize client
    client = XAgentClient("http://localhost:8000")
    
    # Login
    client.login("john", "secret")
    
    # Create a goal
    goal = client.create_goal(
        description="Build a REST API for user management",
        priority=8,
        completion_criteria=[
            "All endpoints implemented",
            "Tests pass with 90%+ coverage",
            "API documentation complete"
        ]
    )
    print(f"Created goal: {goal['goal']['id']}")
    
    # Start the agent
    client.start_agent()
    print("Agent started")
    
    # Check goals
    goals = client.get_goals()
    print(f"Total goals: {goals['total']}")
    
    # Get specific goal
    goal_details = client.get_goal(goal['goal']['id'])
    print(f"Goal status: {goal_details['status']}")
    
    # Send feedback
    client.send_feedback("Great progress! Add error handling to all endpoints")
```

---

## Interactive API Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation where you can:
- Explore all endpoints
- Try out API calls directly in your browser
- See request/response schemas
- Test authentication

Alternative ReDoc documentation: `http://localhost:8000/redoc`

---

## WebSocket API

For real-time event streaming, connect to the WebSocket endpoint:

**URL**: `ws://localhost:8001/ws`

See the WebSocket documentation for details on real-time communication.

---

## Support & Contributing

- **Issues**: https://github.com/UnknownEngineOfficial/X-Agent/issues
- **Discussions**: https://github.com/UnknownEngineOfficial/X-Agent/discussions
- **Contributing**: See [CONTRIBUTING.md](../CONTRIBUTING.md)

---

## Changelog

- **2025-11-08**: Initial API documentation created
- All endpoints documented with examples
- Python client example added
- Error handling guide added
