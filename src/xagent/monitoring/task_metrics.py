"""
Task queue metrics for Prometheus monitoring.

This module provides metrics collection for Celery task execution:
- Task execution duration
- Task queue depth
- Task success/failure rates
- Worker health metrics
"""

import logging
import time
from typing import Dict, Optional

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Task execution metrics
task_started_counter = Counter(
    "xagent_task_started_total",
    "Total number of tasks started",
    ["task_name"],
)

task_completed_counter = Counter(
    "xagent_task_completed_total",
    "Total number of tasks completed",
    ["task_name", "status"],
)

task_failed_counter = Counter(
    "xagent_task_failed_total",
    "Total number of tasks failed",
    ["task_name"],
)

task_retry_counter = Counter(
    "xagent_task_retry_total",
    "Total number of task retries",
    ["task_name"],
)

task_duration_histogram = Histogram(
    "xagent_task_duration_seconds",
    "Task execution duration in seconds",
    ["task_name"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# Queue depth metrics
queue_depth_gauge = Gauge(
    "xagent_task_queue_depth",
    "Number of tasks in queue",
    ["queue_name"],
)

# Worker metrics
active_workers_gauge = Gauge(
    "xagent_active_workers",
    "Number of active Celery workers",
)

# Task state tracking (in-memory for now)
_task_start_times: Dict[str, float] = {}


def record_task_started(task_name: str, task_id: str) -> None:
    """
    Record that a task has started.

    Args:
        task_name: Name of the task
        task_id: Unique task ID
    """
    task_started_counter.labels(task_name=task_name).inc()
    _task_start_times[task_id] = time.time()
    logger.debug(f"Task started: {task_name} (ID: {task_id})")


def record_task_completed(
    task_name: str,
    task_id: str,
    success: bool = True,
) -> None:
    """
    Record that a task has completed.

    Args:
        task_name: Name of the task
        task_id: Unique task ID
        success: Whether the task succeeded
    """
    status = "success" if success else "failure"
    task_completed_counter.labels(task_name=task_name, status=status).inc()

    # Record duration if we have a start time
    if task_id in _task_start_times:
        duration = time.time() - _task_start_times[task_id]
        task_duration_histogram.labels(task_name=task_name).observe(duration)
        del _task_start_times[task_id]
        logger.debug(
            f"Task completed: {task_name} (ID: {task_id}) in {duration:.2f}s"
        )
    else:
        logger.warning(f"No start time found for task {task_id}")


def record_task_failed(task_name: str, task_id: str) -> None:
    """
    Record that a task has failed.

    Args:
        task_name: Name of the task
        task_id: Unique task ID
    """
    task_failed_counter.labels(task_name=task_name).inc()
    record_task_completed(task_name, task_id, success=False)


def record_task_retry(task_name: str, task_id: str) -> None:
    """
    Record that a task is being retried.

    Args:
        task_name: Name of the task
        task_id: Unique task ID
    """
    task_retry_counter.labels(task_name=task_name).inc()
    logger.debug(f"Task retrying: {task_name} (ID: {task_id})")


def update_queue_depth(queue_name: str, depth: int) -> None:
    """
    Update the queue depth metric.

    Args:
        queue_name: Name of the queue
        depth: Number of tasks in the queue
    """
    queue_depth_gauge.labels(queue_name=queue_name).set(depth)


def update_active_workers(count: int) -> None:
    """
    Update the active workers metric.

    Args:
        count: Number of active workers
    """
    active_workers_gauge.set(count)


def get_queue_stats() -> Dict[str, int]:
    """
    Get current queue statistics from Celery.

    Returns:
        Dict mapping queue names to task counts
    """
    try:
        from xagent.tasks.queue import celery_app

        # Get queue stats from Celery
        inspect = celery_app.control.inspect()
        active = inspect.active()
        reserved = inspect.reserved()

        stats = {}
        if active:
            for worker, tasks in active.items():
                for task in tasks:
                    queue = task.get("delivery_info", {}).get("routing_key", "default")
                    stats[queue] = stats.get(queue, 0) + 1

        if reserved:
            for worker, tasks in reserved.items():
                for task in tasks:
                    queue = task.get("delivery_info", {}).get("routing_key", "default")
                    stats[queue] = stats.get(queue, 0) + 1

        return stats

    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}")
        return {}


def get_worker_count() -> int:
    """
    Get the count of active Celery workers.

    Returns:
        Number of active workers
    """
    try:
        from xagent.tasks.queue import celery_app

        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        return len(stats) if stats else 0

    except Exception as e:
        logger.error(f"Error getting worker count: {str(e)}")
        return 0


def update_metrics() -> None:
    """
    Update all task queue metrics.

    This should be called periodically to refresh metrics.
    """
    try:
        # Update queue depths
        queue_stats = get_queue_stats()
        for queue_name, depth in queue_stats.items():
            update_queue_depth(queue_name, depth)

        # Update worker count
        worker_count = get_worker_count()
        update_active_workers(worker_count)

        logger.debug(
            f"Task metrics updated: {len(queue_stats)} queues, {worker_count} workers"
        )

    except Exception as e:
        logger.error(f"Error updating task metrics: {str(e)}")
