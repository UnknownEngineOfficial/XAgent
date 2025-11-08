"""WebSocket Gateway for real-time communication."""

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from xagent.core.agent import XAgent
from xagent.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)

# Configure logging
configure_logging()

# Create FastAPI app for WebSocket
app = FastAPI(
    title="X-Agent WebSocket Gateway",
    description="Real-time communication with X-Agent",
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

# Global agent instance and active connections
agent: XAgent | None = None
active_connections: set[WebSocket] = set()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_to_client(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        self.active_connections -= disconnected


manager = ConnectionManager()


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize agent on startup."""
    global agent

    logger.info("Starting X-Agent WebSocket Gateway...")
    agent = XAgent()
    await agent.initialize()
    logger.info("X-Agent WebSocket Gateway started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup on shutdown."""
    global agent

    logger.info("Shutting down X-Agent WebSocket Gateway...")
    if agent:
        await agent.stop()
    logger.info("X-Agent WebSocket Gateway shutdown complete")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "X-Agent WebSocket Gateway",
        "version": "0.1.0",
        "active_connections": len(manager.active_connections),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time communication."""
    await manager.connect(websocket)

    # Send welcome message
    await manager.send_to_client(
        websocket,
        {
            "type": "connected",
            "message": "Connected to X-Agent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                logger.info(f"Received message: {message_type}")

                # Handle different message types
                if message_type == "command":
                    await handle_command(websocket, message)

                elif message_type == "feedback":
                    await handle_feedback(websocket, message)

                elif message_type == "status":
                    await handle_status_request(websocket)

                elif message_type == "start":
                    await handle_start(websocket, message)

                elif message_type == "stop":
                    await handle_stop(websocket)

                else:
                    await manager.send_to_client(
                        websocket,
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

            except json.JSONDecodeError:
                await manager.send_to_client(
                    websocket,
                    {
                        "type": "error",
                        "message": "Invalid JSON",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected")


async def handle_command(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Handle command message."""
    command = message.get("content", "")

    if not agent:
        await manager.send_to_client(
            websocket,
            {
                "type": "error",
                "message": "Agent not initialized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return

    await agent.send_command(command)

    # Send acknowledgment
    await manager.send_to_client(
        websocket,
        {
            "type": "command_received",
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Broadcast to other clients
    await manager.broadcast(
        {
            "type": "command_broadcast",
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


async def handle_feedback(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Handle feedback message."""
    feedback = message.get("content", "")

    if not agent:
        await manager.send_to_client(
            websocket,
            {
                "type": "error",
                "message": "Agent not initialized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return

    await agent.send_feedback(feedback)

    # Send acknowledgment
    await manager.send_to_client(
        websocket,
        {
            "type": "feedback_received",
            "feedback": feedback,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def handle_status_request(websocket: WebSocket) -> None:
    """Handle status request."""
    if not agent:
        await manager.send_to_client(
            websocket,
            {
                "type": "error",
                "message": "Agent not initialized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return

    status = await agent.get_status()

    await manager.send_to_client(
        websocket,
        {
            "type": "status",
            "data": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


async def handle_start(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Handle start message."""
    if not agent:
        await manager.send_to_client(
            websocket,
            {
                "type": "error",
                "message": "Agent not initialized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return

    initial_goal = message.get("goal")
    await agent.start(initial_goal=initial_goal)

    # Send acknowledgment
    await manager.send_to_client(
        websocket,
        {
            "type": "started",
            "message": "Agent started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Broadcast to other clients
    await manager.broadcast(
        {
            "type": "agent_started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


async def handle_stop(websocket: WebSocket) -> None:
    """Handle stop message."""
    if not agent:
        await manager.send_to_client(
            websocket,
            {
                "type": "error",
                "message": "Agent not initialized",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return

    await agent.stop()

    # Send acknowledgment
    await manager.send_to_client(
        websocket,
        {
            "type": "stopped",
            "message": "Agent stopped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Broadcast to other clients
    await manager.broadcast(
        {
            "type": "agent_stopped",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
