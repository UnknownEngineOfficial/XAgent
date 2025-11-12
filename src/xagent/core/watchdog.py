"""Watchdog/Supervisor for long-running tasks.

Provides timeout detection, automatic task cancellation, and retry logic
for production-ready task management.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class TaskMetrics:
    """Metrics for a supervised task."""

    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_seconds: float = 0.0
    timeout_seconds: float = 0.0
    retry_count: int = 0
    max_retries: int = 0
    error: str | None = None
    result: Any = None


@dataclass
class SupervisedTask:
    """A task under supervision."""

    task_id: str
    coro: Coroutine
    timeout: float  # seconds
    max_retries: int = 3
    retry_on_timeout: bool = True
    retry_on_error: bool = True
    on_timeout: Callable[[str], None] | None = None
    on_complete: Callable[[str, Any], None] | None = None
    on_error: Callable[[str, Exception], None] | None = None

    # Runtime state
    asyncio_task: asyncio.Task | None = None
    metrics: TaskMetrics = field(init=False)
    _cancelled: bool = False

    def __post_init__(self):
        """Initialize metrics."""
        self.metrics = TaskMetrics(
            task_id=self.task_id,
            timeout_seconds=self.timeout,
            max_retries=self.max_retries,
        )


class TaskWatchdog:
    """
    Watchdog supervisor for long-running tasks.

    Features:
    - Timeout detection and enforcement
    - Automatic task cancellation on timeout
    - Retry logic with exponential backoff
    - Task metrics collection
    - Callback hooks for events
    """

    def __init__(self, default_timeout: float = 300.0, max_concurrent_tasks: int = 100):
        """
        Initialize task watchdog.

        Args:
            default_timeout: Default timeout for tasks in seconds (5 minutes)
            max_concurrent_tasks: Maximum number of concurrent supervised tasks
        """
        self.default_timeout = default_timeout
        self.max_concurrent_tasks = max_concurrent_tasks

        self.supervised_tasks: dict[str, SupervisedTask] = {}
        self.task_metrics: dict[str, TaskMetrics] = {}

        self._supervisor_task: asyncio.Task | None = None
        self._running = False
        self._check_interval = 1.0  # Check every second

        logger.info(
            f"TaskWatchdog initialized: default_timeout={default_timeout}s, "
            f"max_concurrent={max_concurrent_tasks}"
        )

    async def start(self) -> None:
        """Start the watchdog supervisor."""
        if self._running:
            logger.warning("Watchdog already running")
            return

        self._running = True
        self._supervisor_task = asyncio.create_task(self._supervision_loop())
        logger.info("Watchdog supervisor started")

    async def stop(self) -> None:
        """Stop the watchdog supervisor."""
        if not self._running:
            return

        self._running = False

        # Cancel all supervised tasks
        for task_id in list(self.supervised_tasks.keys()):
            await self.cancel_task(task_id)

        # Stop supervisor
        if self._supervisor_task:
            self._supervisor_task.cancel()
            try:
                await self._supervisor_task
            except asyncio.CancelledError:
                pass

        logger.info("Watchdog supervisor stopped")

    async def supervise_task(
        self,
        task_id: str,
        coro: Coroutine,
        timeout: float | None = None,
        max_retries: int = 3,
        retry_on_timeout: bool = True,
        retry_on_error: bool = True,
        on_timeout: Callable[[str], None] | None = None,
        on_complete: Callable[[str, Any], None] | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> str:
        """
        Add a task to supervision.

        Args:
            task_id: Unique identifier for the task
            coro: Coroutine to execute
            timeout: Task timeout in seconds (uses default if None)
            max_retries: Maximum retry attempts
            retry_on_timeout: Whether to retry on timeout
            retry_on_error: Whether to retry on error
            on_timeout: Callback when task times out
            on_complete: Callback when task completes successfully
            on_error: Callback when task fails

        Returns:
            Task ID

        Raises:
            ValueError: If task ID already exists or max concurrent tasks reached
        """
        if task_id in self.supervised_tasks:
            raise ValueError(f"Task {task_id} already under supervision")

        if len(self.supervised_tasks) >= self.max_concurrent_tasks:
            raise ValueError(
                f"Maximum concurrent tasks ({self.max_concurrent_tasks}) reached"
            )

        timeout = timeout or self.default_timeout

        supervised_task = SupervisedTask(
            task_id=task_id,
            coro=coro,
            timeout=timeout,
            max_retries=max_retries,
            retry_on_timeout=retry_on_timeout,
            retry_on_error=retry_on_error,
            on_timeout=on_timeout,
            on_complete=on_complete,
            on_error=on_error,
        )

        self.supervised_tasks[task_id] = supervised_task

        logger.info(
            f"Task {task_id} added to supervision: timeout={timeout}s, max_retries={max_retries}"
        )

        return task_id

    async def execute_supervised_task(
        self,
        task_id: str,
        coro: Coroutine,
        timeout: float | None = None,
        max_retries: int = 3,
        retry_on_timeout: bool = True,
        retry_on_error: bool = True,
    ) -> Any:
        """
        Execute a task with supervision and wait for result.

        Args:
            task_id: Unique identifier for the task
            coro: Coroutine to execute
            timeout: Task timeout in seconds
            max_retries: Maximum retry attempts
            retry_on_timeout: Whether to retry on timeout
            retry_on_error: Whether to retry on error

        Returns:
            Task result

        Raises:
            asyncio.TimeoutError: If task times out and no retries
            Exception: If task fails and no retries
        """
        await self.supervise_task(
            task_id=task_id,
            coro=coro,
            timeout=timeout,
            max_retries=max_retries,
            retry_on_timeout=retry_on_timeout,
            retry_on_error=retry_on_error,
        )

        # Wait for task to complete
        while task_id in self.supervised_tasks:
            await asyncio.sleep(0.1)

        # Get metrics
        metrics = self.task_metrics.get(task_id)
        if not metrics:
            raise RuntimeError(f"No metrics found for task {task_id}")

        if metrics.status == TaskStatus.COMPLETED:
            return metrics.result
        elif metrics.status == TaskStatus.TIMEOUT:
            raise asyncio.TimeoutError(f"Task {task_id} timed out after {metrics.timeout_seconds}s")
        elif metrics.status == TaskStatus.CANCELLED:
            raise asyncio.CancelledError(f"Task {task_id} was cancelled")
        else:
            raise RuntimeError(f"Task {task_id} failed: {metrics.error}")

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a supervised task.

        Args:
            task_id: Task identifier

        Returns:
            True if task was cancelled, False if not found
        """
        supervised_task = self.supervised_tasks.get(task_id)
        if not supervised_task:
            logger.warning(f"Task {task_id} not found for cancellation")
            return False

        supervised_task._cancelled = True

        if supervised_task.asyncio_task:
            supervised_task.asyncio_task.cancel()
            try:
                await supervised_task.asyncio_task
            except asyncio.CancelledError:
                pass

        supervised_task.metrics.status = TaskStatus.CANCELLED
        supervised_task.metrics.end_time = datetime.now(timezone.utc)

        # Move to completed metrics
        self.task_metrics[task_id] = supervised_task.metrics
        del self.supervised_tasks[task_id]

        logger.info(f"Task {task_id} cancelled")
        return True

    async def _supervision_loop(self) -> None:
        """Main supervision loop - monitors and manages tasks."""
        logger.info("Supervision loop started")

        while self._running:
            try:
                await self._check_tasks()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Error in supervision loop: {e}")
                await asyncio.sleep(self._check_interval)

        logger.info("Supervision loop stopped")

    async def _check_tasks(self) -> None:
        """Check all supervised tasks for timeouts and completion."""
        for task_id in list(self.supervised_tasks.keys()):
            supervised_task = self.supervised_tasks.get(task_id)
            if not supervised_task:
                continue

            # Start task if not running
            if supervised_task.asyncio_task is None:
                await self._start_task(supervised_task)
                continue

            # Check if task completed
            if supervised_task.asyncio_task.done():
                await self._handle_task_completion(supervised_task)
                continue

            # Check for timeout
            if supervised_task.metrics.start_time:
                elapsed = (
                    datetime.now(timezone.utc) - supervised_task.metrics.start_time
                ).total_seconds()

                if elapsed > supervised_task.timeout:
                    await self._handle_task_timeout(supervised_task)

    async def _start_task(self, supervised_task: SupervisedTask) -> None:
        """Start executing a supervised task."""
        supervised_task.metrics.status = TaskStatus.RUNNING
        supervised_task.metrics.start_time = datetime.now(timezone.utc)

        supervised_task.asyncio_task = asyncio.create_task(supervised_task.coro)

        logger.info(f"Task {supervised_task.task_id} started")

    async def _handle_task_completion(self, supervised_task: SupervisedTask) -> None:
        """Handle completion of a supervised task."""
        if supervised_task._cancelled:
            return

        task_id = supervised_task.task_id
        asyncio_task = supervised_task.asyncio_task

        if not asyncio_task:
            return

        try:
            result = asyncio_task.result()

            # Success
            supervised_task.metrics.status = TaskStatus.COMPLETED
            supervised_task.metrics.result = result
            supervised_task.metrics.end_time = datetime.now(timezone.utc)

            if supervised_task.metrics.start_time:
                supervised_task.metrics.duration_seconds = (
                    supervised_task.metrics.end_time - supervised_task.metrics.start_time
                ).total_seconds()

            logger.info(
                f"Task {task_id} completed successfully in {supervised_task.metrics.duration_seconds:.2f}s"
            )

            # Callback
            if supervised_task.on_complete:
                try:
                    supervised_task.on_complete(task_id, result)
                except Exception as e:
                    logger.error(f"Error in completion callback for {task_id}: {e}")

            # Move to completed metrics
            self.task_metrics[task_id] = supervised_task.metrics
            del self.supervised_tasks[task_id]

        except asyncio.CancelledError:
            # Task was cancelled
            supervised_task.metrics.status = TaskStatus.CANCELLED
            supervised_task.metrics.end_time = datetime.now(timezone.utc)

            logger.info(f"Task {task_id} was cancelled")

            self.task_metrics[task_id] = supervised_task.metrics
            del self.supervised_tasks[task_id]

        except Exception as e:
            # Task failed
            await self._handle_task_error(supervised_task, e)

    async def _handle_task_timeout(self, supervised_task: SupervisedTask) -> None:
        """Handle task timeout."""
        task_id = supervised_task.task_id

        logger.warning(
            f"Task {task_id} timed out after {supervised_task.timeout}s "
            f"(attempt {supervised_task.metrics.retry_count + 1}/{supervised_task.max_retries})"
        )

        # Cancel the task
        if supervised_task.asyncio_task:
            supervised_task.asyncio_task.cancel()
            try:
                await supervised_task.asyncio_task
            except asyncio.CancelledError:
                pass

        # Callback
        if supervised_task.on_timeout:
            try:
                supervised_task.on_timeout(task_id)
            except Exception as e:
                logger.error(f"Error in timeout callback for {task_id}: {e}")

        # Retry if configured
        if (
            supervised_task.retry_on_timeout
            and supervised_task.metrics.retry_count < supervised_task.max_retries
        ):
            supervised_task.metrics.retry_count += 1

            # Wait with exponential backoff
            wait_time = min(2 ** supervised_task.metrics.retry_count, 60)
            logger.info(f"Retrying task {task_id} after {wait_time}s...")

            await asyncio.sleep(wait_time)

            # Reset task for retry
            supervised_task.asyncio_task = None
            supervised_task.metrics.start_time = None

        else:
            # No more retries
            supervised_task.metrics.status = TaskStatus.TIMEOUT
            supervised_task.metrics.end_time = datetime.now(timezone.utc)
            supervised_task.metrics.error = f"Timeout after {supervised_task.timeout}s"

            self.task_metrics[task_id] = supervised_task.metrics
            del self.supervised_tasks[task_id]

    async def _handle_task_error(
        self, supervised_task: SupervisedTask, error: Exception
    ) -> None:
        """Handle task error."""
        task_id = supervised_task.task_id

        logger.error(
            f"Task {task_id} failed: {error} "
            f"(attempt {supervised_task.metrics.retry_count + 1}/{supervised_task.max_retries})"
        )

        # Callback
        if supervised_task.on_error:
            try:
                supervised_task.on_error(task_id, error)
            except Exception as e:
                logger.error(f"Error in error callback for {task_id}: {e}")

        # Retry if configured
        if (
            supervised_task.retry_on_error
            and supervised_task.metrics.retry_count < supervised_task.max_retries
        ):
            supervised_task.metrics.retry_count += 1

            # Wait with exponential backoff
            wait_time = min(2 ** supervised_task.metrics.retry_count, 60)
            logger.info(f"Retrying task {task_id} after {wait_time}s...")

            await asyncio.sleep(wait_time)

            # Reset task for retry
            supervised_task.asyncio_task = None
            supervised_task.metrics.start_time = None

        else:
            # No more retries
            supervised_task.metrics.status = TaskStatus.FAILED
            supervised_task.metrics.end_time = datetime.now(timezone.utc)
            supervised_task.metrics.error = str(error)

            self.task_metrics[task_id] = supervised_task.metrics
            del self.supervised_tasks[task_id]

    def get_task_status(self, task_id: str) -> TaskStatus | None:
        """Get status of a task."""
        if task_id in self.supervised_tasks:
            return self.supervised_tasks[task_id].metrics.status
        if task_id in self.task_metrics:
            return self.task_metrics[task_id].status
        return None

    def get_task_metrics(self, task_id: str) -> TaskMetrics | None:
        """Get metrics for a task."""
        if task_id in self.supervised_tasks:
            return self.supervised_tasks[task_id].metrics
        return self.task_metrics.get(task_id)

    def get_all_metrics(self) -> dict[str, TaskMetrics]:
        """Get metrics for all tasks (active and completed)."""
        all_metrics = {}

        # Active tasks
        for task_id, supervised_task in self.supervised_tasks.items():
            all_metrics[task_id] = supervised_task.metrics

        # Completed tasks
        all_metrics.update(self.task_metrics)

        return all_metrics

    def get_statistics(self) -> dict[str, Any]:
        """Get overall statistics."""
        all_metrics = self.get_all_metrics()

        stats = {
            "total_tasks": len(all_metrics),
            "active_tasks": len(self.supervised_tasks),
            "completed_tasks": len(
                [m for m in all_metrics.values() if m.status == TaskStatus.COMPLETED]
            ),
            "failed_tasks": len(
                [m for m in all_metrics.values() if m.status == TaskStatus.FAILED]
            ),
            "timeout_tasks": len(
                [m for m in all_metrics.values() if m.status == TaskStatus.TIMEOUT]
            ),
            "cancelled_tasks": len(
                [m for m in all_metrics.values() if m.status == TaskStatus.CANCELLED]
            ),
            "total_retries": sum(m.retry_count for m in all_metrics.values()),
        }

        # Calculate average duration for completed tasks
        completed = [
            m for m in all_metrics.values() if m.status == TaskStatus.COMPLETED
        ]
        if completed:
            stats["avg_duration_seconds"] = sum(
                m.duration_seconds for m in completed
            ) / len(completed)
        else:
            stats["avg_duration_seconds"] = 0.0

        return stats


# Global instance
_watchdog: TaskWatchdog | None = None


def get_watchdog() -> TaskWatchdog:
    """Get or create global watchdog instance."""
    global _watchdog
    if _watchdog is None:
        _watchdog = TaskWatchdog()
    return _watchdog
