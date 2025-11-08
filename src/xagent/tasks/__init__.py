"""
Task queue management for X-Agent using Celery.

This module provides distributed task execution capabilities for:
- Cognitive loop processing
- Tool execution
- Goal management
- Background maintenance tasks

Usage:
    from xagent.tasks import celery_app, execute_cognitive_loop

    # Enqueue a task
    result = execute_cognitive_loop.delay(agent_id="agent-1")

    # Wait for result
    output = result.get(timeout=60)
"""

from xagent.tasks.queue import celery_app
from xagent.tasks.worker import (
    cleanup_memory,
    execute_cognitive_loop,
    execute_tool,
    process_goal,
)

__all__ = [
    "celery_app",
    "execute_cognitive_loop",
    "execute_tool",
    "process_goal",
    "cleanup_memory",
]
