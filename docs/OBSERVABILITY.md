# X-Agent Observability Stack

**Version**: 1.1  
**Last Updated**: 2025-11-07  
**Status**: Production Ready

## Overview

X-Agent includes a comprehensive observability stack for monitoring, tracing, logging, and analyzing agent performance in production environments.

### Components

1. **Prometheus** - Metrics collection and storage
2. **Grafana** - Metrics visualization and dashboards
3. **Jaeger** - Distributed tracing
4. **OpenTelemetry** - Instrumentation framework
5. **Loki** - Log aggregation and storage
6. **Promtail** - Log collection and forwarding

---

## Quick Start

### Local Development

Start the full observability stack:

```bash
docker-compose up -d prometheus grafana jaeger loki promtail
```

Access the services:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Jaeger UI**: http://localhost:16686
- **Loki**: http://localhost:3100
- **Metrics Endpoint**: http://localhost:8000/metrics

---

## Metrics

### Available Metrics

X-Agent exposes comprehensive Prometheus metrics covering all aspects of agent operation:

#### Agent Performance Metrics

```
# Cognitive loop duration
agent_cognitive_loop_duration_seconds

# Total cognitive loop iterations
agent_cognitive_loop_total{status="success|error"}

# Goal completion time
agent_goal_completion_seconds{mode="goal_oriented|continuous"}

# Active goals
agent_active_goals_total{status="pending|in_progress|blocked"}

# Goals created
agent_goals_total{mode="...", status="completed|failed"}

# Think iterations
agent_think_iterations_total{result="action_taken|no_action"}

# Metacognition checks
agent_metacognition_checks_total{trigger="periodic|error|user_request"}
```

#### API Metrics

```
# API request duration
api_request_duration_seconds{method="GET|POST|...", endpoint="...", status="200|404|..."}

# Total API requests
api_requests_total{method="...", endpoint="...", status="..."}

# API errors
api_errors_total{method="...", endpoint="...", error_type="..."}

# Authentication attempts
api_auth_attempts_total{result="success|failure|expired"}

# Active connections
api_active_connections{protocol="http|websocket"}
```

#### Tool Execution Metrics

```
# Tool execution duration
tool_execution_duration_seconds{tool_name="...", status="success|error|timeout"}

# Total tool executions
tool_executions_total{tool_name="...", status="..."}

# Tool errors
tool_errors_total{tool_name="...", error_type="..."}

# Tool queue size
tool_queue_size
```

#### Memory Metrics

```
# Short-term memory entries
memory_short_term_entries

# Vector store entries
memory_vector_entries

# Cache hits/misses
memory_cache_hits_total{cache_type="redis|local"}
memory_cache_misses_total{cache_type="redis|local"}

# Memory operation duration
memory_operations_duration_seconds{operation="read|write|search"}
```

#### Planning Metrics

```
# Planning duration
planner_planning_duration_seconds{strategy="llm|rule_based"}

# Plans created
planner_plans_total{strategy="...", quality="good|acceptable|poor"}

# Plan steps
planner_plan_steps
```

### Querying Metrics

#### Example Prometheus Queries

```promql
# Average API response time (last 5 minutes)
rate(api_request_duration_seconds_sum[5m]) / rate(api_request_duration_seconds_count[5m])

# API request rate by endpoint
sum(rate(api_requests_total[5m])) by (endpoint)

# Error rate
sum(rate(api_errors_total[5m]))

# P95 cognitive loop duration
histogram_quantile(0.95, rate(agent_cognitive_loop_duration_seconds_bucket[5m]))

# Success rate percentage
100 * sum(rate(agent_cognitive_loop_total{status="success"}[5m])) / sum(rate(agent_cognitive_loop_total[5m]))
```

---

## Distributed Tracing

### OpenTelemetry Integration

X-Agent uses OpenTelemetry for distributed tracing, providing detailed insights into request flows and performance bottlenecks.

### Trace Components

#### Automatic Instrumentation

FastAPI is automatically instrumented to trace all HTTP requests:

```python
# Automatic - no code changes needed
GET /goals -> trace created automatically
```

#### Manual Instrumentation

Use the tracing helpers for custom operations:

```python
from xagent.monitoring.tracing import trace_operation, tracing

# Generic operation
with trace_operation("custom_operation", {"key": "value"}):
    # Your code here
    pass

# Cognitive loop phase
with tracing.trace_cognitive_loop("think"):
    # Thinking logic
    pass

# Tool execution
with tracing.trace_tool_execution("code_exec", {"language": "python"}):
    # Execute tool
    pass

# Memory operation
with tracing.trace_memory_operation("search", "vector"):
    # Search memory
    pass

# Planning
with tracing.trace_planning("llm"):
    # Plan generation
    pass

# Goal operations
with tracing.trace_goal_operation("create", goal_id="123"):
    # Goal operation
    pass
```

#### Adding Events and Attributes

```python
from xagent.monitoring.tracing import add_span_event, set_span_attribute

with trace_operation("complex_operation"):
    set_span_attribute("user_id", "user-123")
    
    # ... do work ...
    
    add_span_event("checkpoint_reached", {"checkpoint": "data_validated"})
    
    # ... more work ...
```

### Viewing Traces

1. Open Jaeger UI: http://localhost:16686
2. Select "x-agent-api" service
3. Browse traces by operation, duration, tags
4. Drill down into specific traces to see span details

---

## Log Aggregation

### Loki and Promtail

X-Agent uses Loki for centralized log aggregation and Promtail for log collection from containers and files.

### Log Collection

#### Application Logs

All X-Agent services output structured JSON logs with the following fields:

```json
{
  "timestamp": "2025-11-07T12:34:56.789Z",
  "level": "info",
  "event": "Request processed",
  "logger": "xagent.api.rest",
  "trace_id": "0123456789abcdef0123456789abcdef",
  "span_id": "0123456789abcdef",
  "user_id": "user-123",
  "request_id": "req-456"
}
```

#### Log Correlation with Traces

Logs automatically include `trace_id` and `span_id` when within an active span, enabling correlation between logs and traces:

```python
from xagent.utils.logging import get_logger
from xagent.monitoring.tracing import trace_operation

logger = get_logger(__name__)

with trace_operation("process_request"):
    logger.info("Processing request", user_id="user-123")
    # Log will include trace_id and span_id automatically
```

### Querying Logs

#### Using Grafana Explore

1. Open Grafana: http://localhost:3000
2. Navigate to Explore (compass icon)
3. Select "Loki" data source
4. Use LogQL queries:

```logql
# All logs from xagent
{job="xagent"}

# Error logs only
{job="xagent"} |= "ERROR"

# Logs for a specific trace
{job="xagent"} | json | trace_id="0123456789abcdef0123456789abcdef"

# Logs by service
{service="xagent-api"}

# Logs with specific logger
{job="xagent"} | json | logger="xagent.core.agent"

# Rate of errors in last 5 minutes
sum(rate({job="xagent"} |= "ERROR" [5m]))

# Top 10 loggers by log volume
topk(10, sum by (logger) (count_over_time({job="xagent"}[1h])))
```

#### Using Logs Dashboard

Pre-configured dashboard available at: `config/grafana/dashboards/logs.json`

Features:
- Real-time log streaming
- Error and warning log panels
- Log rate by level and logger
- Docker container logs
- Log search and filtering

### Log Retention

#### Development

- Loki: 7 days retention
- File logs: 30 days rotation

#### Production

Configure in `config/loki-config.yml`:

```yaml
limits_config:
  retention_period: 720h  # 30 days
  
table_manager:
  retention_deletes_enabled: true
  retention_period: 720h
```

### Log Parsing

Promtail automatically parses:
- JSON-formatted application logs
- Docker container logs
- Structured log fields as labels

Custom parsing rules in `config/promtail-config.yml`.

---

## Grafana Dashboards

### Pre-configured Dashboards

X-Agent includes production-ready Grafana dashboards:

#### 1. Agent Performance Dashboard

**File**: `config/grafana/dashboards/agent-performance.json`

Panels:
- Cognitive loop performance (duration, P95, P99)
- Active goals gauge
- Cognitive loop operations (success/error rates)
- Goals created (by mode and status)
- Goal completion time (P50, P95, P99)

#### 2. API Health Dashboard

**File**: `config/grafana/dashboards/api-health.json`

Panels:
- API response time (P50, P95, P99)
- Request rate by endpoint
- HTTP status codes distribution
- Error rate gauge
- Authentication attempts

#### 3. Logs Dashboard

**File**: `config/grafana/dashboards/logs.json`

Panels:
- Real-time application logs
- Error and warning log streams
- Log rate by level
- Log rate by logger
- Docker container logs
- Log volume trends

### Accessing Dashboards

1. Open Grafana: http://localhost:3000
2. Login: admin/admin
3. Navigate to Dashboards
4. Select:
   - "X-Agent - Agent Performance"
   - "X-Agent - API Health"
   - "X-Agent - Logs"

### Creating Custom Dashboards

1. Click "+" → "Dashboard" in Grafana
2. Add Panel
3. Select data source:
   - Prometheus for metrics
   - Jaeger for traces
   - Loki for logs
4. Enter query (PromQL, TraceQL, or LogQL)
5. Configure visualization
6. Save dashboard

---

## Configuration

### Environment Variables

```bash
# OpenTelemetry
OTLP_ENDPOINT=http://jaeger:4317  # Jaeger OTLP collector endpoint
TRACING_CONSOLE=false              # Enable console span exporter for debugging

# Loki
# No environment variables needed - logs automatically forwarded by Promtail

# Prometheus (automatic scraping)
# No additional config needed - metrics exposed at /metrics
```

### Prometheus Configuration

File: `config/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'xagent-api'
    static_configs:
      - targets: ['xagent-api:8000']
```

### Grafana Configuration

Data sources are automatically provisioned via:
- `config/grafana/provisioning/datasources/datasources.yml`
- `config/grafana/provisioning/dashboards/dashboards.yml`

---

## Monitoring Best Practices

### 1. Set Up Alerts

Create alerts for critical metrics:

```yaml
# Example alert rule (Prometheus)
groups:
  - name: xagent_alerts
    rules:
      - alert: HighErrorRate
        expr: sum(rate(api_errors_total[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High API error rate detected"
```

### 2. Monitor Key Metrics

Focus on:
- **API Response Time**: P95 should be < 200ms
- **Error Rate**: Should be < 1%
- **Cognitive Loop Duration**: Monitor for performance degradation
- **Active Goals**: Alert if queue grows too large
- **Memory Usage**: Track memory growth

### 3. Use Distributed Tracing for Debugging

When investigating issues:
1. Check Grafana for metric anomalies
2. Use Jaeger to find slow traces
3. Analyze span details to identify bottlenecks
4. Look for error patterns in traces

### 4. Regular Review

- Review dashboards weekly
- Identify performance trends
- Optimize slow operations
- Clean up unused metrics

---

## Performance Impact

### Metrics Collection

- **CPU Overhead**: < 1%
- **Memory Overhead**: ~10MB
- **Network**: Minimal (metrics scraped every 15s)

### Distributed Tracing

- **CPU Overhead**: < 2%
- **Memory Overhead**: ~20MB
- **Sampling**: All traces captured by default
  - For high-traffic production, consider sampling:
    ```python
    setup_tracing(
        service_name="x-agent-api",
        otlp_endpoint=otlp_endpoint,
        sample_rate=0.1  # Sample 10% of traces
    )
    ```

---

## Troubleshooting

### Metrics Not Appearing

1. Check Prometheus targets: http://localhost:9090/targets
2. Verify `/metrics` endpoint is accessible
3. Check Prometheus scrape config
4. Verify service is running

### Traces Not Showing in Jaeger

1. Verify OTLP_ENDPOINT is set correctly
2. Check Jaeger is running: http://localhost:16686
3. Verify OpenTelemetry instrumentation is initialized
4. Check application logs for tracing errors

### Grafana Dashboard Not Loading

1. Verify Prometheus data source is configured
2. Check dashboard JSON is valid
3. Verify provisioning directories are mounted in Docker
4. Restart Grafana container

### High Memory Usage

1. Reduce trace sampling rate
2. Increase Prometheus retention period
3. Limit metric cardinality (reduce label values)
4. Enable metric scraping less frequently

---

## Production Deployment

### Security

1. **Enable Authentication**:
   ```yaml
   # Grafana
   GF_SECURITY_ADMIN_PASSWORD: <strong-password>
   GF_USERS_ALLOW_SIGN_UP: false
   
   # Prometheus (add auth proxy)
   ```

2. **Network Isolation**:
   - Place observability stack in private network
   - Use reverse proxy for external access
   - Enable TLS for all connections

3. **Access Control**:
   - Restrict metrics endpoint to internal network
   - Use Grafana RBAC for dashboard access
   - Implement API authentication

### Scaling

1. **High Traffic**:
   - Use Prometheus federation for multi-instance scraping
   - Deploy separate Prometheus instances per service
   - Consider Thanos for long-term storage

2. **Tracing at Scale**:
   - Enable trace sampling (10-20%)
   - Use tail-based sampling for errors
   - Deploy Jaeger with Elasticsearch backend

### Backup

1. **Grafana**:
   - Export dashboards regularly
   - Backup grafana.db
   - Version control dashboard JSON

2. **Prometheus**:
   - Use remote write to persistent storage
   - Snapshot TSDB data periodically
   - Consider long-term storage solutions

---

## Next Steps

1. ~~**Phase 3**: Add Loki for log aggregation~~ ✅ **COMPLETE**
2. **Phase 4**: Implement alerting with AlertManager
3. **Phase 5**: Create performance testing dashboards
4. **Phase 6**: Add business metrics and KPIs
5. **Phase 7**: Implement log-based alerting rules

---

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [Promtail Documentation](https://grafana.com/docs/loki/latest/clients/promtail/)

---

**Questions?** Open an issue on GitHub or check the project discussions.
