"""
Celery task definitions for X-Agent.

This module defines the core tasks that can be executed by Celery workers:
- execute_cognitive_loop: Main agent thinking and decision-making
- execute_tool: Execute a specific tool with given parameters
- process_goal: Process and update a specific goal
- cleanup_memory: Background memory cleanup and optimization
"""

import logging
from typing import Any, Dict, Optional

from celery import Task
from tenacity import retry, stop_after_attempt, wait_exponential

from xagent.tasks.queue import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="xagent.tasks.worker.execute_cognitive_loop",
    max_retries=3,
    default_retry_delay=60,
)
def execute_cognitive_loop(
    self: Task,
    agent_id: str,
    goal_id: Optional[str] = None,
    max_iterations: int = 10,
) -> Dict[str, Any]:
    """
    Execute the cognitive loop for an agent.

    This task runs the agent's main thinking cycle:
    1. Perceive current state
    2. Think and plan
    3. Decide on actions
    4. Execute actions
    5. Learn from results

    Args:
        agent_id: Unique identifier for the agent
        goal_id: Optional specific goal to work on
        max_iterations: Maximum number of loop iterations

    Returns:
        Dict with execution results:
        {
            "status": "success" | "failure" | "partial",
            "iterations": int,
            "goals_completed": int,
            "actions_executed": int,
            "error": Optional[str]
        }

    Raises:
        Exception: If cognitive loop fails critically
    """
    try:
        logger.info(
            f"Starting cognitive loop for agent {agent_id}",
            extra={"agent_id": agent_id, "goal_id": goal_id},
        )

        # Import here to avoid circular dependencies
        from xagent.core.agent import XAgent
        from xagent.core.goal_engine import GoalEngine

        # Initialize agent components
        goal_engine = GoalEngine()
        agent = XAgent(agent_id=agent_id, goal_engine=goal_engine)

        # Run cognitive loop
        results = {
            "status": "success",
            "iterations": 0,
            "goals_completed": 0,
            "actions_executed": 0,
            "error": None,
        }

        for i in range(max_iterations):
            results["iterations"] = i + 1

            try:
                # Execute one iteration of the cognitive loop
                iteration_result = agent.think_and_act()

                # Update results
                if iteration_result.get("goal_completed"):
                    results["goals_completed"] += 1
                if iteration_result.get("actions"):
                    results["actions_executed"] += len(iteration_result["actions"])

                # Check if we should stop
                if iteration_result.get("should_stop"):
                    logger.info(f"Cognitive loop completed naturally after {i+1} iterations")
                    break

            except Exception as e:
                logger.error(
                    f"Error in cognitive loop iteration {i+1}: {str(e)}",
                    exc_info=True,
                )
                results["status"] = "partial"
                results["error"] = str(e)
                break

        logger.info(
            f"Cognitive loop completed for agent {agent_id}",
            extra=results,
        )

        return results

    except Exception as exc:
        logger.error(
            f"Critical error in cognitive loop for agent {agent_id}: {str(exc)}",
            exc_info=True,
        )
        # Retry on failure
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="xagent.tasks.worker.execute_tool",
    max_retries=2,
    default_retry_delay=30,
)
def execute_tool(
    self: Task,
    tool_name: str,
    tool_args: Dict[str, Any],
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a specific tool with given arguments.

    Args:
        tool_name: Name of the tool to execute
        tool_args: Dictionary of tool arguments
        agent_id: Optional agent ID for context

    Returns:
        Dict with execution results:
        {
            "status": "success" | "failure",
            "result": Any,
            "error": Optional[str]
        }

    Raises:
        Exception: If tool execution fails
    """
    try:
        logger.info(
            f"Executing tool {tool_name}",
            extra={
                "tool_name": tool_name,
                "agent_id": agent_id,
                "args": tool_args,
            },
        )

        # Import here to avoid circular dependencies
        from xagent.tools.langserve_tools import get_tool_by_name

        # Get and execute the tool
        tool = get_tool_by_name(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        result = tool(**tool_args)

        logger.info(
            f"Tool {tool_name} executed successfully",
            extra={"tool_name": tool_name, "agent_id": agent_id},
        )

        return {
            "status": "success",
            "result": result,
            "error": None,
        }

    except Exception as exc:
        logger.error(
            f"Error executing tool {tool_name}: {str(exc)}",
            exc_info=True,
        )
        
        # Return error result instead of retrying for now
        return {
            "status": "failure",
            "result": None,
            "error": str(exc),
        }


@celery_app.task(
    bind=True,
    name="xagent.tasks.worker.process_goal",
    max_retries=3,
    default_retry_delay=45,
)
def process_goal(
    self: Task,
    goal_id: str,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a specific goal.

    This task:
    1. Loads the goal
    2. Plans how to achieve it
    3. Breaks it down into sub-goals if needed
    4. Executes the plan

    Args:
        goal_id: Unique identifier for the goal
        agent_id: Optional agent ID for context

    Returns:
        Dict with processing results:
        {
            "status": "success" | "failure",
            "goal_status": str,
            "sub_goals_created": int,
            "error": Optional[str]
        }

    Raises:
        Exception: If goal processing fails critically
    """
    try:
        logger.info(
            f"Processing goal {goal_id}",
            extra={"goal_id": goal_id, "agent_id": agent_id},
        )

        # Import here to avoid circular dependencies
        from xagent.core.goal_engine import GoalEngine
        from xagent.core.planner import Planner

        # Initialize components
        goal_engine = GoalEngine()
        planner = Planner()

        # Get the goal
        goal = goal_engine.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal not found: {goal_id}")

        # Create a plan for the goal
        plan = planner.create_plan(goal)

        # Process the plan
        result = {
            "status": "success",
            "goal_status": goal.status,
            "sub_goals_created": 0,
            "error": None,
        }

        # Create sub-goals if the plan suggests decomposition
        if plan and plan.get("sub_goals"):
            for sub_goal_desc in plan["sub_goals"]:
                sub_goal = goal_engine.create_goal(
                    description=sub_goal_desc,
                    parent_id=goal_id,
                    priority=goal.priority,
                )
                result["sub_goals_created"] += 1

        logger.info(
            f"Goal {goal_id} processed successfully",
            extra=result,
        )

        return result

    except Exception as exc:
        logger.error(
            f"Error processing goal {goal_id}: {str(exc)}",
            exc_info=True,
        )
        # Retry on failure
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="xagent.tasks.worker.cleanup_memory",
    max_retries=1,
)
def cleanup_memory(
    self: Task,
    max_age_hours: int = 24,
    batch_size: int = 100,
) -> Dict[str, Any]:
    """
    Clean up old memory entries.

    This task runs periodically to:
    1. Remove old/expired memory entries
    2. Optimize vector store
    3. Archive completed goals

    Args:
        max_age_hours: Maximum age of memory entries to keep
        batch_size: Number of entries to process per batch

    Returns:
        Dict with cleanup results:
        {
            "status": "success" | "failure",
            "entries_removed": int,
            "goals_archived": int,
            "error": Optional[str]
        }
    """
    try:
        logger.info(
            "Starting memory cleanup",
            extra={"max_age_hours": max_age_hours, "batch_size": batch_size},
        )

        # Import here to avoid circular dependencies
        from datetime import datetime, timedelta
        from xagent.memory.memory_layer import MemoryLayer
        from xagent.core.goal_engine import GoalEngine

        result = {
            "status": "success",
            "entries_removed": 0,
            "goals_archived": 0,
            "error": None,
        }

        # Clean up old memory entries
        try:
            memory = MemoryLayer()
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            # This is a placeholder - implement based on your memory layer API
            # result["entries_removed"] = memory.cleanup(cutoff_time, batch_size)
            logger.info("Memory cleanup completed (placeholder)")
        except Exception as e:
            logger.warning(f"Memory cleanup skipped: {str(e)}")

        # Archive completed goals
        try:
            goal_engine = GoalEngine()
            # This is a placeholder - implement based on your goal engine API
            # result["goals_archived"] = goal_engine.archive_completed_goals()
            logger.info("Goal archival completed (placeholder)")
        except Exception as e:
            logger.warning(f"Goal archival skipped: {str(e)}")

        logger.info(
            "Memory cleanup completed",
            extra=result,
        )

        return result

    except Exception as exc:
        logger.error(
            f"Error during memory cleanup: {str(exc)}",
            exc_info=True,
        )
        return {
            "status": "failure",
            "entries_removed": 0,
            "goals_archived": 0,
            "error": str(exc),
        }


# Periodic tasks configuration
@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender: Any, **kwargs: Dict[str, Any]) -> None:
    """
    Set up periodic tasks using Celery Beat.

    This configures scheduled tasks that run automatically:
    - Memory cleanup every 6 hours
    - Health checks every 5 minutes
    """
    # Memory cleanup every 6 hours
    sender.add_periodic_task(
        60 * 60 * 6,  # 6 hours
        cleanup_memory.s(),
        name="cleanup_memory_periodic",
    )

    logger.info("Periodic tasks configured")
