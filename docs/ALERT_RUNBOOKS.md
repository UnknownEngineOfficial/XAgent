# X-Agent Alert Runbooks

**Purpose**: This document provides runbooks for responding to alerts fired by the X-Agent monitoring system.

**Last Updated**: 2025-11-13  
**Version**: 1.0  

---

## Table of Contents

1. [API Alerts](#api-alerts)
2. [Agent Alerts](#agent-alerts)
3. [Resource Alerts](#resource-alerts)
4. [Database Alerts](#database-alerts)
5. [Tool Alerts](#tool-alerts)
6. [Worker Alerts](#worker-alerts)
7. [General Response Procedures](#general-response-procedures)

---

## API Alerts

### XAgentAPIDown

**Severity**: Critical  
**Description**: The X-Agent API is not responding

#### Investigation Steps

1. Check if the API container/pod is running:
   ```bash
   # Docker
   docker ps | grep xagent-api
   docker logs xagent-api --tail 100
   
   # Kubernetes
   kubectl get pods -l app=xagent-api
   kubectl logs -l app=xagent-api --tail=100
   ```

2. Check API health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

3. Review recent logs for errors:
   ```bash
   # Check for crashes
   docker logs xagent-api --since 10m | grep -i error
   
   # Check application logs
   tail -f /var/log/xagent/api.log
   ```

#### Resolution Steps

1. **If container crashed**: Restart the service
   ```bash
   # Docker
   docker restart xagent-api
   
   # Kubernetes
   kubectl rollout restart deployment/xagent-api
   ```

2. **If OOM (Out of Memory)**: Increase memory limits
   ```bash
   # Edit docker-compose.yml or k8s deployment
   # Increase memory limit from 512Mi to 1Gi
   ```

3. **If connection issues**: Check network and dependencies
   ```bash
   # Test Redis connection
   redis-cli -h redis -p 6379 ping
   
   # Test PostgreSQL connection
   psql -h postgres -U xagent -c "SELECT 1"
   ```

4. **If persistent issues**: Check for deployment problems
   ```bash
   # Revert to last known good version
   kubectl rollout undo deployment/xagent-api
   ```

---

### XAgentHighErrorRate

**Severity**: High  
**Description**: More than 5% of API requests are returning 5xx errors

#### Investigation Steps

1. Check which endpoints are failing:
   ```bash
   # Query Prometheus for error breakdown
   curl 'http://prometheus:9090/api/v1/query' \
     --data 'query=rate(http_requests_total{status=~"5.."}[5m]) by (path)'
   ```

2. Review application logs:
   ```bash
   docker logs xagent-api --tail 500 | grep "ERROR\|500\|502\|503"
   ```

3. Check for resource exhaustion:
   ```bash
   # CPU and memory usage
   docker stats xagent-api
   ```

4. Check dependency health:
   ```bash
   # Redis health
   redis-cli -h redis info | grep -E 'used_memory|connected_clients'
   
   # PostgreSQL health
   psql -h postgres -U xagent -c "SELECT count(*) FROM pg_stat_activity"
   ```

#### Resolution Steps

1. **If database connection issues**: Check connection pool
   ```python
   # In Python console or script
   from xagent.database import get_db
   db = next(get_db())
   # Test query
   db.execute("SELECT 1")
   ```

2. **If specific endpoint failing**: Disable problematic endpoint temporarily
   ```bash
   # Add to .env
   DISABLE_ENDPOINT_X=true
   docker restart xagent-api
   ```

3. **If widespread issues**: Scale up resources or instances
   ```bash
   # Kubernetes - scale replicas
   kubectl scale deployment xagent-api --replicas=5
   
   # Docker - increase resources
   docker update --memory=2g --cpus=2 xagent-api
   ```

---

### XAgentHighLatency

**Severity**: Warning  
**Description**: 95th percentile API latency exceeds 2 seconds

#### Investigation Steps

1. Identify slow endpoints:
   ```bash
   # Query Prometheus
   curl 'http://prometheus:9090/api/v1/query' \
     --data 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) by (path)'
   ```

2. Check for slow database queries:
   ```sql
   -- PostgreSQL slow queries
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;
   ```

3. Profile the application:
   ```bash
   # Enable profiling endpoint
   curl http://localhost:8000/debug/pprof/profile?seconds=30 > profile.pb.gz
   ```

4. Check for external API delays:
   ```bash
   # Review HTTP client metrics
   curl 'http://prometheus:9090/api/v1/query' \
     --data 'query=http_client_request_duration_seconds{quantile="0.95"}'
   ```

#### Resolution Steps

1. **If database queries slow**: Add indexes or optimize queries
   ```sql
   -- Example: Add index on frequently queried column
   CREATE INDEX idx_goals_status ON goals(status);
   ```

2. **If caching issue**: Clear and warm cache
   ```bash
   # Clear Redis cache
   redis-cli FLUSHDB
   
   # Warm cache with common queries
   python scripts/warm_cache.py
   ```

3. **If external API slow**: Implement timeouts and circuit breakers
   ```python
   # Already implemented in HttpClient
   # Adjust timeout values in config
   HTTP_CLIENT_TIMEOUT=10  # seconds
   ```

4. **If resource constrained**: Scale horizontally
   ```bash
   kubectl scale deployment xagent-api --replicas=10
   ```

---

## Agent Alerts

### XAgentCognitiveLoopStuck

**Severity**: Critical  
**Description**: Cognitive loop hasn't completed an iteration in 5+ minutes

#### Investigation Steps

1. Check agent state:
   ```bash
   # Query agent status endpoint
   curl http://localhost:8000/api/v1/agent/status
   ```

2. Check for deadlocks:
   ```bash
   # Review locks in PostgreSQL
   psql -h postgres -U xagent -c "SELECT * FROM pg_locks WHERE NOT granted"
   ```

3. Review cognitive loop logs:
   ```bash
   docker logs xagent-api | grep -i "cognitive_loop" | tail -100
   ```

4. Check for infinite loops:
   ```bash
   # Look for repeated patterns
   docker logs xagent-api | tail -1000 | sort | uniq -c | sort -rn
   ```

#### Resolution Steps

1. **If deadlock**: Restart agent gracefully
   ```bash
   # Send SIGTERM for graceful shutdown
   docker kill --signal=SIGTERM xagent-api
   docker start xagent-api
   ```

2. **If infinite loop in goal**: Cancel problematic goal
   ```python
   # Via API or CLI
   xagent goal cancel <goal_id>
   ```

3. **If resource starved**: Increase CPU/memory
   ```bash
   docker update --cpus=4 --memory=4g xagent-api
   ```

4. **If persistent**: Enable checkpoint and resume
   ```bash
   # Ensure checkpoint enabled
   ENABLE_CHECKPOINTS=true
   CHECKPOINT_INTERVAL=10  # iterations
   docker restart xagent-api
   ```

---

### XAgentHighFailureRate

**Severity**: High  
**Description**: More than 20% of cognitive loop iterations are failing

#### Investigation Steps

1. Check failure reasons:
   ```bash
   # Query metrics for failure types
   curl 'http://prometheus:9090/api/v1/query' \
     --data 'query=rate(cognitive_loop_iterations_total{status="failed"}[10m]) by (reason)'
   ```

2. Review error logs:
   ```bash
   docker logs xagent-api | grep "ERROR.*cognitive_loop" | tail -50
   ```

3. Check tool execution failures:
   ```bash
   # Tool failure metrics
   curl 'http://prometheus:9090/api/v1/query' \
     --data 'query=rate(tool_execution_total{status="error"}[10m]) by (tool_name)'
   ```

4. Verify dependencies:
   ```bash
   # Check all required services
   docker ps | grep -E 'redis|postgres|chromadb|opa'
   ```

#### Resolution Steps

1. **If tool failures**: Fix or disable problematic tools
   ```bash
   # Disable specific tool
   echo "DISABLE_TOOL_X=true" >> .env
   docker restart xagent-api
   ```

2. **If LLM issues**: Check API keys and quotas
   ```bash
   # Test OpenAI connection
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **If policy blocks**: Review OPA policies
   ```bash
   # Check OPA policies
   curl http://opa:8181/v1/policies
   ```

4. **If systemic**: Roll back to previous version
   ```bash
   kubectl rollout undo deployment/xagent-api
   ```

---

## Resource Alerts

### XAgentHighCPU

**Severity**: Warning  
**Description**: CPU usage exceeds 80% for 10+ minutes

#### Investigation Steps

1. Profile CPU usage:
   ```bash
   # Top processes in container
   docker exec xagent-api top -b -n 1
   
   # Python profiling
   python -m cProfile -o profile.stats scripts/profile_agent.py
   ```

2. Check for CPU-intensive operations:
   ```bash
   # Review recent operations
   docker logs xagent-api | grep -E "Planning|Embedding|Computation" | tail -50
   ```

3. Monitor concurrent operations:
   ```bash
   # Check active workers
   curl http://localhost:8000/api/v1/metrics | grep worker_active
   ```

#### Resolution Steps

1. **If planning overhead**: Optimize planner
   ```python
   # Reduce max planning depth
   MAX_PLANNING_DEPTH=3
   USE_LANGGRAPH_PLANNER=true  # More efficient
   ```

2. **If embedding generation**: Batch operations
   ```python
   # In vector_store.py
   # Use batch_upsert instead of individual upserts
   ```

3. **If many concurrent requests**: Implement rate limiting
   ```python
   # Already implemented
   # Adjust limits in config
   RATE_LIMIT_PER_MINUTE=100
   ```

4. **If sustained high usage**: Scale horizontally
   ```bash
   kubectl scale deployment xagent-api --replicas=8
   ```

---

### XAgentHighMemory

**Severity**: Warning  
**Description**: Memory usage exceeds 1.5GB for 10+ minutes

#### Investigation Steps

1. Check memory breakdown:
   ```bash
   # Memory usage by process
   docker exec xagent-api ps aux --sort=-%mem | head -10
   
   # Python memory profiling
   python -m memory_profiler scripts/profile_memory.py
   ```

2. Check for memory leaks:
   ```bash
   # Monitor memory over time
   watch -n 5 'docker stats xagent-api --no-stream'
   ```

3. Review cache usage:
   ```bash
   # Redis memory
   redis-cli info memory | grep used_memory_human
   ```

#### Resolution Steps

1. **If cache bloat**: Clear and optimize cache
   ```bash
   # Clear old cache entries
   redis-cli --scan --pattern "cache:*" | xargs redis-cli DEL
   
   # Set memory limits
   redis-cli CONFIG SET maxmemory 512mb
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```

2. **If large objects in memory**: Implement pagination
   ```python
   # Use streaming for large results
   # Implement cursor-based pagination
   ```

3. **If memory leak**: Restart service
   ```bash
   docker restart xagent-api
   ```

4. **If sustained high usage**: Increase memory limit
   ```bash
   docker update --memory=3g xagent-api
   ```

---

## Database Alerts

### XAgentRedisDown

**Severity**: Critical  
**Description**: Redis is not responding

#### Investigation Steps

1. Check Redis status:
   ```bash
   docker ps | grep redis
   docker logs redis --tail 100
   ```

2. Test connection:
   ```bash
   redis-cli -h redis -p 6379 ping
   ```

3. Check for crashes:
   ```bash
   docker logs redis | grep -i "error\|fatal"
   ```

#### Resolution Steps

1. **If container stopped**: Restart Redis
   ```bash
   docker restart redis
   ```

2. **If connection issues**: Check network
   ```bash
   docker network inspect xagent_network
   ```

3. **If data corruption**: Restore from backup
   ```bash
   # Stop Redis
   docker stop redis
   
   # Restore backup
   docker cp redis-backup.rdb redis:/data/dump.rdb
   
   # Start Redis
   docker start redis
   ```

4. **If persistent issues**: Check Redis logs and config
   ```bash
   docker exec redis cat /etc/redis/redis.conf
   ```

---

### XAgentPostgreSQLDown

**Severity**: Critical  
**Description**: PostgreSQL is not responding

#### Investigation Steps

1. Check PostgreSQL status:
   ```bash
   docker ps | grep postgres
   docker logs postgres --tail 100
   ```

2. Test connection:
   ```bash
   psql -h postgres -U xagent -c "SELECT 1"
   ```

3. Check for corruption:
   ```bash
   docker exec postgres pg_isready
   ```

#### Resolution Steps

1. **If container stopped**: Restart PostgreSQL
   ```bash
   docker restart postgres
   ```

2. **If connection limit reached**: Increase max connections
   ```sql
   ALTER SYSTEM SET max_connections = 200;
   SELECT pg_reload_conf();
   ```

3. **If disk full**: Clean up old data
   ```sql
   -- Remove old logs
   DELETE FROM logs WHERE created_at < NOW() - INTERVAL '30 days';
   
   -- Vacuum database
   VACUUM FULL;
   ```

4. **If corruption**: Restore from backup
   ```bash
   docker exec postgres pg_restore -d xagent /backups/latest.dump
   ```

---

## Tool Alerts

### XAgentToolExecutionFailures

**Severity**: Warning  
**Description**: More than 5 tool execution failures per second

#### Investigation Steps

1. Identify failing tools:
   ```bash
   curl 'http://prometheus:9090/api/v1/query' \
     --data 'query=rate(tool_execution_total{status="error"}[5m]) by (tool_name)'
   ```

2. Check tool logs:
   ```bash
   docker logs xagent-api | grep "tool_execution" | grep "ERROR" | tail -50
   ```

3. Test tool directly:
   ```python
   # Via Python REPL
   from xagent.tools import langserve_tools
   tool = langserve_tools.get_tool_by_name("execute_code")
   result = tool.invoke({"code": "print('test')", "language": "python"})
   ```

#### Resolution Steps

1. **If sandbox issues**: Restart Docker daemon
   ```bash
   sudo systemctl restart docker
   docker restart xagent-api
   ```

2. **If specific tool failing**: Disable temporarily
   ```bash
   echo "DISABLE_TOOL_EXECUTE_CODE=true" >> .env
   docker restart xagent-api
   ```

3. **If external API issues**: Check rate limits and quotas
   ```bash
   # Check OpenAI usage
   curl https://api.openai.com/v1/dashboard/billing/usage \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

4. **If policy blocking**: Review OPA rules
   ```bash
   # Check which tools are blocked
   docker logs opa | grep "tool_execution"
   ```

---

## Worker Alerts

### XAgentWorkerDown

**Severity**: High  
**Description**: Celery worker is not responding

#### Investigation Steps

1. Check worker status:
   ```bash
   docker ps | grep xagent-worker
   docker logs xagent-worker --tail 100
   ```

2. Check Celery status:
   ```bash
   celery -A xagent.tasks.worker inspect active
   celery -A xagent.tasks.worker inspect stats
   ```

3. Check task queue:
   ```bash
   # Redis queue length
   redis-cli LLEN celery
   ```

#### Resolution Steps

1. **If worker crashed**: Restart worker
   ```bash
   docker restart xagent-worker
   ```

2. **If stuck tasks**: Purge and restart
   ```bash
   celery -A xagent.tasks.worker purge
   docker restart xagent-worker
   ```

3. **If scaling needed**: Add more workers
   ```bash
   docker-compose up -d --scale xagent-worker=5
   ```

---

### XAgentHighTaskQueue

**Severity**: Warning  
**Description**: Task queue has more than 1000 tasks pending

#### Investigation Steps

1. Check queue size:
   ```bash
   redis-cli LLEN celery
   ```

2. Check worker capacity:
   ```bash
   celery -A xagent.tasks.worker inspect active
   celery -A xagent.tasks.worker inspect stats
   ```

3. Identify task types:
   ```bash
   # Sample tasks from queue
   redis-cli LRANGE celery 0 10
   ```

#### Resolution Steps

1. **If workers overwhelmed**: Scale up workers
   ```bash
   docker-compose up -d --scale xagent-worker=10
   ```

2. **If task storm**: Implement rate limiting
   ```python
   # Add rate limit to task
   @task(rate_limit='10/m')
   def my_task():
       pass
   ```

3. **If specific task type**: Purge specific tasks
   ```bash
   celery -A xagent.tasks.worker purge --queue=specific_queue
   ```

---

## General Response Procedures

### Escalation Path

1. **Level 1 - Automated**: Auto-restart via health checks
2. **Level 2 - On-Call Engineer**: Apply runbook procedures
3. **Level 3 - Senior Engineer**: Complex issues requiring investigation
4. **Level 4 - Architecture Review**: Systemic issues requiring redesign

### Communication

- **Critical Alerts**: Notify on-call via PagerDuty immediately
- **High Alerts**: Slack #xagent-alerts within 5 minutes
- **Warning Alerts**: Email to team@example.com

### Post-Incident

1. Document what happened
2. What was the root cause
3. What was done to fix it
4. How to prevent in the future
5. Update runbook if needed

---

## Useful Commands Reference

### Docker

```bash
# View logs
docker logs <container> --tail 100 --follow

# Restart container
docker restart <container>

# Execute command in container
docker exec -it <container> bash

# View container stats
docker stats <container>

# Update resources
docker update --memory=2g --cpus=2 <container>
```

### Kubernetes

```bash
# View pods
kubectl get pods -l app=xagent-api

# View logs
kubectl logs -l app=xagent-api --tail=100 -f

# Restart deployment
kubectl rollout restart deployment/xagent-api

# Scale deployment
kubectl scale deployment xagent-api --replicas=5

# Rollback deployment
kubectl rollout undo deployment/xagent-api
```

### Prometheus Queries

```bash
# Query via API
curl 'http://prometheus:9090/api/v1/query' \
  --data 'query=<your_query>'

# Query via PromQL
up{job="xagent-api"}
rate(http_requests_total[5m])
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

---

## Additional Resources

- **Prometheus Alerts**: `config/alerting/prometheus-rules.yml`
- **AlertManager Config**: `config/alerting/alertmanager.yml`
- **Grafana Dashboards**: http://grafana:3000
- **Prometheus**: http://prometheus:9090
- **Jaeger**: http://jaeger:16686

---

**Last Updated**: 2025-11-13  
**Maintained By**: X-Agent Team  
**Version**: 1.0
