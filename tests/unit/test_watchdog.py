"""Tests for task watchdog."""

import asyncio
import pytest

from xagent.core.watchdog import TaskStatus, TaskWatchdog, get_watchdog


@pytest.fixture
async def watchdog():
    """Create and start a watchdog for testing."""
    wd = TaskWatchdog(default_timeout=5.0, max_concurrent_tasks=10)
    await wd.start()
    yield wd
    await wd.stop()


class TestTaskWatchdog:
    """Test task watchdog functionality."""

    @pytest.mark.asyncio
    async def test_watchdog_start_stop(self):
        """Test starting and stopping watchdog."""
        wd = TaskWatchdog()
        
        assert not wd._running
        
        await wd.start()
        assert wd._running
        
        await wd.stop()
        assert not wd._running

    @pytest.mark.asyncio
    async def test_execute_successful_task(self, watchdog):
        """Test executing a successful task."""
        async def simple_task():
            await asyncio.sleep(0.1)
            return "success"

        result = await watchdog.execute_supervised_task(
            task_id="test_success",
            coro=simple_task(),
            timeout=1.0,
        )

        assert result == "success"

        metrics = watchdog.get_task_metrics("test_success")
        assert metrics is not None
        assert metrics.status == TaskStatus.COMPLETED
        assert metrics.result == "success"
        assert metrics.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_task_timeout(self, watchdog):
        """Test task timeout detection."""
        async def slow_task():
            await asyncio.sleep(10)
            return "should_not_complete"

        with pytest.raises(asyncio.TimeoutError):
            await watchdog.execute_supervised_task(
                task_id="test_timeout",
                coro=slow_task(),
                timeout=0.5,
                max_retries=0,  # No retries
            )

        metrics = watchdog.get_task_metrics("test_timeout")
        assert metrics is not None
        assert metrics.status == TaskStatus.TIMEOUT
        assert metrics.error is not None

    @pytest.mark.asyncio
    async def test_task_failure(self, watchdog):
        """Test task failure handling."""
        async def failing_task():
            await asyncio.sleep(0.1)
            raise ValueError("Task failed")

        with pytest.raises(RuntimeError):
            await watchdog.execute_supervised_task(
                task_id="test_failure",
                coro=failing_task(),
                timeout=1.0,
                max_retries=0,  # No retries
            )

        metrics = watchdog.get_task_metrics("test_failure")
        assert metrics is not None
        assert metrics.status == TaskStatus.FAILED
        assert "Task failed" in metrics.error

    @pytest.mark.asyncio
    async def test_task_retry_on_failure(self, watchdog):
        """Test task retry on failure."""
        call_count = 0

        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            if call_count < 2:
                raise ValueError("Transient error")
            return "success_after_retry"

        result = await watchdog.execute_supervised_task(
            task_id="test_retry",
            coro=failing_then_success(),
            timeout=1.0,
            max_retries=3,
            retry_on_error=True,
        )

        assert result == "success_after_retry"
        assert call_count == 2

        metrics = watchdog.get_task_metrics("test_retry")
        assert metrics.retry_count == 1

    @pytest.mark.asyncio
    async def test_task_retry_on_timeout(self, watchdog):
        """Test task retry on timeout."""
        call_count = 0

        async def timeout_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                await asyncio.sleep(10)  # Will timeout
            else:
                await asyncio.sleep(0.1)  # Will succeed
            return "success_after_timeout_retry"

        result = await watchdog.execute_supervised_task(
            task_id="test_timeout_retry",
            coro=timeout_then_success(),
            timeout=0.5,
            max_retries=3,
            retry_on_timeout=True,
        )

        assert result == "success_after_timeout_retry"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, watchdog):
        """Test max retries exceeded."""
        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            raise ValueError("Always fails")

        with pytest.raises(RuntimeError):
            await watchdog.execute_supervised_task(
                task_id="test_max_retries",
                coro=always_fails(),
                timeout=1.0,
                max_retries=2,
                retry_on_error=True,
            )

        # Should try once + 2 retries = 3 total
        assert call_count == 3

        metrics = watchdog.get_task_metrics("test_max_retries")
        assert metrics.retry_count == 2

    @pytest.mark.asyncio
    async def test_cancel_task(self, watchdog):
        """Test task cancellation."""
        async def long_task():
            await asyncio.sleep(10)
            return "should_not_complete"

        # Add task to supervision (don't wait)
        task_id = "test_cancel"
        await watchdog.supervise_task(
            task_id=task_id,
            coro=long_task(),
            timeout=20.0,
        )

        # Wait for task to start
        await asyncio.sleep(0.2)

        # Cancel task
        cancelled = await watchdog.cancel_task(task_id)
        assert cancelled is True

        metrics = watchdog.get_task_metrics(task_id)
        assert metrics.status == TaskStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_supervise_duplicate_task_id(self, watchdog):
        """Test that duplicate task IDs are rejected."""
        async def dummy_task():
            await asyncio.sleep(10)

        await watchdog.supervise_task(
            task_id="duplicate",
            coro=dummy_task(),
            timeout=20.0,
        )

        with pytest.raises(ValueError, match="already under supervision"):
            await watchdog.supervise_task(
                task_id="duplicate",
                coro=dummy_task(),
                timeout=20.0,
            )

        # Cleanup
        await watchdog.cancel_task("duplicate")

    @pytest.mark.asyncio
    async def test_max_concurrent_tasks(self):
        """Test max concurrent tasks limit."""
        wd = TaskWatchdog(max_concurrent_tasks=2)
        await wd.start()

        try:
            async def dummy_task():
                await asyncio.sleep(10)

            # Add 2 tasks (should succeed)
            await wd.supervise_task("task1", dummy_task(), timeout=20.0)
            await wd.supervise_task("task2", dummy_task(), timeout=20.0)

            # Third task should fail
            with pytest.raises(ValueError, match="Maximum concurrent tasks"):
                await wd.supervise_task("task3", dummy_task(), timeout=20.0)

        finally:
            await wd.stop()

    @pytest.mark.asyncio
    async def test_get_task_status(self, watchdog):
        """Test getting task status."""
        async def quick_task():
            await asyncio.sleep(0.1)
            return "done"

        # Non-existent task
        status = watchdog.get_task_status("nonexistent")
        assert status is None

        # Execute task
        await watchdog.execute_supervised_task(
            task_id="status_test",
            coro=quick_task(),
            timeout=1.0,
        )

        # Completed task
        status = watchdog.get_task_status("status_test")
        assert status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_statistics(self, watchdog):
        """Test getting overall statistics."""
        async def quick_task():
            await asyncio.sleep(0.1)
            return "done"

        async def failing_task():
            raise ValueError("fail")

        # Execute various tasks
        await watchdog.execute_supervised_task("success1", quick_task(), timeout=1.0)
        await watchdog.execute_supervised_task("success2", quick_task(), timeout=1.0)

        try:
            await watchdog.execute_supervised_task(
                "fail1", failing_task(), timeout=1.0, max_retries=0
            )
        except RuntimeError:
            pass

        # Get statistics
        stats = watchdog.get_statistics()

        assert stats["total_tasks"] == 3
        assert stats["completed_tasks"] == 2
        assert stats["failed_tasks"] == 1
        assert stats["avg_duration_seconds"] > 0

    @pytest.mark.asyncio
    async def test_task_callbacks(self, watchdog):
        """Test task event callbacks."""
        callback_events = []

        def on_complete(task_id, result):
            callback_events.append(("complete", task_id, result))

        def on_error(task_id, error):
            callback_events.append(("error", task_id, str(error)))

        def on_timeout(task_id):
            callback_events.append(("timeout", task_id))

        # Successful task
        async def success_task():
            return "success"

        await watchdog.execute_supervised_task(
            task_id="callback_success",
            coro=success_task(),
            timeout=1.0,
            on_complete=on_complete,
        )

        assert ("complete", "callback_success", "success") in callback_events

        # Failing task
        async def fail_task():
            raise ValueError("error")

        try:
            await watchdog.execute_supervised_task(
                task_id="callback_error",
                coro=fail_task(),
                timeout=1.0,
                max_retries=0,
                on_error=on_error,
            )
        except RuntimeError:
            pass

        assert any(
            event[0] == "error" and event[1] == "callback_error"
            for event in callback_events
        )

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self, watchdog):
        """Test multiple concurrent tasks."""
        async def task(duration):
            await asyncio.sleep(duration)
            return f"done_{duration}"

        # Start multiple tasks
        results = await asyncio.gather(
            watchdog.execute_supervised_task("concurrent1", task(0.1), timeout=1.0),
            watchdog.execute_supervised_task("concurrent2", task(0.2), timeout=1.0),
            watchdog.execute_supervised_task("concurrent3", task(0.15), timeout=1.0),
        )

        assert len(results) == 3
        assert all("done_" in str(r) for r in results)

        # Check all completed
        stats = watchdog.get_statistics()
        assert stats["completed_tasks"] >= 3

    @pytest.mark.asyncio
    async def test_no_retry_on_success(self, watchdog):
        """Test that successful tasks don't trigger retries."""
        call_count = 0

        async def success_task():
            nonlocal call_count
            call_count += 1
            return "success"

        await watchdog.execute_supervised_task(
            task_id="no_retry_success",
            coro=success_task(),
            timeout=1.0,
            max_retries=3,
        )

        # Should only be called once
        assert call_count == 1

        metrics = watchdog.get_task_metrics("no_retry_success")
        assert metrics.retry_count == 0

    @pytest.mark.asyncio
    async def test_get_watchdog_singleton(self):
        """Test global watchdog singleton."""
        wd1 = get_watchdog()
        wd2 = get_watchdog()

        assert wd1 is wd2

    @pytest.mark.asyncio
    async def test_supervision_without_wait(self, watchdog):
        """Test supervising a task without waiting for completion."""
        async def background_task():
            await asyncio.sleep(0.5)
            return "background_result"

        task_id = "background_task"
        await watchdog.supervise_task(
            task_id=task_id,
            coro=background_task(),
            timeout=2.0,
        )

        # Task should be in supervised list
        assert task_id in watchdog.supervised_tasks

        # Wait for completion
        await asyncio.sleep(1.0)

        # Task should be completed and moved to metrics
        assert task_id not in watchdog.supervised_tasks
        metrics = watchdog.get_task_metrics(task_id)
        assert metrics.status == TaskStatus.COMPLETED
        assert metrics.result == "background_result"
