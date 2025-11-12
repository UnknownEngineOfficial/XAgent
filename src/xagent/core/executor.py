"""Executor - Action execution for X-Agent."""

import time
from datetime import datetime, timezone
from typing import Any, cast

from xagent.core.internal_rate_limiting import get_internal_rate_limiter
from xagent.monitoring.metrics import MetricsCollector
from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class Executor:
    """
    Executor runs actions and tool calls.

    Coordinates with the tool server to execute various actions.
    """

    def __init__(self, tool_server: Any | None = None) -> None:
        """
        Initialize executor.

        Args:
            tool_server: Tool server instance
        """
        self.tool_server = tool_server
        self.metrics = MetricsCollector()
        self.rate_limiter = get_internal_rate_limiter()

    async def execute(self, plan: dict[str, Any]) -> dict[str, Any]:
        """
        Execute an action plan.

        Args:
            plan: Action plan to execute

        Returns:
            Execution result
        """
        action_type = plan.get("type")
        action = plan.get("action")
        parameters = plan.get("parameters", {})

        logger.info(f"Executing action: {action_type} - {action}")

        result = {
            "action_type": action_type,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": False,
            "output": None,
            "error": None,
        }

        try:
            # Route to appropriate handler
            if action_type == "think":
                output = await self._execute_think(action or "", parameters)
            elif action_type == "tool_call":
                output = await self._execute_tool_call(action or "", parameters)
            elif action_type == "create_goal":
                output = await self._execute_create_goal(parameters)
            elif action_type == "start_goal":
                output = await self._execute_start_goal(parameters)
            else:
                output = {"message": f"Unknown action type: {action_type}"}

            result["success"] = True
            result["output"] = output

        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    async def _execute_think(self, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute thinking/analysis action."""
        return {
            "thought": f"Analyzed: {action}",
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _execute_tool_call(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute tool call."""
        # Check rate limit before executing tool
        if not await self.rate_limiter.check_tool_call_limit():
            logger.warning(f"Tool call rate limited: {tool_name}")
            return {
                "message": f"Tool call rate limited: {tool_name}",
                "tool": tool_name,
                "rate_limited": True,
            }

        start_time = time.time()
        status = "success"
        
        try:
            if self.tool_server:
                result = await self.tool_server.call_tool(tool_name, parameters)
                return cast(dict[str, Any], result)
            else:
                logger.warning("Tool server not available")
                status = "unavailable"
                return {
                    "message": f"Tool call simulated: {tool_name}",
                    "parameters": parameters,
                }
        except Exception as e:
            status = "error"
            raise
        finally:
            # Record tool execution metrics
            duration = time.time() - start_time
            self.metrics.record_tool_execution(duration, tool_name, status)

    async def _execute_create_goal(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute goal creation."""
        return {
            "action": "create_goal",
            "description": parameters.get("content"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _execute_start_goal(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute goal start."""
        return {
            "action": "start_goal",
            "goal_id": parameters.get("goal_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
