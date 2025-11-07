"""REST API for X-Agent."""

from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Depends, Security, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from xagent.core.agent import XAgent
from xagent.core.goal_engine import GoalMode
from xagent.config import settings
from xagent.utils.logging import get_logger, configure_logging
from xagent.health import HealthCheck
from xagent.security.auth import (
    AuthManager,
    User,
    UserRole,
    TokenScope,
    verify_token,
    require_scope,
    require_role,
    optional_auth,
    get_auth_manager,
)
from xagent.monitoring.metrics import get_metrics_collector

logger = get_logger(__name__)

# Configure logging
configure_logging()

# Create FastAPI app
app = FastAPI(
    title="X-Agent API",
    description="Autonomous AI Agent API",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent: Optional[XAgent] = None

# Global health checker instance
health_checker = HealthCheck()


# Request/Response models
class GoalCreate(BaseModel):
    """Goal creation request."""
    
    description: str
    mode: str = "goal_oriented"  # goal_oriented or continuous
    priority: int = 5
    completion_criteria: list[str] = []


class CommandRequest(BaseModel):
    """Command request."""
    
    command: str


class FeedbackRequest(BaseModel):
    """Feedback request."""
    
    feedback: str


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
    user: Dict[str, Any] = Field(..., description="User information")


class CreateTokenRequest(BaseModel):
    """Create token request (admin only)."""
    
    username: str = Field(..., description="Username")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    expires_hours: int = Field(default=24, description="Token expiration in hours")


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
async def get_current_user(current_user: User = Depends(verify_token)) -> Dict[str, Any]:
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
@app.on_event("startup")
async def startup_event() -> None:
    """Initialize agent on startup."""
    global agent
    
    logger.info("Starting X-Agent API...")
    agent = XAgent()
    await agent.initialize()
    logger.info("X-Agent API started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    global agent
    
    logger.info("Shutting down X-Agent API...")
    if agent:
        await agent.stop()
    logger.info("X-Agent API shutdown complete")


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "name": "X-Agent API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/status")
async def get_status(current_user: Optional[User] = Depends(optional_auth)) -> Dict[str, Any]:
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


@app.post("/start", dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))], tags=["Agent Control"])
async def start_agent(
    goal: Optional[GoalCreate] = None,
    current_user: User = Depends(verify_token),
) -> Dict[str, str]:
    """Start the agent. Requires AGENT_CONTROL scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    initial_goal = goal.description if goal else None
    await agent.start(initial_goal=initial_goal)
    
    logger.info(f"Agent started by user: {current_user.username}")
    
    return {"status": "started", "message": "Agent started successfully"}


@app.post("/stop", dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))], tags=["Agent Control"])
async def stop_agent(current_user: User = Depends(verify_token)) -> Dict[str, str]:
    """Stop the agent. Requires AGENT_CONTROL scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent.stop()
    
    logger.info(f"Agent stopped by user: {current_user.username}")
    
    return {"status": "stopped", "message": "Agent stopped successfully"}


@app.post("/command", dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))], tags=["Agent Control"])
async def send_command(
    request: CommandRequest,
    current_user: User = Depends(verify_token),
) -> Dict[str, str]:
    """Send a command to the agent. Requires AGENT_CONTROL scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent.send_command(request.command)
    
    logger.info(f"Command sent by {current_user.username}: {request.command}")
    
    return {
        "status": "sent",
        "message": f"Command sent: {request.command}",
    }


@app.post("/feedback", dependencies=[Depends(require_scope(TokenScope.AGENT_CONTROL.value))], tags=["Agent Control"])
async def send_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(verify_token),
) -> Dict[str, str]:
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
@app.post("/goals", dependencies=[Depends(require_scope(TokenScope.GOAL_WRITE.value))], tags=["Goals"])
async def create_goal(
    goal: GoalCreate,
    current_user: User = Depends(verify_token),
) -> Dict[str, Any]:
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
    
    return {
        "status": "created",
        "goal": created_goal.to_dict(),
    }


@app.get("/goals", dependencies=[Depends(require_scope(TokenScope.GOAL_READ.value))], tags=["Goals"])
async def list_goals(current_user: User = Depends(verify_token)) -> Dict[str, Any]:
    """List all goals. Requires GOAL_READ scope."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    goals = agent.goal_engine.list_goals()
    
    return {
        "total": len(goals),
        "goals": [goal.to_dict() for goal in goals],
    }


@app.get("/goals/{goal_id}", dependencies=[Depends(require_scope(TokenScope.GOAL_READ.value))], tags=["Goals"])
async def get_goal(
    goal_id: str,
    current_user: User = Depends(verify_token),
) -> Dict[str, Any]:
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
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Returns detailed health status including all dependency checks.
    Returns 200 if healthy, 503 if unhealthy.
    """
    health_status = health_checker.get_health()
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    # FastAPI doesn't allow direct status code setting in return,
    # so we use Response for custom status codes
    from fastapi import Response
    from fastapi.responses import JSONResponse
    
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/healthz")
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe endpoint.
    
    Indicates if the service is alive and running.
    Always returns 200 if the service is responsive.
    """
    return health_checker.get_liveness()


@app.get("/ready")
async def readiness_check() -> Dict[str, Any]:
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
    current_user: Optional[User] = Depends(optional_auth),
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
