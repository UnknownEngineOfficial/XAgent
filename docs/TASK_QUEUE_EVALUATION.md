# Task Queue Evaluation: Arq vs Celery

**Date**: 2025-11-07  
**Status**: Decision Made  
**Selected**: Celery

## Overview

This document evaluates Arq and Celery for X-Agent's distributed task queue needs in Phase 3, Week 7-8.

## Comparison Matrix

| Feature | Celery | Arq | Winner |
|---------|--------|-----|--------|
| **Maturity** | Production-ready since 2009 | Relatively new (2017) | Celery |
| **Async Support** | Good (async tasks) | Native async/await | Arq |
| **Broker Support** | Redis, RabbitMQ, SQS, etc. | Redis only | Celery |
| **Result Backend** | Multiple (Redis, PostgreSQL, etc.) | Redis only | Celery |
| **Monitoring** | Flower, Prometheus exporters | Basic built-in | Celery |
| **Scheduled Tasks** | Beat scheduler (robust) | Built-in cron | Tie |
| **Community** | Large, mature ecosystem | Smaller, growing | Celery |
| **Documentation** | Extensive | Good but limited | Celery |
| **Performance** | Good (10k+ tasks/sec) | Excellent (native async) | Arq |
| **Complexity** | More complex, more features | Simple, opinionated | Arq |
| **Integration** | Wide ecosystem support | FastAPI-friendly | Celery |

## Detailed Analysis

### Celery Advantages

1. **Battle-tested**: Used in production by thousands of companies
2. **Feature-rich**: 
   - Multiple broker options (we already use Redis and RabbitMQ could be added)
   - Multiple result backends (PostgreSQL, Redis, etc.)
   - Advanced routing and task priorities
   - Task chains, groups, chords for complex workflows
3. **Monitoring**: 
   - Flower for web-based monitoring
   - Prometheus exporters available
   - Grafana integration proven
4. **Flexibility**: Supports both sync and async tasks
5. **Already in requirements.txt**: No additional dependency needed

### Arq Advantages

1. **Native async**: Built for asyncio from the ground up
2. **Simplicity**: Less configuration, easier to get started
3. **Performance**: Slightly better for async workloads
4. **FastAPI-friendly**: Works seamlessly with FastAPI patterns

### Decision Rationale

**Selected: Celery**

Reasons:
1. **Already installed** (celery>=5.3.0 in requirements.txt)
2. **Production readiness**: Proven at scale with extensive tooling
3. **Observability**: Better integration with our existing monitoring stack (Prometheus, Grafana)
4. **Flexibility**: Multiple brokers/backends align with our infrastructure
5. **Community support**: Larger ecosystem for troubleshooting and plugins
6. **Complex workflows**: We may need task chains, groups, and chords for agent orchestration

While Arq's simplicity is appealing, Celery's maturity and feature set better match our requirements for a production-ready system with comprehensive observability.

## Implementation Plan

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI App                         │
│  ┌────────────────┐  ┌────────────────┐                │
│  │ REST Endpoints │  │   WebSocket    │                │
│  └────────┬───────┘  └────────┬───────┘                │
└───────────┼────────────────────┼─────────────────────────┘
            │                    │
            │ Enqueue Task       │
            ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                    Celery Workers                       │
│  ┌────────────────┐  ┌────────────────┐                │
│  │ Cognitive Loop │  │  Tool Executor │                │
│  │     Tasks      │  │     Tasks      │                │
│  └────────┬───────┘  └────────┬───────┘                │
└───────────┼────────────────────┼─────────────────────────┘
            │                    │
            │   Store Result     │
            ▼                    ▼
┌─────────────────────────────────────────────────────────┐
│                      Redis                              │
│  ┌────────────────┐  ┌────────────────┐                │
│  │     Broker     │  │ Result Backend │                │
│  └────────────────┘  └────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

### Key Components

1. **Celery App** (`src/xagent/tasks/queue.py`)
   - Configure Celery with Redis broker
   - Set up result backend (Redis)
   - Configure task routing
   - Add task monitoring hooks

2. **Task Definitions** (`src/xagent/tasks/worker.py`)
   - `execute_cognitive_loop`: Main agent thinking task
   - `execute_tool`: Tool execution task
   - `process_goal`: Goal processing task
   - `cleanup_memory`: Background cleanup task

3. **Worker Management** (`src/xagent/tasks/worker.py`)
   - Worker configuration
   - Signal handlers
   - Health check integration
   - Graceful shutdown

4. **Docker Integration** (`docker-compose.yml`)
   - Celery worker service
   - Health checks
   - Resource limits
   - Auto-scaling configuration

5. **Monitoring** (`src/xagent/monitoring/task_metrics.py`)
   - Task execution metrics
   - Queue depth metrics
   - Worker health metrics
   - Integration with Prometheus

### Task Types

1. **Real-time Tasks** (priority: high)
   - Tool execution
   - API request processing
   - User interactions

2. **Background Tasks** (priority: medium)
   - Cognitive loop iterations
   - Goal decomposition
   - Planning operations

3. **Maintenance Tasks** (priority: low)
   - Memory cleanup
   - Log rotation
   - Metrics aggregation

### Configuration

```python
# Celery Configuration
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/1"
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 270  # 4.5 minutes
```

## Testing Strategy

1. **Unit Tests**:
   - Task serialization
   - Task routing
   - Error handling
   - Retry logic

2. **Integration Tests**:
   - End-to-end task execution
   - Task chaining
   - Result retrieval
   - Worker health checks

3. **Performance Tests**:
   - Task throughput
   - Latency under load
   - Worker scaling
   - Queue depth management

## Success Metrics

1. **Performance**:
   - Task latency < 100ms (p95)
   - Throughput > 1000 tasks/sec
   - Worker startup time < 5s

2. **Reliability**:
   - Task failure rate < 0.1%
   - Automatic retry success rate > 90%
   - Zero task loss

3. **Observability**:
   - Real-time queue depth monitoring
   - Task execution traces
   - Worker health metrics
   - Alert on queue saturation

## Next Steps

1. Implement Celery app configuration
2. Define core tasks
3. Set up worker management
4. Add Docker integration
5. Implement monitoring
6. Write comprehensive tests
7. Update documentation

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Arq Documentation](https://arq-docs.helpmanual.io/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#best-practices)

---

**Decision Date**: 2025-11-07  
**Decided By**: X-Agent Development Team  
**Review Date**: 2025-12-07 (1 month)
