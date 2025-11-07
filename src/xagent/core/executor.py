"""Executor - Action execution for X-Agent."""

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class Executor:
    """
    Executor runs actions and tool calls.
    
    Coordinates with the tool server to execute various actions.
    """
    
    def __init__(self, tool_server: Optional[Any] = None) -> None:
        """
        Initialize executor.
        
        Args:
            tool_server: Tool server instance
        """
        self.tool_server = tool_server
        
    async def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
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
                output = await self._execute_think(action, parameters)
            elif action_type == "tool_call":
                output = await self._execute_tool_call(action, parameters)
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
    
    async def _execute_think(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute thinking/analysis action."""
        return {
            "thought": f"Analyzed: {action}",
            "parameters": parameters,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _execute_tool_call(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute tool call."""
        if self.tool_server:
            return await self.tool_server.call_tool(tool_name, parameters)
        else:
            logger.warning("Tool server not available")
            return {
                "message": f"Tool call simulated: {tool_name}",
                "parameters": parameters,
            }
    
    async def _execute_create_goal(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute goal creation."""
        return {
            "action": "create_goal",
            "description": parameters.get("content"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def _execute_start_goal(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute goal start."""
        return {
            "action": "start_goal",
            "goal_id": parameters.get("goal_id"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
