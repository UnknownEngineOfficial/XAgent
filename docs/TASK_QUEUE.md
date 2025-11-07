# X-Agent Task Queue Documentation

**Version**: 1.0  
**Last Updated**: 2025-11-07  
**Status**: Production Ready

## Overview

X-Agent uses Celery as a distributed task queue for asynchronous task execution. This enables scalable, reliable processing of agent operations including cognitive loops, tool execution, goal management, and background maintenance.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                     │
│  ┌────────────────┐  ┌────────────────┐                    │
│  │ REST Endpoints │  │   WebSocket    │                    │
│  └────────┬───────┘  └────────┬───────┘                    │
└───────────┼────────────────────┼─────────────────────────────┘
            │                    │
            │ Enqueue Task       │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Redis Message Broker                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Cognitive │  │  Tools   │  │  Goals   │  │  Maint.  │   │
│  │ Queue    │  │  Queue   │  │  Queue   │  │  Queue   │   │
│  │(Priority │  │(Priority │  │(Priority │  │(Priority │   │
│  │   7)     │  │   9)     │  │   6)     │  │   3)     │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼───────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Celery Workers                           │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │   Worker 1     │  │   Worker 2     │  │   Worker N   │  │
│  │  (2 threads)   │  │  (2 threads)   │  │  (2 threads) │  │
│  └────────┬───────┘  └────────┬───────┘  └────────┬──────┘  │
└───────────┼────────────────────┼────────────────────┼─────────┘
            │                    │                    │
            │   Store Result     │                    │
            ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Redis Result Backend                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Task Results (expire after 1 hour)             │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
            │
            │   Collect Metrics
            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Prometheus Metrics                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Task duration, queue depth, success/failure rates     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Tasks

### 1. execute_cognitive_loop

**Purpose**: Execute the agent's main thinking and decision-making cycle

**Queue**: `cognitive` (priority: 7)  
**Max Retries**: 3  
**Retry Delay**: 60 seconds

**Parameters**:
- `agent_id` (str): Unique identifier for the agent
- `goal_id` (Optional[str]): Specific goal to work on
- `max_iterations` (int): Maximum loop iterations (default: 10)

**Returns**:
```python
{
    "status": "success" | "failure" | "partial",
    "iterations": int,
    "goals_completed": int,
    "actions_executed": int,
    "error": Optional[str]
}
```

**Usage**:
```python
from xagent.tasks import execute_cognitive_loop

# Enqueue task
result = execute_cognitive_loop.delay(
    agent_id="agent-123",
    max_iterations=5
)

# Get result (blocks until complete)
output = result.get(timeout=300)
```

### 2. execute_tool

**Purpose**: Execute a specific tool with given arguments

**Queue**: `tools` (priority: 9 - highest)  
**Max Retries**: 2  
**Retry Delay**: 30 seconds

**Parameters**:
- `tool_name` (str): Name of the tool to execute
- `tool_args` (Dict[str, Any]): Tool arguments
- `agent_id` (Optional[str]): Agent context

**Returns**:
```python
{
    "status": "success" | "failure",
    "result": Any,
    "error": Optional[str]
}
```

**Usage**:
```python
from xagent.tasks import execute_tool

# Execute code tool
result = execute_tool.delay(
    tool_name="execute_code",
    tool_args={
        "code": "print('Hello, World!')",
        "language": "python"
    }
)

output = result.get(timeout=60)
```

### 3. process_goal

**Purpose**: Process and decompose a specific goal

**Queue**: `goals` (priority: 6)  
**Max Retries**: 3  
**Retry Delay**: 45 seconds

**Parameters**:
- `goal_id` (str): Goal identifier
- `agent_id` (Optional[str]): Agent context

**Returns**:
```python
{
    "status": "success" | "failure",
    "goal_status": str,
    "sub_goals_created": int,
    "error": Optional[str]
}
```

**Usage**:
```python
from xagent.tasks import process_goal

result = process_goal.delay(goal_id="goal-456")
output = result.get(timeout=120)
```

### 4. cleanup_memory

**Purpose**: Background memory cleanup and optimization

**Queue**: `maintenance` (priority: 3 - lowest)  
**Max Retries**: 1  
**Schedule**: Every 6 hours (via Celery Beat)

**Parameters**:
- `max_age_hours` (int): Maximum age of entries to keep (default: 24)
- `batch_size` (int): Entries per batch (default: 100)

**Returns**:
```python
{
    "status": "success" | "failure",
    "entries_removed": int,
    "goals_archived": int,
    "error": Optional[str]
}
```

**Usage**:
```python
from xagent.tasks import cleanup_memory

# Manual cleanup
result = cleanup_memory.delay(max_age_hours=48)
output = result.get(timeout=300)
```

## Queue Configuration

### Queue Priorities

| Queue | Priority | Purpose | Example Tasks |
|-------|----------|---------|---------------|
| **tools** | 9 (highest) | Tool execution | Code execution, web search, file ops |
| **cognitive** | 7 | Agent thinking | Cognitive loop, reasoning |
| **goals** | 6 | Goal management | Goal decomposition, planning |
| **maintenance** | 3 (lowest) | Background tasks | Memory cleanup, archival |

### Task Limits

- **Hard time limit**: 5 minutes (300 seconds)
- **Soft time limit**: 4.5 minutes (270 seconds)
- **Worker prefetch**: 1 task at a time
- **Max tasks per child**: 1000 (then restart)
- **Result expiration**: 1 hour

## Worker Management

### Docker Compose

Workers are automatically started with docker-compose:

```bash
# Start all services including workers
docker-compose up -d

# View worker logs
docker-compose logs -f xagent-worker

# Scale workers
docker-compose up -d --scale xagent-worker=3

# Stop workers
docker-compose stop xagent-worker
```

### Development Script

Use `scripts/celery_worker.sh` for development:

```bash
# Start worker
./scripts/celery_worker.sh start

# Check status
./scripts/celery_worker.sh status

# View logs
./scripts/celery_worker.sh logs

# Scale workers
CELERY_CONCURRENCY=4 ./scripts/celery_worker.sh restart

# Stop worker
./scripts/celery_worker.sh stop

# Purge all pending tasks
./scripts/celery_worker.sh purge
```

### Environment Variables

Configure workers with environment variables:

```bash
# Worker concurrency
export CELERY_CONCURRENCY=2

# Queues to process
export CELERY_QUEUES=cognitive,tools,goals,maintenance

# Log level
export CELERY_LOGLEVEL=info

# Broker URL
export CELERY_BROKER_URL=redis://localhost:6379/1

# Result backend
export CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

## Monitoring

### Prometheus Metrics

Task queue metrics are automatically collected and exposed at `/metrics`:

```python
# Task execution metrics
xagent_task_started_total{task_name="execute_tool"}
xagent_task_completed_total{task_name="execute_tool",status="success"}
xagent_task_failed_total{task_name="execute_tool"}
xagent_task_retry_total{task_name="execute_tool"}

# Task duration (histogram)
xagent_task_duration_seconds{task_name="execute_tool",le="1.0"}

# Queue metrics
xagent_task_queue_depth{queue_name="tools"}

# Worker metrics
xagent_active_workers
```

### Grafana Dashboard

Access the Task Queue dashboard at: `http://localhost:3000/d/xagent-task-queue`

**Panels include**:
- Task execution rate
- Success vs failure rate
- Task duration (p50, p95)
- Queue depth by queue
- Active workers
- Task retry rate
- Success rate percentage
- Task types distribution
- Recent failures

### Manual Monitoring

```python
# Check task status
from xagent.tasks.queue import celery_app

# Inspect active tasks
inspect = celery_app.control.inspect()
active_tasks = inspect.active()

# Check queue stats
reserved_tasks = inspect.reserved()

# Get worker stats
worker_stats = inspect.stats()

# Check registered tasks
registered = inspect.registered()
```

## Error Handling

### Automatic Retries

Tasks automatically retry on failure with exponential backoff:

```python
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def my_task(self, arg):
    try:
        # Task logic
        return result
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc)
```

### Error Logging

All task errors are logged with structured logging:

```python
# Errors are automatically logged with:
# - Task ID
# - Task name
# - Arguments
# - Exception details
# - Stack trace
```

### Monitoring Failed Tasks

```python
from xagent.monitoring.task_metrics import get_queue_stats

# Get current queue statistics
stats = get_queue_stats()

# Check for task failures in Prometheus
# Query: rate(xagent_task_failed_total[5m])
```

## Best Practices

### 1. Task Design

- **Idempotent**: Tasks should produce the same result when called multiple times
- **Short-lived**: Keep tasks under 5 minutes (hard limit)
- **Atomic**: Each task should be a single unit of work
- **Stateless**: Don't rely on worker state between tasks

### 2. Queue Selection

- **tools queue**: Interactive operations needing fast response
- **cognitive queue**: Agent thinking and reasoning
- **goals queue**: Goal management and planning
- **maintenance queue**: Background cleanup and optimization

### 3. Error Handling

- Use try/except blocks for expected errors
- Return error information in task result
- Let unexpected errors trigger retries
- Log all errors for debugging

### 4. Performance

- Set appropriate concurrency for your workload
- Monitor queue depth to detect bottlenecks
- Use task priorities to manage resource allocation
- Scale workers horizontally for increased throughput

### 5. Testing

```python
# Always test tasks in isolation
def test_my_task():
    result = my_task.apply(args=("test",)).get()
    assert result["status"] == "success"

# Test with mocked dependencies
@patch("xagent.core.agent.XAgent")
def test_cognitive_loop(mock_agent):
    mock_agent.return_value.think_and_act.return_value = {"should_stop": True}
    result = execute_cognitive_loop.apply(args=("agent-123",)).get()
    assert result["status"] == "success"
```

## Troubleshooting

### Worker not starting

```bash
# Check Redis connection
redis-cli -h localhost -p 6379 ping

# Check worker logs
docker-compose logs xagent-worker

# Verify Celery installation
celery --version
```

### Tasks not executing

```bash
# Check if worker is connected to correct broker
celery -A xagent.tasks.queue inspect active

# Verify task is registered
celery -A xagent.tasks.queue inspect registered

# Check queue depth
celery -A xagent.tasks.queue inspect reserved
```

### High queue depth

```bash
# Scale workers
docker-compose up -d --scale xagent-worker=5

# Or increase concurrency
docker-compose restart xagent-worker

# With higher concurrency in env
CELERY_CONCURRENCY=4 docker-compose up -d xagent-worker
```

### Task timeouts

```python
# Increase time limits in task definition
@celery_app.task(
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=570
)
def long_running_task():
    pass
```

## Advanced Topics

### Custom Tasks

Create new tasks by adding them to `src/xagent/tasks/worker.py`:

```python
@celery_app.task(
    bind=True,
    name="xagent.tasks.worker.my_custom_task",
    max_retries=3,
)
def my_custom_task(self, arg1, arg2):
    """Custom task implementation."""
    try:
        result = do_work(arg1, arg2)
        return {"status": "success", "result": result}
    except Exception as exc:
        raise self.retry(exc=exc)
```

### Task Chaining

Chain tasks for complex workflows:

```python
from celery import chain

# Execute tasks in sequence
workflow = chain(
    process_goal.s("goal-123"),
    execute_tool.s("think", {"thought": "Planning complete"}),
    execute_cognitive_loop.s("agent-123")
)

result = workflow.apply_async()
```

### Task Groups

Execute tasks in parallel:

```python
from celery import group

# Execute multiple tools in parallel
jobs = group(
    execute_tool.s("read_file", {"path": "file1.txt"}),
    execute_tool.s("read_file", {"path": "file2.txt"}),
    execute_tool.s("read_file", {"path": "file3.txt"})
)

result = jobs.apply_async()
results = result.get()
```

### Periodic Tasks

Add scheduled tasks in `src/xagent/tasks/worker.py`:

```python
@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Run every hour
    sender.add_periodic_task(
        3600.0,
        my_hourly_task.s(),
        name='hourly_task'
    )
```

## Configuration Reference

### Celery Settings

See `src/xagent/tasks/queue.py` for complete configuration:

```python
celery_app.conf.update(
    task_serializer="json",              # JSON serialization only
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=270,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    result_extended=True,
    task_queue_max_priority=10,
    task_default_priority=5,
    worker_max_tasks_per_child=1000,
    worker_send_task_events=True,
    task_send_sent_event=True,
)
```

## Security Considerations

1. **Serialization**: Only JSON serialization is allowed (no pickle)
2. **Result Expiration**: Results expire after 1 hour to prevent memory leaks
3. **Time Limits**: Hard limits prevent runaway tasks
4. **Worker Restart**: Workers restart after 1000 tasks to prevent memory leaks
5. **Docker Sandbox**: Tool execution uses Docker for isolation

## Performance Tuning

### Concurrency

```bash
# Default: 2 concurrent processes per worker
CELERY_CONCURRENCY=4 docker-compose up -d xagent-worker

# Or use autoscaling
celery -A xagent.tasks.queue worker --autoscale=10,3
```

### Queue Priorities

Adjust priorities in `src/xagent/tasks/queue.py`:

```python
celery_app.conf.task_routes = {
    "xagent.tasks.worker.my_urgent_task": {"queue": "tools"},  # Priority 9
    "xagent.tasks.worker.my_task": {"queue": "maintenance"},   # Priority 3
}
```

### Resource Limits

Configure in `docker-compose.yml`:

```yaml
xagent-worker:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '0.5'
        memory: 512M
```

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Task Queue Evaluation](TASK_QUEUE_EVALUATION.md)
- [Integration Roadmap](INTEGRATION_ROADMAP.md)
- [Features Documentation](FEATURES.md)

---

**Last Updated**: 2025-11-07  
**Maintainer**: X-Agent Development Team  
**Version**: 1.0
