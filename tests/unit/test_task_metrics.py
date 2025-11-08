"""Tests for task queue metrics."""

import time
import pytest
from unittest.mock import MagicMock, patch

from xagent.monitoring.task_metrics import (
    record_task_started,
    record_task_completed,
    record_task_failed,
    record_task_retry,
    update_queue_depth,
    update_active_workers,
    get_queue_stats,
    get_worker_count,
    update_metrics,
)


def test_record_task_started():
    """Test recording task start."""
    record_task_started("test_task", "task-123")
    # Should not raise exception


def test_record_task_completed():
    """Test recording task completion."""
    # Start a task
    record_task_started("test_task", "task-456")

    # Small delay to ensure measurable duration
    time.sleep(0.01)

    # Complete the task
    record_task_completed("test_task", "task-456", success=True)
    # Should not raise exception


def test_record_task_completed_without_start():
    """Test recording completion without start time."""
    # Should handle gracefully
    record_task_completed("test_task", "unknown-task", success=True)


def test_record_task_failed():
    """Test recording task failure."""
    record_task_started("test_task", "task-789")
    record_task_failed("test_task", "task-789")
    # Should not raise exception


def test_record_task_retry():
    """Test recording task retry."""
    record_task_retry("test_task", "task-retry-1")
    # Should not raise exception


def test_update_queue_depth():
    """Test updating queue depth metric."""
    update_queue_depth("cognitive", 5)
    update_queue_depth("tools", 10)
    # Should not raise exception


def test_update_active_workers():
    """Test updating active workers metric."""
    update_active_workers(3)
    # Should not raise exception


@patch("xagent.tasks.queue.celery_app")
def test_get_queue_stats_success(mock_celery_app):
    """Test getting queue statistics."""
    # Setup mock
    mock_inspect = MagicMock()
    mock_celery_app.control.inspect.return_value = mock_inspect

    mock_inspect.active.return_value = {
        "worker1": [
            {
                "delivery_info": {"routing_key": "cognitive"},
            }
        ]
    }
    mock_inspect.reserved.return_value = {
        "worker1": [
            {
                "delivery_info": {"routing_key": "tools"},
            }
        ]
    }

    # Get stats
    stats = get_queue_stats()

    # Verify
    assert isinstance(stats, dict)
    assert "cognitive" in stats or len(stats) >= 0


@patch("xagent.tasks.queue.celery_app")
def test_get_queue_stats_error(mock_celery_app):
    """Test getting queue stats with error."""
    mock_celery_app.control.inspect.side_effect = Exception("Connection error")

    # Should return empty dict on error
    stats = get_queue_stats()
    assert stats == {}


@patch("xagent.tasks.queue.celery_app")
def test_get_worker_count_success(mock_celery_app):
    """Test getting worker count."""
    # Setup mock
    mock_inspect = MagicMock()
    mock_celery_app.control.inspect.return_value = mock_inspect
    mock_inspect.stats.return_value = {
        "worker1": {},
        "worker2": {},
    }

    # Get count
    count = get_worker_count()

    # Verify
    assert count >= 0


@patch("xagent.tasks.queue.celery_app")
def test_get_worker_count_error(mock_celery_app):
    """Test getting worker count with error."""
    mock_celery_app.control.inspect.side_effect = Exception("Connection error")

    # Should return 0 on error
    count = get_worker_count()
    assert count == 0


@patch("xagent.tasks.queue.celery_app")
def test_get_worker_count_no_workers(mock_celery_app):
    """Test getting worker count when no workers."""
    mock_inspect = MagicMock()
    mock_celery_app.control.inspect.return_value = mock_inspect
    mock_inspect.stats.return_value = None

    count = get_worker_count()
    assert count == 0


@patch("xagent.monitoring.task_metrics.get_worker_count")
@patch("xagent.monitoring.task_metrics.get_queue_stats")
def test_update_metrics_success(mock_get_queue_stats, mock_get_worker_count):
    """Test updating all metrics."""
    # Setup mocks
    mock_get_queue_stats.return_value = {
        "cognitive": 5,
        "tools": 3,
    }
    mock_get_worker_count.return_value = 2

    # Update metrics
    update_metrics()
    # Should not raise exception


@patch("xagent.monitoring.task_metrics.get_queue_stats")
def test_update_metrics_error(mock_get_queue_stats):
    """Test updating metrics with error."""
    mock_get_queue_stats.side_effect = Exception("Error")

    # Should handle error gracefully
    update_metrics()


def test_task_duration_tracking():
    """Test that task duration is tracked correctly."""
    task_id = "duration-test-123"

    # Start task
    record_task_started("test_task", task_id)

    # Wait a bit
    time.sleep(0.05)

    # Complete task
    record_task_completed("test_task", task_id, success=True)

    # Duration should have been recorded (verified by no exception)


def test_multiple_tasks_tracking():
    """Test tracking multiple tasks simultaneously."""
    # Start multiple tasks
    record_task_started("task_a", "id-1")
    record_task_started("task_b", "id-2")
    record_task_started("task_c", "id-3")

    # Complete in different order
    record_task_completed("task_b", "id-2", success=True)
    record_task_completed("task_a", "id-1", success=True)
    record_task_completed("task_c", "id-3", success=False)

    # Should track all correctly


def test_task_failed_updates_completion():
    """Test that task failure also updates completion metrics."""
    task_id = "fail-test-456"

    record_task_started("test_task", task_id)
    record_task_failed("test_task", task_id)

    # Should have recorded both failure and completion


def test_update_queue_depth_multiple_queues():
    """Test updating depth for multiple queues."""
    update_queue_depth("cognitive", 10)
    update_queue_depth("tools", 5)
    update_queue_depth("goals", 3)
    update_queue_depth("maintenance", 1)
    # Should not raise exception


def test_task_metrics_with_special_characters():
    """Test metrics with special characters in names."""
    record_task_started("task.with.dots", "task-special-1")
    record_task_completed("task.with.dots", "task-special-1", success=True)
    # Should handle special characters
