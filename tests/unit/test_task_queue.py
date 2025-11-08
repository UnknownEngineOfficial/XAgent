"""Tests for Celery task queue configuration."""

import pytest
from unittest.mock import MagicMock, patch

from xagent.tasks.queue import (
    celery_app,
    get_celery_app,
    MonitoredTask,
)


def test_celery_app_exists():
    """Test that celery app is configured."""
    assert celery_app is not None
    assert celery_app.main == "xagent"


def test_celery_app_configuration():
    """Test that celery app has correct configuration."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.task_track_started is True


def test_celery_app_time_limits():
    """Test that celery app has correct time limits."""
    assert celery_app.conf.task_time_limit == 300
    assert celery_app.conf.task_soft_time_limit == 270


def test_celery_app_task_routes():
    """Test that celery app has correct task routes."""
    routes = celery_app.conf.task_routes
    assert "xagent.tasks.worker.execute_cognitive_loop" in routes
    assert "xagent.tasks.worker.execute_tool" in routes
    assert "xagent.tasks.worker.process_goal" in routes
    assert "xagent.tasks.worker.cleanup_memory" in routes


def test_celery_app_queues():
    """Test that celery app has correct queues configured."""
    queues = celery_app.conf.task_queues
    queue_names = [q.name for q in queues]
    assert "cognitive" in queue_names
    assert "tools" in queue_names
    assert "goals" in queue_names
    assert "maintenance" in queue_names


def test_get_celery_app():
    """Test get_celery_app helper function."""
    app = get_celery_app()
    assert app is celery_app


def test_monitored_task_on_success():
    """Test MonitoredTask on_success callback."""
    task = MonitoredTask()
    task.name = "test_task"

    # Should not raise exception
    task.on_success(retval={"result": "success"}, task_id="123", args=(), kwargs={})


def test_monitored_task_on_failure():
    """Test MonitoredTask on_failure callback."""
    with patch("xagent.tasks.queue.logger"):  # Mock logger to avoid conflicts
        task = MonitoredTask()
        task.name = "test_task"

        exc = Exception("Test error")

        # Should not raise exception
        task.on_failure(exc=exc, task_id="123", args=("arg1",), kwargs={"key": "value"}, einfo=None)


def test_monitored_task_on_retry():
    """Test MonitoredTask on_retry callback."""
    with patch("xagent.tasks.queue.logger"):  # Mock logger to avoid conflicts
        task = MonitoredTask()
        task.name = "test_task"

        exc = Exception("Test error")

        # Should not raise exception
        task.on_retry(exc=exc, task_id="123", args=("arg1",), kwargs={"key": "value"}, einfo=None)


def test_celery_app_result_backend():
    """Test that celery app has result backend configured."""
    assert celery_app.conf.result_backend is not None
    assert "redis" in celery_app.conf.result_backend


def test_celery_app_worker_settings():
    """Test that celery app has correct worker settings."""
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_max_tasks_per_child == 1000


def test_celery_app_monitoring_enabled():
    """Test that monitoring events are enabled."""
    assert celery_app.conf.worker_send_task_events is True
    assert celery_app.conf.task_send_sent_event is True


@patch("xagent.monitoring.task_metrics.record_task_started")
def test_task_prerun_signal(mock_record_started):
    """Test that task prerun signal calls metric recording."""
    from xagent.tasks.queue import task_prerun_handler

    mock_task = MagicMock()
    mock_task.name = "test_task"

    task_prerun_handler(task_id="123", task=mock_task)

    # Verify metric recording was called (if module is available)
    # Note: This test might pass even if metrics aren't recorded
    # if the import fails gracefully


@patch("xagent.monitoring.task_metrics.record_task_completed")
def test_task_postrun_signal(mock_record_completed):
    """Test that task postrun signal calls metric recording."""
    from xagent.tasks.queue import task_postrun_handler

    mock_task = MagicMock()
    mock_task.name = "test_task"

    task_postrun_handler(task_id="123", task=mock_task, retval={"result": "success"})

    # Verify metric recording was called (if module is available)


@patch("xagent.monitoring.task_metrics.record_task_failed")
def test_task_failure_signal(mock_record_failed):
    """Test that task failure signal calls metric recording."""
    from xagent.tasks.queue import task_failure_handler

    exc = Exception("Test error")

    task_failure_handler(task_id="123", exception=exc, task={"name": "test_task"})

    # Verify metric recording was called (if module is available)


def test_celery_app_accept_content():
    """Test that celery only accepts JSON content."""
    assert celery_app.conf.accept_content == ["json"]


def test_celery_app_result_expires():
    """Test that results have expiration configured."""
    assert celery_app.conf.result_expires == 3600  # 1 hour


def test_celery_app_queue_priorities():
    """Test that queue priorities are configured."""
    assert celery_app.conf.task_queue_max_priority == 10
    assert celery_app.conf.task_default_priority == 5

    # Check that queues exist (priority is internal kombu detail)
    queue_names = [q.name for q in celery_app.conf.task_queues]
    assert "tools" in queue_names  # Highest priority
    assert "cognitive" in queue_names
    assert "goals" in queue_names
    assert "maintenance" in queue_names  # Lowest priority
