# Quick Start: Monitoring & Performance Tracking

**Last Updated**: 2025-11-13  
**Version**: 1.0  

This guide helps you quickly get started with X-Agent's monitoring, alerting, and performance baseline systems.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Starting the Monitoring Stack](#starting-the-monitoring-stack)
3. [Performance Baseline](#performance-baseline)
4. [Alert Management](#alert-management)
5. [Viewing Metrics](#viewing-metrics)
6. [Common Tasks](#common-tasks)

---

## Prerequisites

Ensure you have:
- Docker and Docker Compose installed
- X-Agent repository cloned
- Environment configured (`.env` file from `.env.example`)

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

---

## Starting the Monitoring Stack

### Full Stack (Recommended for Production)

Start all services including monitoring:

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Expected services:
# - xagent-api       (Main API)
# - xagent-worker    (Celery worker)
# - redis            (Cache)
# - postgres         (Database)
# - prometheus       (Metrics)
# - grafana          (Dashboards)
# - jaeger           (Tracing)
# - opa              (Policy engine)
```

### Monitoring Only (For Development)

Start just the monitoring services:

```bash
# Start monitoring stack
docker-compose up -d prometheus grafana jaeger

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)
# Jaeger:     http://localhost:16686
```

---

## Performance Baseline

### Creating a Baseline

Create a performance baseline for regression detection:

```bash
# Create baseline with default output
python scripts/create_performance_baseline.py

# Create baseline with custom output path
python scripts/create_performance_baseline.py --output my-baseline.json

# Output will be saved to benchmark_results/baseline.json
```

**What gets measured:**
- Cognitive loop latency (P50, P95, P99)
- Memory operations (read latency, write rate)
- Planning performance (simple, complex)
- Goal management (creation rate, query latency)
- Tool execution (action latency)
- End-to-end workflows

**Baseline structure:**
```json
{
  "created_at": "2025-11-13T...",
  "version": "0.1.0",
  "benchmarks": {
    "cognitive_loop": { ... },
    "memory": { ... },
    "planning": { ... },
    "goals": { ... },
    "tools": { ... },
    "e2e": { ... }
  },
  "thresholds": {
    "cognitive_loop_latency_ms": 27.73,
    ...
  },
  "regression_tolerance": {
    "percentage": 10,
    "note": "Thresholds set at 10% above baseline"
  }
}
```

### Running Benchmarks

Run performance benchmarks:

```bash
# Run all performance tests
pytest tests/performance/ --benchmark-only

# Run specific benchmark
pytest tests/performance/test_cognitive_loop_benchmark.py --benchmark-only

# Save results to JSON
pytest tests/performance/ --benchmark-only --benchmark-json=benchmark_results/current.json
```

### Comparing Against Baseline

Compare current performance against baseline:

```bash
# Compare with default baseline
python scripts/compare_benchmarks.py \
  --baseline benchmark_results/baseline.json \
  --current benchmark_results/current.json

# Exit codes:
# 0 - No regressions detected (CI PASS)
# 1 - Regressions detected (CI FAIL)
# 2 - Error reading files
```

**Output example:**
```
╭─────────────────────────────────────╮
│ Benchmark Comparison Report         │
╰─────────────────────────────────────╯

Summary:
  Total Metrics: 8
  Regressions: 0
  Improvements: 2
  Stable: 6

┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Metric                 ┃ Current  ┃ Threshold ┃ Change  ┃ Status      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Cognitive Loop P95     │  24.1ms  │  27.7ms   │  -2.3%  │ IMPROVED    │
│ Memory Write Rate      │  950/sec │  836/sec  │  +1.1%  │ STABLE      │
...
└────────────────────────┴──────────┴───────────┴─────────┴─────────────┘

✅ No performance regressions detected
```

### Integrating with CI/CD

Add to your CI pipeline (`.github/workflows/ci.yml`):

```yaml
- name: Run Performance Benchmarks
  run: |
    pytest tests/performance/ --benchmark-only --benchmark-json=benchmark_results/current.json

- name: Compare Against Baseline
  run: |
    python scripts/compare_benchmarks.py \
      --baseline benchmark_results/baseline.json \
      --current benchmark_results/current.json
```

---

## Alert Management

### Understanding Alert Severity

Alerts are categorized by severity:

- **Critical** (🔴): Immediate action required
  - API down
  - Database down
  - Cognitive loop stuck
  - Service unavailable

- **High** (🟠): Prompt attention needed
  - High error rate
  - High failure rate
  - Authentication failures
  - Tool execution failures

- **Warning** (🟡): Monitor and investigate
  - High latency
  - High resource usage
  - Low goal completion rate
  - Large task queue

### Viewing Active Alerts

```bash
# Via Prometheus UI
open http://localhost:9090/alerts

# Via API
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts'

# Via CLI
docker exec prometheus promtool query instant \
  http://localhost:9090 \
  'ALERTS{alertstate="firing"}'
```

### Alert Rules

All alert rules are defined in `config/alerting/prometheus-rules.yml`:

**Categories:**
1. **API Alerts**: Service availability, error rates, latency
2. **Agent Alerts**: Cognitive loop health, failure rates
3. **Resource Alerts**: CPU, memory, disk usage
4. **Database Alerts**: Redis, PostgreSQL, ChromaDB health
5. **Tool Alerts**: Tool execution, sandbox availability
6. **Worker Alerts**: Celery worker health, task queue

### Responding to Alerts

When an alert fires:

1. **Check the runbook**: `docs/ALERT_RUNBOOKS.md`
2. **Find the alert section**: Each alert has detailed runbook
3. **Follow investigation steps**: Diagnostic commands provided
4. **Apply resolution steps**: Fix procedures documented
5. **Document the incident**: Post-mortem template included

**Example runbook lookup:**

```bash
# Search for specific alert
grep -A 30 "XAgentAPIDown" docs/ALERT_RUNBOOKS.md

# View all critical alerts
grep -B 2 "Severity.*Critical" docs/ALERT_RUNBOOKS.md
```

### Silencing Alerts

Temporarily silence alerts during maintenance:

```bash
# Silence specific alert (1 hour)
curl -X POST http://localhost:9093/api/v2/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "alertname",
        "value": "XAgentAPIDown",
        "isRegex": false
      }
    ],
    "startsAt": "2025-11-13T23:00:00Z",
    "endsAt": "2025-11-14T00:00:00Z",
    "createdBy": "admin",
    "comment": "Scheduled maintenance"
  }'
```

---

## Viewing Metrics

### Prometheus

Access Prometheus at http://localhost:9090

**Useful queries:**

```promql
# CPU usage
rate(process_cpu_seconds_total{job="xagent-api"}[5m])

# Memory usage
process_resident_memory_bytes{job="xagent-api"} / 1024 / 1024

# Request rate
rate(http_requests_total{job="xagent-api"}[5m])

# Error rate
rate(http_requests_total{job="xagent-api",status=~"5.."}[5m])

# P95 latency
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket{job="xagent-api"}[5m])
)

# Task success rate
rate(agent_tasks_completed_total{status="success"}[5m]) 
/ 
rate(agent_tasks_completed_total[5m])
```

### Grafana

Access Grafana at http://localhost:3000 (default: admin/admin)

**Pre-configured dashboards:**

1. **X-Agent Overview**
   - Service health
   - Request rates
   - Error rates
   - Latency percentiles

2. **Agent Performance**
   - Cognitive loop metrics
   - Goal completion rates
   - Tool execution stats
   - Memory operations

3. **Infrastructure**
   - Resource usage (CPU, Memory, Disk)
   - Database health
   - Cache performance
   - Queue metrics

**Importing dashboards:**

```bash
# Dashboards are in config/grafana/dashboards/
ls config/grafana/dashboards/

# Auto-imported on startup via provisioning
```

### Jaeger (Distributed Tracing)

Access Jaeger at http://localhost:16686

**Finding traces:**

1. **Select service**: `xagent-api`
2. **Select operation**: e.g., `/api/v1/agent/execute`
3. **Set time range**: Last hour
4. **Click "Find Traces"**

**Trace details show:**
- Request flow through components
- Time spent in each operation
- Database queries
- External API calls
- Errors and exceptions

---

## Common Tasks

### Task 1: Validate System Health

```bash
# 1. Check all services are running
docker-compose ps

# 2. Test API health
curl http://localhost:8000/health

# 3. Check metrics endpoint
curl http://localhost:8000/metrics | head -20

# 4. View active alerts
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts | length'

# 5. Verify database connections
docker exec postgres pg_isready
redis-cli -h localhost ping
```

### Task 2: Monitor a Deployment

```bash
# Before deployment - create baseline
python scripts/create_performance_baseline.py --output baseline-pre-deploy.json

# Deploy new version
docker-compose up -d --build

# Wait for warmup (2 minutes)
sleep 120

# Run benchmarks
pytest tests/performance/ --benchmark-only --benchmark-json=current-post-deploy.json

# Compare performance
python scripts/compare_benchmarks.py \
  --baseline baseline-pre-deploy.json \
  --current current-post-deploy.json

# If regressions detected, rollback
if [ $? -eq 1 ]; then
  docker-compose down
  git checkout HEAD~1
  docker-compose up -d --build
fi
```

### Task 3: Investigate High Latency

```bash
# 1. Check P95 latency in Prometheus
curl 'http://localhost:9090/api/v1/query' \
  --data 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'

# 2. Identify slow endpoints
curl 'http://localhost:9090/api/v1/query' \
  --data 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) by (path)' \
  | jq '.data.result | sort_by(.value[1] | tonumber) | reverse | .[0:5]'

# 3. Check for slow database queries
docker exec postgres psql -U xagent -c "
  SELECT query, calls, total_time, mean_time
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;
"

# 4. View traces for slow requests
# Open Jaeger UI and filter by duration > 1000ms
```

### Task 4: Debug Memory Growth

```bash
# 1. Monitor memory over time
watch -n 5 'docker stats xagent-api --no-stream --format "{{.MemUsage}}"'

# 2. Check Redis memory
redis-cli info memory | grep used_memory_human

# 3. Check for large objects
redis-cli --bigkeys

# 4. Python memory profiling
docker exec xagent-api python -c "
import tracemalloc
tracemalloc.start()
# ... run your code ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
"
```

### Task 5: Analyze Failed Tasks

```bash
# 1. Get failure rate
curl 'http://localhost:9090/api/v1/query' \
  --data 'query=rate(agent_tasks_completed_total{status="failure"}[5m]) / rate(agent_tasks_completed_total[5m])'

# 2. View recent failures in logs
docker logs xagent-api --since 1h | grep "ERROR" | grep "task_execution"

# 3. Check failure reasons
docker logs xagent-api --since 1h | grep "ERROR" | \
  awk -F'"reason":' '{print $2}' | sort | uniq -c | sort -rn

# 4. View failed tasks in database
docker exec postgres psql -U xagent -c "
  SELECT id, goal_id, error_message, created_at
  FROM actions
  WHERE status = 'failed'
  ORDER BY created_at DESC
  LIMIT 10;
"
```

---

## Best Practices

### Performance Baseline

1. **Create baseline in stable environment**: Minimal load, no background tasks
2. **Update baseline after major changes**: New features, architecture changes
3. **Run multiple times**: Average 3-5 runs for consistency
4. **Document baselines**: Tag with version, date, environment
5. **Archive old baselines**: Keep history for trend analysis

### Alert Management

1. **Start conservative**: Better too many alerts than missing critical issues
2. **Tune thresholds**: Adjust based on actual system behavior
3. **Document responses**: Update runbooks with learnings
4. **Test alert rules**: Manually trigger to verify notification chain
5. **Regular reviews**: Monthly review of alert effectiveness

### Monitoring

1. **Check dashboards daily**: Quick health check
2. **Review metrics weekly**: Identify trends
3. **Analyze traces for slow requests**: Find optimization opportunities
4. **Set up notifications**: Email/Slack for critical alerts
5. **Maintain documentation**: Keep runbooks updated

---

## Troubleshooting

### Prometheus not scraping metrics

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'

# Verify metrics endpoint is accessible
curl http://xagent-api:8000/metrics

# Check Prometheus config
docker exec prometheus cat /etc/prometheus/prometheus.yml

# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload
```

### Grafana not showing data

```bash
# Check Grafana datasource
curl http://localhost:3000/api/datasources | jq '.'

# Test datasource connection
docker logs grafana | grep "datasource"

# Verify Prometheus is reachable from Grafana
docker exec grafana curl http://prometheus:9090/api/v1/query?query=up
```

### Alerts not firing

```bash
# Check alert rules are loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | .name'

# Check rule evaluation
docker logs prometheus | grep "rule"

# Verify AlertManager is configured
curl http://localhost:9090/api/v1/alertmanagers | jq '.'

# Test alert manually
# (Trigger condition that should fire alert)
```

---

## Additional Resources

- **Alert Runbooks**: `docs/ALERT_RUNBOOKS.md`
- **Performance Baseline**: `scripts/create_performance_baseline.py`
- **Benchmark Comparison**: `scripts/compare_benchmarks.py`
- **Results Report**: `RESULTS_2025-11-13.md`
- **Features Documentation**: `FEATURES.md`

---

**Questions or Issues?**

- Open an issue: https://github.com/UnknownEngineOfficial/XAgent/issues
- Check documentation: `/docs/`
- Review examples: `/examples/`

---

**Last Updated**: 2025-11-13  
**Maintained By**: X-Agent Team  
**Version**: 1.0
