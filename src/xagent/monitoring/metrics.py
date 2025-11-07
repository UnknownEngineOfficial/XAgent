"""Enhanced Prometheus metrics for X-Agent.

Provides comprehensive metrics collection for agent performance,
API usage, tool execution, and system health.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import time

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


# Create custom registry for better control
registry = CollectorRegistry()


# ============================================================================
# Agent Performance Metrics
# ============================================================================

agent_cognitive_loop_duration = Histogram(
    "agent_cognitive_loop_duration_seconds",
    "Time spent in cognitive loop iteration",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
)

agent_cognitive_loop_total = Counter(
    "agent_cognitive_loop_total",
    "Total number of cognitive loop iterations",
    ["status"],  # success, error
    registry=registry,
)

agent_goal_completion_time = Histogram(
    "agent_goal_completion_seconds",
    "Time taken to complete goals",
    ["mode"],  # goal_oriented, continuous
    buckets=[10, 30, 60, 300, 600, 1800, 3600],
    registry=registry,
)

agent_active_goals = Gauge(
    "agent_active_goals_total",
    "Current number of active goals",
    ["status"],  # pending, in_progress, blocked
    registry=registry,
)

agent_goals_total = Counter(
    "agent_goals_total",
    "Total number of goals created",
    ["mode", "status"],  # mode: goal_oriented/continuous, status: completed/failed
    registry=registry,
)

agent_think_iterations = Counter(
    "agent_think_iterations_total",
    "Number of think/reasoning iterations",
    ["result"],  # action_taken, no_action
    registry=registry,
)

agent_metacognition_checks = Counter(
    "agent_metacognition_checks_total",
    "Number of metacognition self-checks performed",
    ["trigger"],  # periodic, error, user_request
    registry=registry,
)


# ============================================================================
# API Metrics
# ============================================================================

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    registry=registry,
)

api_requests_total = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

api_errors_total = Counter(
    "api_errors_total",
    "Total API errors",
    ["method", "endpoint", "error_type"],
    registry=registry,
)

api_auth_attempts_total = Counter(
    "api_auth_attempts_total",
    "Total authentication attempts",
    ["result"],  # success, failure, expired
    registry=registry,
)

api_active_connections = Gauge(
    "api_active_connections",
    "Number of active API connections",
    ["protocol"],  # http, websocket
    registry=registry,
)


# ============================================================================
# Tool Execution Metrics
# ============================================================================

tool_execution_duration = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name", "status"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
)

tool_executions_total = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"],  # success, error, timeout
    registry=registry,
)

tool_errors_total = Counter(
    "tool_errors_total",
    "Tool execution errors",
    ["tool_name", "error_type"],
    registry=registry,
)

tool_queue_size = Gauge(
    "tool_queue_size",
    "Number of tools waiting in execution queue",
    registry=registry,
)


# ============================================================================
# Memory Metrics
# ============================================================================

memory_short_term_entries = Gauge(
    "memory_short_term_entries",
    "Number of entries in short-term memory",
    registry=registry,
)

memory_vector_store_entries = Gauge(
    "memory_vector_entries",
    "Number of entries in vector store",
    registry=registry,
)

memory_cache_hits_total = Counter(
    "memory_cache_hits_total",
    "Total cache hits",
    ["cache_type"],  # redis, local
    registry=registry,
)

memory_cache_misses_total = Counter(
    "memory_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
    registry=registry,
)

memory_operations_duration = Histogram(
    "memory_operations_duration_seconds",
    "Memory operation duration",
    ["operation"],  # read, write, search
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry,
)


# ============================================================================
# System Resource Metrics
# ============================================================================

system_cpu_usage = Gauge(
    "system_cpu_usage_percent",
    "CPU usage percentage",
    registry=registry,
)

system_memory_usage = Gauge(
    "system_memory_usage_bytes",
    "Memory usage in bytes",
    registry=registry,
)

system_disk_usage = Gauge(
    "system_disk_usage_bytes",
    "Disk usage in bytes",
    ["mount_point"],
    registry=registry,
)


# ============================================================================
# Planning Metrics
# ============================================================================

planner_planning_duration = Histogram(
    "planner_planning_duration_seconds",
    "Time taken to create plans",
    ["strategy"],  # llm, rule_based
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registry=registry,
)

planner_plans_total = Counter(
    "planner_plans_total",
    "Total plans created",
    ["strategy", "quality"],  # quality: good, acceptable, poor
    registry=registry,
)

planner_plan_steps = Histogram(
    "planner_plan_steps",
    "Number of steps in generated plans",
    buckets=[1, 3, 5, 10, 20, 50],
    registry=registry,
)


# ============================================================================
# Agent Information
# ============================================================================

agent_info = Info(
    "agent",
    "Agent information",
    registry=registry,
)

# Set static agent info
agent_info.info({
    "version": "0.1.0",
    "name": "X-Agent",
    "mode": "interactive",
})


# ============================================================================
# Helper Classes
# ============================================================================

class MetricsCollector:
    """Helper class for collecting and managing metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.start_times: Dict[str, float] = {}
        self._max_start_times = 1000  # Limit to prevent memory leaks
        logger.info("Metrics collector initialized")
    
    def _cleanup_old_start_times(self):
        """Remove old start times to prevent memory leaks."""
        if len(self.start_times) > self._max_start_times:
            # Remove oldest 20% of entries
            import time
            current_time = time.time()
            cutoff_time = current_time - 3600  # 1 hour ago
            
            self.start_times = {
                key: value
                for key, value in self.start_times.items()
                if value > cutoff_time
            }
            logger.warning(
                f"Cleaned up orphaned timing entries. Remaining: {len(self.start_times)}"
            )
    
    # Agent metrics
    
    def record_cognitive_loop(self, duration: float, status: str = "success"):
        """Record cognitive loop execution."""
        agent_cognitive_loop_duration.observe(duration)
        agent_cognitive_loop_total.labels(status=status).inc()
    
    def record_goal_completion(self, duration: float, mode: str = "goal_oriented"):
        """Record goal completion time."""
        agent_goal_completion_time.labels(mode=mode).observe(duration)
    
    def update_active_goals(self, pending: int = 0, in_progress: int = 0, blocked: int = 0):
        """Update active goals gauge."""
        agent_active_goals.labels(status="pending").set(pending)
        agent_active_goals.labels(status="in_progress").set(in_progress)
        agent_active_goals.labels(status="blocked").set(blocked)
    
    def record_goal_created(self, mode: str, status: str):
        """Record goal creation and completion."""
        agent_goals_total.labels(mode=mode, status=status).inc()
    
    def record_think_iteration(self, result: str = "action_taken"):
        """Record think/reasoning iteration."""
        agent_think_iterations.labels(result=result).inc()
    
    def record_metacognition_check(self, trigger: str = "periodic"):
        """Record metacognition check."""
        agent_metacognition_checks.labels(trigger=trigger).inc()
    
    # API metrics
    
    def start_api_request(self, request_id: str):
        """Start timing an API request."""
        self._cleanup_old_start_times()
        self.start_times[f"api_{request_id}"] = time.time()
    
    def record_api_request(
        self,
        request_id: str,
        method: str,
        endpoint: str,
        status: int,
    ):
        """Record API request completion."""
        key = f"api_{request_id}"
        if key in self.start_times:
            duration = time.time() - self.start_times[key]
            api_request_duration.labels(
                method=method,
                endpoint=endpoint,
                status=str(status),
            ).observe(duration)
            del self.start_times[key]
        
        api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status),
        ).inc()
    
    def record_api_error(self, method: str, endpoint: str, error_type: str):
        """Record API error."""
        api_errors_total.labels(
            method=method,
            endpoint=endpoint,
            error_type=error_type,
        ).inc()
    
    def record_auth_attempt(self, result: str):
        """Record authentication attempt."""
        api_auth_attempts_total.labels(result=result).inc()
    
    def update_active_connections(self, count: int, protocol: str = "http"):
        """Update active connections gauge."""
        api_active_connections.labels(protocol=protocol).set(count)
    
    # Tool metrics
    
    def start_tool_execution(self, tool_name: str, execution_id: str):
        """Start timing tool execution."""
        self._cleanup_old_start_times()
        self.start_times[f"tool_{execution_id}"] = time.time()
    
    def record_tool_execution(
        self,
        tool_name: str,
        execution_id: str,
        status: str = "success",
    ):
        """Record tool execution completion."""
        key = f"tool_{execution_id}"
        if key in self.start_times:
            duration = time.time() - self.start_times[key]
            tool_execution_duration.labels(
                tool_name=tool_name,
                status=status,
            ).observe(duration)
            del self.start_times[key]
        
        tool_executions_total.labels(
            tool_name=tool_name,
            status=status,
        ).inc()
    
    def record_tool_error(self, tool_name: str, error_type: str):
        """Record tool error."""
        tool_errors_total.labels(
            tool_name=tool_name,
            error_type=error_type,
        ).inc()
    
    def update_tool_queue_size(self, size: int):
        """Update tool queue size."""
        tool_queue_size.set(size)
    
    # Memory metrics
    
    def update_memory_stats(
        self,
        short_term: int = 0,
        vector_store: int = 0,
    ):
        """Update memory statistics."""
        memory_short_term_entries.set(short_term)
        memory_vector_store_entries.set(vector_store)
    
    def record_cache_access(self, hit: bool, cache_type: str = "redis"):
        """Record cache hit or miss."""
        if hit:
            memory_cache_hits_total.labels(cache_type=cache_type).inc()
        else:
            memory_cache_misses_total.labels(cache_type=cache_type).inc()
    
    def record_memory_operation(self, operation: str, duration: float):
        """Record memory operation duration."""
        memory_operations_duration.labels(operation=operation).observe(duration)
    
    # Planning metrics
    
    def record_planning(
        self,
        duration: float,
        strategy: str,
        quality: str,
        num_steps: int,
    ):
        """Record planning operation."""
        planner_planning_duration.labels(strategy=strategy).observe(duration)
        planner_plans_total.labels(strategy=strategy, quality=quality).inc()
        planner_plan_steps.observe(num_steps)
    
    # System metrics
    
    def update_system_metrics(
        self,
        cpu_percent: Optional[float] = None,
        memory_bytes: Optional[int] = None,
        disk_usage: Optional[Dict[str, int]] = None,
    ):
        """Update system resource metrics."""
        if cpu_percent is not None:
            system_cpu_usage.set(cpu_percent)
        
        if memory_bytes is not None:
            system_memory_usage.set(memory_bytes)
        
        if disk_usage:
            for mount_point, usage in disk_usage.items():
                system_disk_usage.labels(mount_point=mount_point).set(usage)
    
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(registry)
    
    def get_content_type(self) -> str:
        """Get content type for metrics response."""
        return CONTENT_TYPE_LATEST


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create metrics collector singleton."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
