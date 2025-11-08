# X-Agent Alerting Guide

This guide covers the alerting setup for X-Agent using Prometheus AlertManager.

## Overview

X-Agent uses Prometheus AlertManager for intelligent alert routing and notification management. Alerts are automatically triggered based on predefined rules and routed to appropriate teams via multiple channels.

## Architecture

```
┌─────────────┐
│ Prometheus  │  Scrapes metrics from X-Agent components
└──────┬──────┘
       │
       │ Evaluates alert rules
       ▼
┌─────────────┐
│ AlertManager│  Routes and deduplicates alerts
└──────┬──────┘
       │
       ├─────────► Email
       ├─────────► Slack
       ├─────────► PagerDuty
       └─────────► Custom Webhooks
```

## Alert Severity Levels

| Severity | Description | Response Time | Notification Channels |
|----------|-------------|---------------|----------------------|
| **Critical** | Service down or major functionality broken | Immediate | PagerDuty + Slack + Email |
| **High** | Significant degradation or elevated error rates | 15 minutes | Slack + Email |
| **Warning** | Performance issues or potential problems | 1 hour | Slack + Email |
| **Info** | Informational alerts | No action required | Email only |

## Alert Categories

### 1. API Alerts

#### XAgentAPIDown
- **Severity**: Critical
- **Trigger**: API instance down for >1 minute
- **Action**: Check pod status, review logs, verify load balancer

#### XAgentHighErrorRate
- **Severity**: High
- **Trigger**: >5% of requests returning 5xx errors for >5 minutes
- **Action**: Review application logs, check dependencies, analyze error patterns

#### XAgentHighLatency
- **Severity**: Warning
- **Trigger**: 95th percentile latency >2 seconds for >5 minutes
- **Action**: Check database performance, review slow queries, analyze resource usage

#### XAgentHighRequestRate
- **Severity**: Warning
- **Trigger**: >1000 requests/second for >5 minutes
- **Action**: Consider scaling up, check for DDoS, review traffic patterns

#### XAgentAuthenticationFailures
- **Severity**: High
- **Trigger**: >10 authentication failures/second for >5 minutes
- **Action**: Check for brute force attacks, review authentication logs

### 2. Agent Alerts

#### XAgentCognitiveLoopStuck
- **Severity**: Critical
- **Trigger**: No cognitive loop iteration for >5 minutes
- **Action**: Check agent logs, review goal queue, restart if necessary

#### XAgentHighFailureRate
- **Severity**: High
- **Trigger**: >20% of cognitive loop iterations failing for >5 minutes
- **Action**: Review agent logs, check LLM API availability, analyze error patterns

#### XAgentLowGoalCompletionRate
- **Severity**: Warning
- **Trigger**: <50% goal completion rate for >30 minutes
- **Action**: Review goal complexity, check tool availability, analyze blocking issues

### 3. Database Alerts

#### XAgentRedisDown / XAgentPostgreSQLDown / XAgentChromaDBDown
- **Severity**: Critical
- **Trigger**: Database instance down for >1-2 minutes
- **Action**: Check pod status, verify storage, review database logs

#### XAgentHighDBConnections
- **Severity**: Warning
- **Trigger**: >80 concurrent database connections for >5 minutes
- **Action**: Review connection pooling, check for connection leaks

#### XAgentRedisHighMemory
- **Severity**: Warning
- **Trigger**: Redis using >90% of max memory for >5 minutes
- **Action**: Clear unnecessary keys, increase memory limit, check eviction policy

### 4. Resource Alerts

#### XAgentHighCPU / XAgentHighMemory
- **Severity**: Warning
- **Trigger**: CPU >80% or Memory >1.5GB for >10 minutes
- **Action**: Consider scaling horizontally, optimize code, review resource limits

#### XAgentLowDiskSpace
- **Severity**: High
- **Trigger**: <10% disk space available for >5 minutes
- **Action**: Clean up logs, increase disk size, review data retention

### 5. Tool Alerts

#### XAgentToolExecutionFailures
- **Severity**: Warning
- **Trigger**: >5 tool execution failures/second for >5 minutes
- **Action**: Check tool availability, review error logs, verify sandbox

#### XAgentSandboxUnavailable
- **Severity**: High
- **Trigger**: Docker sandbox unavailable for >2 minutes
- **Action**: Check Docker daemon, review container logs, verify permissions

### 6. Worker Alerts

#### XAgentWorkerDown
- **Severity**: High
- **Trigger**: Worker instance down for >2 minutes
- **Action**: Check pod status, review logs, verify Celery broker

#### XAgentHighTaskQueue
- **Severity**: Warning
- **Trigger**: >1000 tasks in queue for >10 minutes
- **Action**: Scale workers, optimize task processing, review task priorities

#### XAgentSlowTaskProcessing
- **Severity**: Warning
- **Trigger**: 95th percentile task duration >5 minutes for >10 minutes
- **Action**: Optimize task code, check resource availability, review dependencies

## Configuration

### AlertManager Configuration

The AlertManager configuration is located at `config/alerting/alertmanager.yml`.

#### Global Settings

```yaml
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@xagent.example.com'
  smtp_auth_username: 'alertmanager@xagent.example.com'
  smtp_auth_password: 'changeme'
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
```

**Update these values** with your actual SMTP and Slack credentials.

#### Route Configuration

Routes define how alerts are grouped and sent to receivers:

```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s          # Wait before sending first notification
  group_interval: 10s      # Wait before sending batched notifications
  repeat_interval: 12h     # Wait before re-sending same alert
  receiver: 'default'
```

#### Receivers

Configure notification channels:

- **Email**: SMTP-based email notifications
- **Slack**: Slack channel notifications
- **PagerDuty**: On-call paging for critical alerts
- **Webhook**: Custom HTTP webhook notifications

### Prometheus Rules

Alert rules are defined in `config/alerting/prometheus-rules.yml`.

To add a new alert rule:

```yaml
- alert: MyCustomAlert
  expr: my_metric > threshold
  for: 5m
  labels:
    severity: warning
    service: my-service
  annotations:
    summary: "Brief description"
    description: "Detailed description with {{ $value }}"
```

## Setup

### Docker Compose

Add AlertManager to your `docker-compose.yml`:

```yaml
services:
  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: xagent-alertmanager
    volumes:
      - ./config/alerting/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager-data:/alertmanager
    ports:
      - "9093:9093"
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    restart: unless-stopped
    networks:
      - xagent-network

  prometheus:
    # ... existing prometheus config ...
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--alertmanager.url=http://alertmanager:9093'  # Add this line
    volumes:
      - ./config/alerting/prometheus-rules.yml:/etc/prometheus/rules.yml  # Add alert rules
```

Update `prometheus.yml` to include alert rules:

```yaml
rule_files:
  - 'rules.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Kubernetes

For Kubernetes deployment, AlertManager is included in the Helm chart.

Enable AlertManager in `values.yaml`:

```yaml
monitoring:
  alertmanager:
    enabled: true
    config:
      global:
        slack_api_url: 'YOUR_SLACK_WEBHOOK'
      route:
        receiver: 'default'
```

## Testing Alerts

### Trigger Test Alert

```bash
# Send test alert to AlertManager
curl -XPOST http://localhost:9093/api/v1/alerts -d '[{
  "labels": {
    "alertname": "TestAlert",
    "severity": "warning",
    "service": "test"
  },
  "annotations": {
    "summary": "Test alert",
    "description": "This is a test alert"
  }
}]'
```

### Check Alert Status

```bash
# View active alerts
curl http://localhost:9093/api/v1/alerts

# View AlertManager status
curl http://localhost:9093/api/v1/status
```

### Silence Alerts

```bash
# Create silence
curl -XPOST http://localhost:9093/api/v1/silences -d '{
  "matchers": [
    {"name": "alertname", "value": "XAgentHighLatency", "isRegex": false}
  ],
  "startsAt": "2024-01-01T00:00:00Z",
  "endsAt": "2024-01-01T01:00:00Z",
  "comment": "Maintenance window"
}'
```

## Notification Channels

### Slack Setup

1. Create a Slack webhook: https://api.slack.com/messaging/webhooks
2. Update `alertmanager.yml` with webhook URL
3. Configure channels for different severity levels:
   - `#xagent-critical` - Critical alerts
   - `#xagent-alerts` - High priority alerts
   - `#xagent-api`, `#xagent-workers`, etc. - Service-specific alerts

### PagerDuty Setup

1. Create a service in PagerDuty
2. Get the Integration Key (service key)
3. Update `alertmanager.yml`:

```yaml
pagerduty_configs:
  - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
```

### Email Setup

Configure SMTP settings in `alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@yourdomain.com'
  smtp_auth_username: 'alerts@yourdomain.com'
  smtp_auth_password: 'your-app-password'
```

For Gmail, use an App Password: https://support.google.com/accounts/answer/185833

## Alert Runbooks

### Critical: XAgentAPIDown

**Impact**: Users cannot access the API

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/component=api

# Check logs
kubectl logs -l app.kubernetes.io/component=api --tail=100

# Check events
kubectl get events --sort-by='.lastTimestamp'
```

**Resolution**:
1. If pods are not running, check resource constraints
2. If pods are CrashLooping, review logs for errors
3. If load balancer issue, check service and ingress
4. Verify health checks are passing: `curl http://api:8000/health`

### High: XAgentHighErrorRate

**Impact**: Elevated error rate affecting user experience

**Diagnosis**:
```bash
# Check error logs
kubectl logs -l app.kubernetes.io/component=api | grep ERROR

# Check metrics
curl http://localhost:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])
```

**Resolution**:
1. Identify common error patterns in logs
2. Check database connectivity
3. Verify external API availability (OpenAI, etc.)
4. Review recent deployments for regressions

### Warning: XAgentHighLatency

**Impact**: Slow response times

**Diagnosis**:
```bash
# Check database performance
SELECT * FROM pg_stat_activity WHERE state = 'active';

# Check resource usage
kubectl top pods -l app.kubernetes.io/component=api
```

**Resolution**:
1. Analyze slow database queries
2. Check for resource contention
3. Consider scaling horizontally
4. Review caching effectiveness

## Best Practices

### 1. Alert Fatigue Prevention

- Set appropriate thresholds to avoid false positives
- Use `for` duration to avoid alerting on transient issues
- Group related alerts together
- Use inhibition rules to suppress redundant alerts

### 2. Actionable Alerts

Every alert should:
- Have a clear description
- Include relevant metrics and values
- Link to runbook documentation
- Specify severity and impact

### 3. Alert Testing

- Test alerts in staging before production
- Regularly review and update alert thresholds
- Conduct alert drills to verify notification channels
- Document resolution procedures

### 4. On-Call Rotation

- Define on-call schedule in PagerDuty
- Document escalation procedures
- Provide access to necessary tools and systems
- Conduct handoff meetings

## Troubleshooting

### Alerts Not Firing

1. Check Prometheus is scraping metrics:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. Verify alert rules are loaded:
   ```bash
   curl http://localhost:9090/api/v1/rules
   ```

3. Check AlertManager connectivity:
   ```bash
   curl http://localhost:9093/api/v1/status
   ```

### Notifications Not Received

1. Check AlertManager logs:
   ```bash
   docker logs xagent-alertmanager
   ```

2. Verify receiver configuration
3. Test notification channels manually
4. Check for silences: `curl http://localhost:9093/api/v1/silences`

### Too Many Alerts

1. Review and adjust alert thresholds
2. Add inhibition rules for related alerts
3. Increase `group_interval` to batch more alerts
4. Consider alert aggregation strategies

## Monitoring AlertManager

AlertManager exposes metrics on `/metrics`:

```bash
# Check alert processing metrics
curl http://localhost:9093/metrics | grep alertmanager_alerts
```

Key metrics:
- `alertmanager_alerts` - Number of active alerts
- `alertmanager_notifications_total` - Total notifications sent
- `alertmanager_notifications_failed_total` - Failed notifications

## References

- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [AlertManager Configuration](https://prometheus.io/docs/alerting/latest/configuration/)
- [Best Practices for Alerting](https://prometheus.io/docs/practices/alerting/)

## Support

For issues with alerting:
- GitHub Issues: https://github.com/UnknownEngineOfficial/X-Agent/issues
- Documentation: https://github.com/UnknownEngineOfficial/X-Agent/docs
