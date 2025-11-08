"""REST API for X-Agent."""

import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from xagent.config import settings
from xagent.core.agent import XAgent
from xagent.core.goal_engine import GoalMode
from xagent.health import HealthCheck
from xagent.monitoring.metrics import get_metrics_collector
from xagent.monitoring.tracing import instrument_fastapi, setup_tracing
from xagent.security.auth import (
    AuthManager,
    TokenScope,
    User,
    UserRole,
    get_auth_manager,
    optional_auth,
    require_role,
    require_scope,
    verify_token,
)
from xagent.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)

# Configure logging
configure_logging()

# Initialize tracing using configuration
setup_tracing(
    service_name="x-agent-api",
    otlp_endpoint=settings.otlp_endpoint or None,
    enable_console=settings.tracing_console,
    insecure=settings.tracing_insecure,
)

# Global agent instance
agent: XAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI."""
    global agent

    # Startup
    logger.info("Starting X-Agent API...")
    agent = XAgent()
    await agent.initialize()
    logger.info("X-Agent API started")

    yield

    # Shutdown
    logger.info("Shutting down X-Agent API...")
    if agent:
        await agent.stop()
    logger.info("X-Agent API shut down")


# Create FastAPI app
app = FastAPI(
    title="X-Agent API",
    description="Autonomous AI Agent API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument FastAPI with OpenTelemetry
instrument_fastapi(app)


# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to track API metrics."""
    metrics_collector = get_metrics_collector()

    # Generate request ID
    request_id = str(uuid.uuid4())

    # Start timing
    metrics_collector.start_api_request(request_id)

    # Process request
    try:
        response = await call_next(request)

        # Record metrics
        metrics_collector.record_api_request(
            request_id=request_id,
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        )

        return response

    except Exception as e:
        # Record error
        metrics_collector.record_api_error(
            method=request.method,
            endpoint=request.url.path,
            error_type=type(e).__name__,
        )
        raise


# Global health checker instance
health_checker = HealthCheck()


# Request/Response models
class GoalCreate(BaseModel):
    """Goal creation request."""

    description: str = Field(
        ...,
        description="Description of the goal to be achieved",
        examples=["Build a web application with user authentication"],
    )
    mode: str = Field(
        default="goal_oriented",
        description="Goal mode: 'goal_oriented' (completes when done) or 'continuous' (runs indefinitely)",
        examples=["goal_oriented"],
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority level (1=lowest, 10=highest)",
        examples=[5],
    )
    completion_criteria: list[str] = Field(
        default_factory=list,
        description="List of criteria that must be met for goal completion",
        examples=[["Tests pass", "Documentation complete", "Code reviewed"]],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Build a REST API for user management",
                    "mode": "goal_oriented",
                    "priority": 8,
                    "completion_criteria": [
                        "All endpoints implemented",
                        "Tests pass with 90%+ coverage",
                        "API documentation complete",
                    ],
                }
            ]
        }
    }


class CommandRequest(BaseModel):
    """Command request."""

    command: str = Field(
        ...,
        description="Command to send to the agent",
        examples=["Add authentication to the API"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"command": "Add authentication to the API"},
                {"command": "Optimize database queries"},
                {"command": "Write unit tests for the controller"},
            ]
        }
    }


class FeedbackRequest(BaseModel):
    """Feedback request."""

    feedback: str = Field(
        ...,
        description="Feedback for the agent about its current work",
        examples=["The implementation looks good, but add error handling"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"feedback": "The implementation looks good, but add error handling"},
                {"feedback": "Please use TypeScript instead of JavaScript"},
                {"feedback": "Great progress! Continue with the next task"},
            ]
        }
    }


# Authentication models
class LoginRequest(BaseModel):
    """Login request."""

    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password (not validated in demo)")


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: dict[str, Any] = Field(..., description="User information")


class CreateTokenRequest(BaseModel):
    """Create token request (admin only)."""

    username: str = Field(..., description="Username")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    expires_hours: int = Field(default=24, description="Token expiration in hours")


# Response models
class StatusResponse(BaseModel):
    """Agent status response."""

    status: str = Field(..., description="Current agent status", examples=["started"])
    message: str = Field(..., description="Status message", examples=["Agent started successfully"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "started",
                    "message": "Agent started successfully",
                },
                {
                    "status": "stopped",
                    "message": "Agent stopped successfully",
                },
            ]
        }
    }


class GoalResponse(BaseModel):
    """Goal response."""

    status: str = Field(..., description="Operation status", examples=["created"])
    goal: dict[str, Any] = Field(..., description="Goal details")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "created",
                    "goal": {
                        "id": "goal-123",
                        "description": "Build a REST API",
                        "mode": "goal_oriented",
                        "priority": 8,
                        "status": "pending",
                        "completion_criteria": ["All endpoints implemented", "Tests pass"],
                    },
                }
            ]
        }
    }


class GoalListResponse(BaseModel):
    """Goals list response."""

    total: int = Field(..., description="Total number of goals", examples=[5])
    goals: list[dict[str, Any]] = Field(..., description="List of goals")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": 2,
                    "goals": [
                        {
                            "id": "goal-123",
                            "description": "Build a REST API",
                            "status": "in_progress",
                        },
                        {
                            "id": "goal-456",
                            "description": "Add authentication",
                            "status": "pending",
                        },
                    ],
                }
            ]
        }
    }


# API endpoints


# Authentication endpoints
@app.post("/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login(
    request: LoginRequest,
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> TokenResponse:
    """
    Login and get access token.

    Note: This is a demo endpoint. In production, validate credentials against a database.
    """
    # Demo: Accept any username/password
    # In production: Validate against database
    logger.info(f"Login attempt for user: {request.username}")

    # Determine role (demo logic - in production, get from database)
    role = UserRole.ADMIN if request.username == "admin" else UserRole.USER

    # Create token with 24 hour expiration
    expires_delta = timedelta(hours=24)
    token = auth_manager.create_access_token(
        username=request.username,
        role=role,
        expires_delta=expires_delta,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=24 * 3600,  # 24 hours in seconds
        user={
            "username": request.username,
            "role": role.value,
        },
    )


@app.post("/auth/token", response_model=TokenResponse, tags=["Authentication"])
async def create_token(
    request: CreateTokenRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> TokenResponse:
    """
    Create a token for a user (admin only).

    This endpoint allows administrators to create tokens for other users.
    """
    expires_delta = timedelta(hours=request.expires_hours)
    token = auth_manager.create_access_token(
        username=request.username,
        role=request.role,
        expires_delta=expires_delta,
    )

    logger.info(
        f"Admin {current_user.username} created token for {request.username} "
        f"with role {request.role.value}"
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=request.expires_hours * 3600,
        user={
            "username": request.username,
            "role": request.role.value,
        },
    )


@app.get("/auth/me", tags=["Authentication"])
async def get_current_user(current_user: User = Depends(verify_token)) -> dict[str, Any]:
    """
    Get current user information.

    Requires authentication.
    """
    return {
        "username": current_user.username,
        "role": current_user.role.value,
        "scopes": current_user.scopes,
        "metadata": current_user.metadata,
    }


# API endpoints

@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "X-Agent API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/status")
async def get_status(current_user: User | None = Depends(optional_auth)) -> dict[str, Any]:
    """Get agent status. Public endpoint, but returns more info when authenticated."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    status = await agent.get_status()

    # Return detailed status only for authenticated users
    if current_user is None:
        return {
            "status": status.get("status", "unknown"),
            "uptime": status.get("uptime"),
        }

    return status


@app.post(
    "/start",
    response_model=StatusResponse,
    dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))],
    tags=["Agent Control"],
    summary="Start the agent",
    description="""
    Start the X-Agent with an optional initial goal.
    
    The agent will begin its cognitive loop and start working towards the specified goal.
    If no goal is provided, the agent will start in idle mode and wait for commands.
    
    **Requires**: `AGENT_CONTROL` scope
    
    **Example Request**:
    ```json
    {
        "description": "Build a REST API for user management",
        "mode": "goal_oriented",
        "priority": 8,
        "completion_criteria": ["All endpoints implemented", "Tests pass"]
    }
    ```
    """,
    response_description="Confirmation that the agent has started",
)
async def start_agent(
    goal: GoalCreate | None = None,
    current_user: User = Depends(verify_token),
) -> StatusResponse:
    """Start the agent. Requires AGENT_CONTROL scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    initial_goal = goal.description if goal else None
    await agent.start(initial_goal=initial_goal)

    logger.info(f"Agent started by user: {current_user.username}")

    return StatusResponse(status="started", message="Agent started successfully")


@app.post(
    "/stop",
    response_model=StatusResponse,
    dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))],
    tags=["Agent Control"],
    summary="Stop the agent",
    description="""
    Stop the currently running agent.
    
    This will gracefully shut down the agent's cognitive loop and save its current state.
    
    **Requires**: `AGENT_CONTROL` scope
    """,
    response_description="Confirmation that the agent has stopped",
)
async def stop_agent(current_user: User = Depends(verify_token)) -> StatusResponse:
    """Stop the agent. Requires AGENT_CONTROL scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    await agent.stop()

    logger.info(f"Agent stopped by user: {current_user.username}")

    return StatusResponse(status="stopped", message="Agent stopped successfully")


@app.post(
    "/command",
    dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))],
    tags=["Agent Control"],
    summary="Send a command to the agent",
    description="""
    Send a command or instruction to the running agent.
    
    Commands can be used to:
    - Provide new instructions
    - Modify current behavior
    - Request specific actions
    - Guide the agent's decision-making
    
    The agent will process the command in its cognitive loop and act accordingly.
    
    **Requires**: `AGENT_CONTROL` scope
    
    **Example Request**:
    ```json
    {
        "command": "Add authentication to the API endpoints"
    }
    ```
    """,
    response_description="Confirmation that the command was received",
)
async def send_command(
    request: CommandRequest,
    current_user: User = Depends(verify_token),
) -> dict[str, str]:
    """Send a command to the agent. Requires AGENT_CONTROL scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    await agent.send_command(request.command)

    logger.info(f"Command sent by {current_user.username}: {request.command}")

    return {
        "status": "sent",
        "message": f"Command sent: {request.command}",
    }


@app.post(
    "/feedback",
    dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))],
    tags=["Agent Control"],
)
async def send_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(verify_token),
) -> dict[str, str]:
    """Send feedback to the agent. Requires AGENT_CONTROL scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    await agent.send_feedback(request.feedback)

    logger.info(f"Feedback sent by {current_user.username}: {request.feedback}")

    return {
        "status": "sent",
        "message": f"Feedback sent: {request.feedback}",
    }


# Goal management endpoints
@app.post(
    "/goals",
    dependencies=[Depends(require_scope(TokenScope.GOAL_WRITE.value))],
    tags=["Goals"],
    summary="Create a new goal",
    description="""
    Create a new goal for the agent to work on.
    
    Goals can be either:
    - **goal_oriented**: The agent works until the goal is completed
    - **continuous**: The agent works on the goal indefinitely until stopped
    
    Each goal has:
    - **description**: What the agent should achieve
    - **priority**: How important the goal is (1-10)
    - **completion_criteria**: Specific conditions that must be met
    
    **Requires**: `GOAL_WRITE` scope
    
    **Example Request**:
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
    """,
    response_description="The created goal with its ID and status",
)
async def create_goal(
    goal: GoalCreate,
    current_user: User = Depends(verify_token),
) -> GoalResponse:
    """Create a new goal. Requires GOAL_WRITE scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    mode = GoalMode.CONTINUOUS if goal.mode == "continuous" else GoalMode.GOAL_ORIENTED

    created_goal = agent.goal_engine.create_goal(
        description=goal.description,
        mode=mode,
        priority=goal.priority,
        completion_criteria=goal.completion_criteria,
    )

    logger.info(f"Goal created by {current_user.username}: {goal.description}")

    return GoalResponse(
        status="created",
        goal=created_goal.to_dict(),
    )


@app.get(
    "/goals",
    response_model=GoalListResponse,
    dependencies=[Depends(require_scope(TokenScope.GOAL_READ.value))],
    tags=["Goals"],
    summary="List all goals",
    description="""
    Retrieve a list of all goals the agent is currently working on or has completed.
    
    **Requires**: `GOAL_READ` scope
    """,
    response_description="List of all goals with their current status",
)
async def list_goals(current_user: User = Depends(verify_token)) -> GoalListResponse:
    """List all goals. Requires GOAL_READ scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    goals = agent.goal_engine.list_goals()

    return GoalListResponse(
        total=len(goals),
        goals=[goal.to_dict() for goal in goals],
    )


@app.get(
    "/goals/{goal_id}",
    dependencies=[Depends(require_scope(TokenScope.GOAL_READ.value))],
    tags=["Goals"],
)
async def get_goal(
    goal_id: str,
    current_user: User = Depends(verify_token),
) -> dict[str, Any]:
    """Get a specific goal. Requires GOAL_READ scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    goal = agent.goal_engine.get_goal(goal_id)

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return {
        "goal": goal.to_dict(),
        "hierarchy": agent.goal_engine.get_goal_hierarchy(goal_id),
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check endpoint.

    Returns detailed health status including all dependency checks.
    Returns 200 if healthy, 503 if unhealthy.
    """
    health_status = health_checker.get_health()
    status_code = 200 if health_status["status"] == "healthy" else 503

    # FastAPI doesn't allow direct status code setting in return,
    # so we use Response for custom status codes
    from fastapi.responses import JSONResponse

    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/healthz")
async def liveness_check() -> dict[str, Any]:
    """
    Liveness probe endpoint.

    Indicates if the service is alive and running.
    Always returns 200 if the service is responsive.
    """
    return health_checker.get_liveness()


@app.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """
    Readiness probe endpoint.

    Indicates if the service is ready to accept traffic.
    Returns 200 if ready, 503 if not ready.
    """
    readiness_status = health_checker.get_readiness()
    status_code = 200 if readiness_status["ready"] else 503

    from fastapi.responses import JSONResponse

    return JSONResponse(content=readiness_status, status_code=status_code)


@app.get("/metrics", tags=["Monitoring"])
async def metrics_endpoint(
    current_user: User | None = Depends(optional_auth),
) -> Response:
    """
    Prometheus metrics endpoint.

    Public endpoint that exposes Prometheus-compatible metrics.
    Provides more detailed metrics when authenticated with SYSTEM_METRICS scope.
    """
    metrics_collector = get_metrics_collector()

    # Get metrics in Prometheus format
    metrics_data = metrics_collector.get_metrics()

    return Response(
        content=metrics_data,
        media_type=metrics_collector.get_content_type(),
    )
