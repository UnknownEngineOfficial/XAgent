"""REST API for X-Agent."""

from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from xagent.core.agent import XAgent
from xagent.core.goal_engine import GoalMode
from xagent.config import settings
from xagent.utils.logging import get_logger, configure_logging
from xagent.health import HealthCheck

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
async def get_status() -> Dict[str, Any]:
    """Get agent status."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return await agent.get_status()


@app.post("/start")
async def start_agent(goal: Optional[GoalCreate] = None) -> Dict[str, str]:
    """Start the agent."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    initial_goal = goal.description if goal else None
    await agent.start(initial_goal=initial_goal)
    
    return {"status": "started", "message": "Agent started successfully"}


@app.post("/stop")
async def stop_agent() -> Dict[str, str]:
    """Stop the agent."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent.stop()
    
    return {"status": "stopped", "message": "Agent stopped successfully"}


@app.post("/command")
async def send_command(request: CommandRequest) -> Dict[str, str]:
    """Send a command to the agent."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent.send_command(request.command)
    
    return {
        "status": "sent",
        "message": f"Command sent: {request.command}",
    }


@app.post("/feedback")
async def send_feedback(request: FeedbackRequest) -> Dict[str, str]:
    """Send feedback to the agent."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    await agent.send_feedback(request.feedback)
    
    return {
        "status": "sent",
        "message": f"Feedback sent: {request.feedback}",
    }


@app.post("/goals")
async def create_goal(goal: GoalCreate) -> Dict[str, Any]:
    """Create a new goal."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    mode = GoalMode.CONTINUOUS if goal.mode == "continuous" else GoalMode.GOAL_ORIENTED
    
    created_goal = agent.goal_engine.create_goal(
        description=goal.description,
        mode=mode,
        priority=goal.priority,
        completion_criteria=goal.completion_criteria,
    )
    
    return {
        "status": "created",
        "goal": created_goal.to_dict(),
    }


@app.get("/goals")
async def list_goals() -> Dict[str, Any]:
    """List all goals."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    goals = agent.goal_engine.list_goals()
    
    return {
        "total": len(goals),
        "goals": [goal.to_dict() for goal in goals],
    }


@app.get("/goals/{goal_id}")
async def get_goal(goal_id: str) -> Dict[str, Any]:
    """Get a specific goal."""
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
