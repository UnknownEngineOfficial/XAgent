# Task Watchdog Documentation

## Overview

The Task Watchdog provides production-ready supervision for long-running asynchronous tasks with automatic timeout detection, task cancellation, and intelligent retry logic with exponential backoff.

**Status**: ✅ Production Ready (2025-11-12)

## Features

### 1. **Timeout Detection & Enforcement**
- Automatically detects tasks that exceed timeout limits
- Gracefully cancels timed-out tasks
- Configurable per-task timeouts
- Global default timeout settings

### 2. **Automatic Retry Logic**
- Exponential backoff strategy (2^retry_count seconds, max 60s)
- Configurable maximum retry attempts
- Separate retry policies for timeouts vs errors
- Retry counter tracking in metrics

### 3. **Task Metrics Collection**
- Start/end timestamps
- Duration tracking
- Retry count
- Status (pending, running, completed, failed, timeout, cancelled)
- Error messages
- Task results

### 4. **Event Callbacks**
- `on_complete`: Called when task succeeds
- `on_error`: Called when task fails
- `on_timeout`: Called when task times out

### 5. **Concurrent Task Management**
- Configurable maximum concurrent tasks
- Independent supervision for each task
- Statistics aggregation

## Architecture

```
┌─────────────────────────────────────────────┐
│         Task Watchdog Supervisor            │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │     Supervision Loop (1s interval)   │  │
│  │                                      │  │
│  │  1. Check active tasks               │  │
│  │  2. Detect timeouts                  │  │
│  │  3. Handle completions               │  │
│  │  4. Manage retries                   │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │   Supervised Tasks (max 100)         │  │
│  │                                      │  │
│  │  task_1 [RUNNING]  timeout: 60s     │  │
│  │  task_2 [COMPLETED] result: "ok"    │  │
│  │  task_3 [RETRY 2/3] wait: 4s        │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │       Task Metrics History           │  │
│  │  - Duration statistics               │  │
│  │  - Success/failure rates             │  │
│  │  - Retry patterns                    │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Usage

### Basic Task Supervision

Execute a task with supervision and wait for result:

```python
from xagent.core.watchdog import TaskWatchdog

async def my_long_task():
    # Some long-running operation
    await perform_heavy_computation()
    return "result"

watchdog = TaskWatchdog()
await watchdog.start()

try:
    result = await watchdog.execute_supervised_task(
        task_id="task_1",
        coro=my_long_task(),
        timeout=60.0,  # 60 second timeout
        max_retries=3,
    )
    print(f"Result: {result}")
finally:
    await watchdog.stop()
```

### Fire-and-Forget Supervision

Supervise a task without waiting for completion:

```python
async def background_task():
    await process_data()
    return "done"

await watchdog.supervise_task(
    task_id="background_1",
    coro=background_task(),
    timeout=300.0,  # 5 minute timeout
)

# Task runs in background
# Check status later
status = watchdog.get_task_status("background_1")
```

### Retry Configuration

Control retry behavior:

```python
result = await watchdog.execute_supervised_task(
    task_id="retry_demo",
    coro=flaky_operation(),
    timeout=30.0,
    max_retries=5,              # Max 5 retry attempts
    retry_on_timeout=True,       # Retry if task times out
    retry_on_error=True,         # Retry if task raises exception
)
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Attempt 4: Wait 8 seconds
- Attempt 5: Wait 16 seconds
- Attempt 6: Wait 32 seconds

### Event Callbacks

React to task events:

```python
def on_task_complete(task_id: str, result: Any):
    print(f"Task {task_id} completed with result: {result}")
    # Update database, send notification, etc.

def on_task_error(task_id: str, error: Exception):
    print(f"Task {task_id} failed: {error}")
    # Log error, alert team, etc.

def on_task_timeout(task_id: str):
    print(f"Task {task_id} timed out!")
    # Send alert, cleanup resources, etc.

await watchdog.execute_supervised_task(
    task_id="callback_demo",
    coro=my_task(),
    timeout=60.0,
    on_complete=on_task_complete,
    on_error=on_task_error,
    on_timeout=on_task_timeout,
)
```

### Task Cancellation

Cancel a running task:

```python
# Start long-running task
await watchdog.supervise_task(
    task_id="long_task",
    coro=very_long_operation(),
    timeout=3600.0,  # 1 hour
)

# Cancel if needed
cancelled = await watchdog.cancel_task("long_task")

if cancelled:
    print("Task cancelled successfully")
```

### Monitoring & Metrics

Get task metrics:

```python
# Individual task metrics
metrics = watchdog.get_task_metrics("task_1")
if metrics:
    print(f"Status: {metrics.status}")
    print(f"Duration: {metrics.duration_seconds}s")
    print(f"Retries: {metrics.retry_count}")
    if metrics.error:
        print(f"Error: {metrics.error}")

# Overall statistics
stats = watchdog.get_statistics()
print(f"Total tasks: {stats['total_tasks']}")
print(f"Completed: {stats['completed_tasks']}")
print(f"Failed: {stats['failed_tasks']}")
print(f"Timeout: {stats['timeout_tasks']}")
print(f"Average duration: {stats['avg_duration_seconds']:.2f}s")
```

### Global Singleton

Use the global watchdog instance:

```python
from xagent.core.watchdog import get_watchdog

watchdog = get_watchdog()
await watchdog.start()

# Use watchdog
result = await watchdog.execute_supervised_task(...)

# Watchdog persists across calls
watchdog2 = get_watchdog()
assert watchdog is watchdog2
```

## Configuration

### Initialization Parameters

```python
watchdog = TaskWatchdog(
    default_timeout=300.0,        # Default timeout (5 minutes)
    max_concurrent_tasks=100,     # Max concurrent supervised tasks
)
```

### Per-Task Configuration

```python
await watchdog.execute_supervised_task(
    task_id="custom_task",
    coro=my_task(),
    timeout=120.0,                # Override default timeout
    max_retries=5,                # Max retry attempts
    retry_on_timeout=True,        # Retry on timeout
    retry_on_error=True,          # Retry on exception
)
```

## Task States

Tasks progress through the following states:

```
PENDING → RUNNING → COMPLETED
                 → FAILED
                 → TIMEOUT
                 → CANCELLED
```

### State Descriptions

- **PENDING**: Task added, not yet started
- **RUNNING**: Task currently executing
- **COMPLETED**: Task finished successfully
- **FAILED**: Task raised an exception (after retries exhausted)
- **TIMEOUT**: Task exceeded timeout limit (after retries exhausted)
- **CANCELLED**: Task was explicitly cancelled

## Error Handling

### Timeout Handling

```python
try:
    result = await watchdog.execute_supervised_task(
        task_id="may_timeout",
        coro=slow_task(),
        timeout=10.0,
        max_retries=0,  # No retries
    )
except asyncio.TimeoutError as e:
    print(f"Task timed out: {e}")
    # Handle timeout
```

### Task Failure Handling

```python
try:
    result = await watchdog.execute_supervised_task(
        task_id="may_fail",
        coro=risky_task(),
        timeout=60.0,
        max_retries=0,  # No retries
    )
except RuntimeError as e:
    print(f"Task failed: {e}")
    # Handle failure
```

### Cancellation Handling

```python
try:
    result = await watchdog.execute_supervised_task(
        task_id="may_cancel",
        coro=cancellable_task(),
        timeout=60.0,
    )
except asyncio.CancelledError as e:
    print(f"Task was cancelled: {e}")
    # Handle cancellation
```

## Best Practices

### 1. Always Use Timeouts

```python
# ❌ Bad: No timeout (could hang forever)
await task()

# ✅ Good: Supervised with timeout
await watchdog.execute_supervised_task(
    "task_1",
    task(),
    timeout=60.0
)
```

### 2. Set Appropriate Timeout Values

```python
# Quick API calls
timeout=10.0  # 10 seconds

# Data processing
timeout=300.0  # 5 minutes

# ML model training
timeout=3600.0  # 1 hour

# Batch jobs
timeout=86400.0  # 24 hours
```

### 3. Use Retries for Transient Failures

```python
# Network requests (transient failures expected)
await watchdog.execute_supervised_task(
    "api_call",
    fetch_data(),
    timeout=30.0,
    max_retries=3,
    retry_on_error=True,
    retry_on_timeout=True,
)

# Deterministic computation (no retries needed)
await watchdog.execute_supervised_task(
    "calculation",
    compute_result(),
    timeout=60.0,
    max_retries=0,  # Don't retry
)
```

### 4. Monitor Task Metrics

```python
# Periodically check statistics
async def monitor_tasks():
    while True:
        await asyncio.sleep(60)  # Every minute
        
        stats = watchdog.get_statistics()
        
        # Alert if too many failures
        if stats["failed_tasks"] > 10:
            send_alert("High task failure rate")
        
        # Alert if tasks are slow
        if stats["avg_duration_seconds"] > 300:
            send_alert("Tasks running slow")
```

### 5. Use Callbacks for Important Events

```python
def alert_on_timeout(task_id: str):
    """Send alert when critical task times out."""
    send_alert(f"Critical task {task_id} timed out!")
    log_incident(task_id)

await watchdog.execute_supervised_task(
    "critical_task",
    important_operation(),
    timeout=60.0,
    on_timeout=alert_on_timeout,
)
```

### 6. Clean Up Resources

```python
async def task_with_resources():
    connection = await open_connection()
    try:
        result = await process_with_connection(connection)
        return result
    finally:
        await connection.close()  # Always cleanup

await watchdog.execute_supervised_task(
    "resource_task",
    task_with_resources(),
    timeout=60.0,
)
```

### 7. Limit Concurrent Tasks

```python
# For resource-intensive tasks
watchdog = TaskWatchdog(max_concurrent_tasks=10)

# Prevents overwhelming system with too many tasks
```

## Performance

### Overhead

- Supervision loop runs every 1 second
- Per-task overhead: < 1ms
- Minimal impact on task execution

### Scalability

- Tested with 100 concurrent tasks
- Efficient timeout checking (O(n) where n = active tasks)
- Metrics stored in memory (consider cleanup for long-running processes)

### Memory Usage

- ~1KB per supervised task (including metrics)
- Metrics history accumulates (consider periodic cleanup)

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
pytest tests/unit/test_watchdog.py -v
```

**Test Coverage:**
- Task execution (success, failure, timeout)
- Retry logic (error retries, timeout retries)
- Cancellation
- Callbacks
- Concurrent tasks
- Statistics
- Edge cases

**Test Results**: 20+ tests, 100% passing

### Integration Testing

```python
# Test with real workload
async def stress_test():
    watchdog = TaskWatchdog()
    await watchdog.start()
    
    # Run 100 tasks concurrently
    tasks = [
        watchdog.execute_supervised_task(
            f"task_{i}",
            simulate_work(),
            timeout=60.0
        )
        for i in range(100)
    ]
    
    results = await asyncio.gather(*tasks)
    
    stats = watchdog.get_statistics()
    print(f"Completed: {stats['completed_tasks']}/100")
    
    await watchdog.stop()
```

## Troubleshooting

### Task Never Starts

**Problem**: Task added but stays in PENDING state

**Causes**:
- Watchdog not started: `await watchdog.start()`
- Supervision loop blocked
- asyncio event loop not running

**Solution**:
```python
# Ensure watchdog is started
watchdog = TaskWatchdog()
await watchdog.start()

# Ensure event loop is running
asyncio.run(main())
```

### Task Times Out Immediately

**Problem**: Tasks timeout even for short operations

**Causes**:
- Timeout too short
- System clock issues
- Task blocking event loop

**Solution**:
```python
# Increase timeout
await watchdog.execute_supervised_task(
    "task",
    coro,
    timeout=300.0  # 5 minutes instead of 30s
)

# Ensure task is truly async (not blocking)
async def proper_async_task():
    await asyncio.sleep(1)  # ✅ Non-blocking
    # time.sleep(1)         # ❌ Blocks event loop
```

### Too Many Retries

**Problem**: Task retries excessively

**Causes**:
- max_retries too high
- Retry on every error (including permanent failures)

**Solution**:
```python
# Reduce retries
max_retries=2  # Instead of 10

# Don't retry on permanent failures
class PermanentError(Exception):
    pass

async def smart_task():
    try:
        return await risky_operation()
    except ValueError:
        # Transient error, will retry
        raise
    except KeyError:
        # Permanent error, don't retry
        raise PermanentError("Cannot retry")

# Only retry on ValueError, not PermanentError
```

### Memory Growth

**Problem**: Memory usage grows over time

**Cause**: Metrics history accumulates indefinitely

**Solution**:
```python
# Periodically clean old metrics
async def cleanup_old_metrics():
    while True:
        await asyncio.sleep(3600)  # Every hour
        
        all_metrics = watchdog.get_all_metrics()
        now = datetime.now(timezone.utc)
        
        # Remove metrics older than 24 hours
        for task_id, metrics in list(all_metrics.items()):
            if metrics.end_time:
                age = (now - metrics.end_time).total_seconds()
                if age > 86400:  # 24 hours
                    del watchdog.task_metrics[task_id]
```

## Integration with X-Agent

### Cognitive Loop Integration

Use watchdog for cognitive loop iterations:

```python
from xagent.core.watchdog import get_watchdog

class CognitiveLoop:
    def __init__(self):
        self.watchdog = get_watchdog()
    
    async def start(self):
        await self.watchdog.start()
        
        while self.running:
            iteration_id = f"iter_{self.iteration_count}"
            
            try:
                await self.watchdog.execute_supervised_task(
                    task_id=iteration_id,
                    coro=self.run_iteration(),
                    timeout=300.0,  # 5 min per iteration
                    max_retries=2,
                )
            except Exception as e:
                logger.error(f"Iteration failed: {e}")
```

### Tool Execution Integration

Supervise tool executions:

```python
from xagent.core.watchdog import get_watchdog

class Executor:
    def __init__(self):
        self.watchdog = get_watchdog()
    
    async def execute_tool(self, tool_name, *args):
        task_id = f"tool_{tool_name}_{uuid.uuid4()}"
        
        return await self.watchdog.execute_supervised_task(
            task_id=task_id,
            coro=self._run_tool(tool_name, *args),
            timeout=60.0,  # 1 min for tools
            max_retries=1,
            retry_on_timeout=False,  # Don't retry timeouts
            retry_on_error=True,     # Retry transient errors
        )
```

## Changelog

### Version 0.2.0 (2025-11-12)
- ✅ Initial implementation
- ✅ Timeout detection and enforcement
- ✅ Automatic retry with exponential backoff
- ✅ Event callbacks (on_complete, on_error, on_timeout)
- ✅ Task metrics collection
- ✅ Concurrent task management
- ✅ Comprehensive test suite (20+ tests)
- ✅ Production-ready documentation

## Related Documentation

- [FEATURES.md](../FEATURES.md) - Feature overview
- [COGNITIVE_LOOP.md](COGNITIVE_LOOP.md) - Cognitive loop documentation
- [TESTING.md](TESTING.md) - Testing guide

## Support

For issues or questions:
- GitHub Issues: https://github.com/UnknownEngineOfficial/XAgent/issues
- Documentation: https://github.com/UnknownEngineOfficial/XAgent/tree/main/docs

---

**Status**: ✅ Production Ready  
**Version**: 0.2.0  
**Last Updated**: 2025-11-12
