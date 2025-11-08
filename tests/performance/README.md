# X-Agent Performance Testing

This directory contains performance and load testing tools for X-Agent using Locust.

## Prerequisites

Install Locust:
```bash
pip install locust
```

## Running Tests

### Basic Load Test

Start the API server first:
```bash
# Terminal 1: Start the API
uvicorn xagent.api.rest:app --host 0.0.0.0 --port 8000
```

Run Locust tests:
```bash
# Terminal 2: Run Locust
cd tests/performance
locust -f locustfile.py
```

Then open http://localhost:8089 in your browser to access the Locust web UI.

### Command-Line Testing

Run without web UI (headless mode):

```bash
# Light load: 10 users, spawn rate 2/sec, run for 60 seconds
locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8000

# Medium load: 50 users, spawn rate 5/sec, run for 5 minutes
locust -f locustfile.py --headless -u 50 -r 5 -t 5m --host http://localhost:8000

# Heavy load: 100 users, spawn rate 10/sec, run for 10 minutes
locust -f locustfile.py --headless -u 100 -r 10 -t 10m --host http://localhost:8000
```

### Test Specific User Types

Test only unauthenticated users:
```bash
locust -f locustfile.py --headless -u 20 -r 2 -t 2m --host http://localhost:8000 XAgentAPIUser
```

Test authenticated users:
```bash
locust -f locustfile.py --headless -u 20 -r 2 -t 2m --host http://localhost:8000 XAgentAuthenticatedUser
```

Stress test:
```bash
locust -f locustfile.py --headless -u 100 -r 20 -t 5m --host http://localhost:8000 XAgentStressUser
```

### Testing Against Production

```bash
locust -f locustfile.py --host https://xagent.example.com
```

## Test Scenarios

### 1. XAgentAPIUser (Default)

Simulates typical unauthenticated API usage:
- **GET /status** (weight: 3) - Most common operation
- **GET /goals** (weight: 2) - List goals
- **POST /goals** (weight: 1) - Create goals
- **GET /health** (weight: 1) - Health checks
- **GET /ready** (weight: 2) - Readiness checks

Wait time: 1-3 seconds between requests

### 2. XAgentAuthenticatedUser

Simulates authenticated users with valid JWT tokens:
- Logs in on start to get token
- Higher frequency operations
- Full CRUD operations on goals

Wait time: 0.5-2 seconds between requests

### 3. XAgentStressUser

High-frequency stress testing:
- Rapid health and status checks
- Minimal wait time (0.1-0.5 seconds)
- Tests system under extreme load

## Interpreting Results

### Key Metrics

1. **Response Time (ms)**
   - 50th percentile (median)
   - 95th percentile
   - 99th percentile
   - Maximum

2. **Requests per Second (RPS)**
   - Total throughput
   - Per-endpoint breakdown

3. **Failure Rate (%)**
   - Should be < 1% under normal load
   - Investigate if > 5%

4. **User Count**
   - Maximum concurrent users system can handle

### Performance Targets

| Metric | Target | Acceptable | Poor |
|--------|--------|------------|------|
| Median Response Time | < 100ms | < 200ms | > 500ms |
| 95th Percentile | < 500ms | < 1000ms | > 2000ms |
| Failure Rate | < 0.5% | < 2% | > 5% |
| RPS (per instance) | > 100 | > 50 | < 20 |

### Example Good Results

```
Type     Name                                          # requests    # fails  |  Avg   Min   Max    |  Median   req/s
--------|----------------------------------------------|-------------|--------|----------------------|-------|--------|
GET      /health                                       500           0        |   45    35    120    |    42   8.3
GET      /ready                                        1000          0        |   38    30    95     |    36   16.7
GET      /status                                       1500          5        |   52    40    250    |    48   25.0
--------|----------------------------------------------|-------------|--------|----------------------|-------|--------|
         Aggregated                                    3000          5 (0.17%)|   47    30    250    |    44   50.0
```

### Example Poor Results (Needs Investigation)

```
Type     Name                                          # requests    # fails  |  Avg   Min   Max     |  Median   req/s
--------|----------------------------------------------|-------------|--------|----------------------|-------|--------|
GET      /health                                       500           25       |  1200   100   5000   |  1100   8.3
GET      /status                                       1500          150      |  2500   200   8000   |  2200   25.0
--------|----------------------------------------------|-------------|--------|----------------------|-------|--------|
         Aggregated                                    2000          175 (8.75%)|2100  100   8000   |  1900   33.3
```

## Continuous Performance Testing

### CI/CD Integration

Add to GitHub Actions workflow:

```yaml
- name: Performance Test
  run: |
    pip install locust
    uvicorn xagent.api.rest:app --host 0.0.0.0 --port 8000 &
    sleep 5
    locust -f tests/performance/locustfile.py --headless \
      -u 50 -r 5 -t 2m --host http://localhost:8000 \
      --csv=performance-results --html=performance-report.html
    
- name: Upload Performance Report
  uses: actions/upload-artifact@v3
  with:
    name: performance-report
    path: performance-report.html
```

### Automated Alerts

Set thresholds and fail builds if performance degrades:

```python
# Add to locustfile.py
from locust import events

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    if environment.stats.total.fail_ratio > 0.05:
        print("FAIL: Failure rate exceeded 5%")
        environment.process_exit_code = 1
    if environment.stats.total.avg_response_time > 500:
        print("FAIL: Average response time exceeded 500ms")
        environment.process_exit_code = 1
```

## Monitoring During Tests

### View Metrics

While tests are running, monitor:

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Health status
watch -n 1 curl -s http://localhost:8000/health | jq

# System resources
htop
docker stats  # if running in containers
```

### Grafana Dashboards

Import the X-Agent dashboards and watch:
- Request rate
- Response time
- Error rate
- CPU/Memory usage
- Database connections

## Troubleshooting

### Connection Errors

If you get connection refused errors:
1. Ensure API is running: `curl http://localhost:8000/health`
2. Check firewall settings
3. Verify host and port settings

### High Failure Rates

If failure rates are high:
1. Check API logs for errors
2. Verify database connectivity
3. Check resource limits (CPU, memory)
4. Reduce concurrent users
5. Increase wait times

### Memory Issues

If tests cause memory issues:
1. Reduce number of users
2. Increase spawn rate delay
3. Add cleanup tasks to remove created resources
4. Monitor with `docker stats` or `htop`

## Best Practices

1. **Start Small**: Begin with low user counts and gradually increase
2. **Monitor Resources**: Watch CPU, memory, and database connections
3. **Baseline First**: Establish baseline performance before changes
4. **Test Incrementally**: Test each major change separately
5. **Use Realistic Data**: Match production data patterns
6. **Document Results**: Keep records of performance over time
7. **Test Different Scenarios**: Mix of read/write operations
8. **Consider Network**: Test with realistic network latency

## Advanced Topics

### Distributed Load Testing

Run Locust across multiple machines:

```bash
# Master node
locust -f locustfile.py --master

# Worker nodes (run on multiple machines)
locust -f locustfile.py --worker --master-host=<master-ip>
```

### Custom Reporting

Generate custom reports:

```bash
locust -f locustfile.py --headless -u 50 -r 5 -t 5m \
  --csv=results --html=report.html --json
```

### Profile-Based Testing

Create different load profiles:

```python
# Add to locustfile.py
from locust import LoadTestShape

class CustomLoadShape(LoadTestShape):
    """Gradually increase load over time."""
    
    def tick(self):
        run_time = self.get_run_time()
        if run_time < 60:
            return (10, 1)  # 10 users, spawn 1/sec
        elif run_time < 120:
            return (50, 2)  # 50 users, spawn 2/sec
        elif run_time < 180:
            return (100, 5)  # 100 users, spawn 5/sec
        else:
            return None  # Stop test
```

## Resources

- [Locust Documentation](https://docs.locust.io/)
- [Performance Testing Best Practices](https://martinfowler.com/articles/performance-testing.html)
- [Load Testing vs Stress Testing](https://www.blazemeter.com/blog/performance-testing-vs-load-testing-vs-stress-testing)
