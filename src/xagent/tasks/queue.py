"""
Celery application configuration for X-Agent task queue.

This module configures the Celery application with:
- Redis broker for message queuing
- Redis result backend for task results
- Task routing and priorities
- Monitoring hooks for Prometheus metrics
"""

import logging
from typing import Any

from celery import Celery, Task
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
    task_success,
)
from kombu import Queue

from xagent.config import settings

logger = logging.getLogger(__name__)

# Celery application instance
celery_app = Celery(
    "xagent",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=270,  # 4.5 minutes soft limit
    task_acks_late=True,  # Acknowledge after task completes
    worker_prefetch_multiplier=1,  # One task at a time per worker
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Store additional metadata
    # Task routing
    task_routes={
        "xagent.tasks.worker.execute_cognitive_loop": {"queue": "cognitive"},
        "xagent.tasks.worker.execute_tool": {"queue": "tools"},
        "xagent.tasks.worker.process_goal": {"queue": "goals"},
        "xagent.tasks.worker.cleanup_memory": {"queue": "maintenance"},
    },
    # Queue priorities
    task_queue_max_priority=10,
    task_default_priority=5,
    # Worker configuration
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Define queues with priorities
celery_app.conf.task_queues = (
    Queue("cognitive", routing_key="cognitive", priority=7),
    Queue("tools", routing_key="tools", priority=9),  # High priority
    Queue("goals", routing_key="goals", priority=6),
    Queue("maintenance", routing_key="maintenance", priority=3),
)


class MonitoredTask(Task):
    """Base task class with monitoring hooks."""

    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """Called when task succeeds."""
        logger.info(
            "Task succeeded",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
            },
        )

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Called when task fails."""
        logger.error(
            "Task failed",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
                "exception": str(exc),
            },
            exc_info=einfo,
        )

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Called when task is retried."""
        logger.warning(
            "Task retrying",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "args": args,
                "kwargs": kwargs,
                "exception": str(exc),
            },
        )


# Set default task base class
celery_app.Task = MonitoredTask


# Celery signals for metrics collection
@task_prerun.connect
def task_prerun_handler(task_id: str, task: Task, **kwargs: dict[str, Any]) -> None:
    """Called before task execution."""
    try:
        from xagent.monitoring.task_metrics import record_task_started

        record_task_started(task.name, task_id)
    except ImportError:
        # Metrics module not available, skip
        pass


@task_postrun.connect
def task_postrun_handler(task_id: str, task: Task, retval: Any, **kwargs: dict[str, Any]) -> None:
    """Called after task execution."""
    try:
        from xagent.monitoring.task_metrics import record_task_completed

        record_task_completed(task.name, task_id, success=True)
    except ImportError:
        pass


@task_failure.connect
def task_failure_handler(task_id: str, exception: Exception, **kwargs: dict[str, Any]) -> None:
    """Called when task fails."""
    try:
        from xagent.monitoring.task_metrics import record_task_failed

        record_task_failed(kwargs.get("task", {}).get("name", "unknown"), task_id)
    except ImportError:
        pass


@task_success.connect
def task_success_handler(result: Any, **kwargs: dict[str, Any]) -> None:
    """Called when task succeeds."""
    logger.debug("Task completed successfully", extra={"result": result})


@task_retry.connect
def task_retry_handler(request: Any, reason: str, **kwargs: dict[str, Any]) -> None:
    """Called when task is retried."""
    try:
        from xagent.monitoring.task_metrics import record_task_retry

        record_task_retry(request.task, request.id)
    except ImportError:
        pass


def get_celery_app() -> Celery:
    """Get the Celery application instance.

    Returns:
        Configured Celery application
    """
    return celery_app
