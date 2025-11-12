# X-Agent Helm Deployment Guide

Complete guide for deploying X-Agent to Kubernetes using Helm charts.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Multi-Environment Deployment](#multi-environment-deployment)
4. [Configuration](#configuration)
5. [Secrets Management](#secrets-management)
6. [Monitoring & Observability](#monitoring--observability)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Prerequisites

### Required Components

- **Kubernetes Cluster**: v1.24+ (GKE, EKS, AKS, or self-hosted)
- **Helm**: v3.8+
- **kubectl**: Configured to access your cluster
- **Ingress Controller**: nginx-ingress, Traefik, or similar
- **cert-manager**: For automatic TLS certificate management
- **Storage Class**: With ReadWriteOnce (RWO) support

### Optional Components

- **Prometheus Operator**: For monitoring integration
- **External Secrets Operator**: For secrets management
- **ArgoCD**: For GitOps deployment

### Installation of Prerequisites

```bash
# Install nginx-ingress controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Verify installation
kubectl get pods -n cert-manager
```

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/UnknownEngineOfficial/XAgent.git
cd XAgent/helm/xagent
```

### 2. Update Dependencies

```bash
helm dependency update
```

### 3. Create Namespace

```bash
kubectl create namespace xagent
```

### 4. Install Chart

```bash
# Basic installation
helm install xagent . -n xagent

# With custom values
helm install xagent . -n xagent \
  --set secrets.openaiApiKey="sk-your-key" \
  --set ingress.hosts[0].host="xagent.yourdomain.com"
```

### 5. Verify Installation

```bash
# Check pod status
kubectl get pods -n xagent

# Check services
kubectl get svc -n xagent

# Check ingress
kubectl get ingress -n xagent
```

## Multi-Environment Deployment

### Development Environment

Minimal resources, no persistence, fast iteration:

```bash
helm install xagent-dev . -n xagent-dev --create-namespace \
  --set api.replicaCount=1 \
  --set worker.replicaCount=1 \
  --set redis.master.persistence.enabled=false \
  --set postgresql.primary.persistence.enabled=false \
  --set chromadb.persistence.enabled=false \
  --set ingress.hosts[0].host="dev.xagent.local"
```

### Staging Environment

Use the staging values file:

```bash
helm install xagent-staging . -n xagent-staging --create-namespace \
  -f values-staging.yaml \
  --set secrets.openaiApiKey="${OPENAI_API_KEY}" \
  --set secrets.jwtSecret="${JWT_SECRET}" \
  --set ingress.hosts[0].host="staging.xagent.yourdomain.com"
```

### Production Environment

Use the production values file with external secrets:

```bash
helm install xagent . -n xagent --create-namespace \
  -f values-production.yaml \
  --set api.image.tag="0.1.0" \
  --set ingress.hosts[0].host="api.xagent.yourdomain.com" \
  --set ingress.hosts[1].host="ws.xagent.yourdomain.com"
```

## Configuration

### Customizing Resource Limits

Create a `custom-resources.yaml`:

```yaml
api:
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
    requests:
      cpu: 1000m
      memory: 2Gi

worker:
  resources:
    limits:
      cpu: 4000m
      memory: 8Gi
    requests:
      cpu: 2000m
      memory: 4Gi
```

Apply:

```bash
helm upgrade xagent . -n xagent -f custom-resources.yaml
```

### Autoscaling Configuration

Adjust autoscaling parameters:

```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60
    targetMemoryUtilizationPercentage: 70

worker:
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 15
    targetCPUUtilizationPercentage: 75
```

### High Availability Setup

Enable Redis and PostgreSQL replication:

```yaml
redis:
  architecture: replication
  replica:
    replicaCount: 2
  sentinel:
    enabled: true
    quorum: 2

postgresql:
  architecture: replication
  readReplicas:
    replicaCount: 2
```

### Storage Configuration

Configure storage classes for different components:

```yaml
redis:
  master:
    persistence:
      storageClass: "fast-ssd"
      size: 20Gi

postgresql:
  primary:
    persistence:
      storageClass: "fast-ssd"
      size: 50Gi

chromadb:
  persistence:
    storageClass: "standard"
    size: 100Gi
```

## Secrets Management

### Method 1: Helm Values (Development Only)

⚠️ **Not recommended for production**

```bash
helm install xagent . \
  --set secrets.openaiApiKey="sk-..." \
  --set secrets.jwtSecret="..."
```

### Method 2: Kubernetes Secrets

Create secrets manually:

```bash
kubectl create secret generic xagent-secrets -n xagent \
  --from-literal=openaiApiKey="sk-..." \
  --from-literal=jwtSecret="..." \
  --from-literal=opaPolicyToken="..."
```

Reference in values:

```yaml
# Disable chart-managed secrets
secrets:
  create: false
  existingSecret: "xagent-secrets"
```

### Method 3: External Secrets Operator (Recommended)

Install External Secrets Operator:

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace
```

Create SecretStore (AWS Secrets Manager example):

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: xagent
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
```

Create ExternalSecret:

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: xagent-secrets
  namespace: xagent
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: xagent-secret
    creationPolicy: Owner
  data:
    - secretKey: openaiApiKey
      remoteRef:
        key: xagent/openai-api-key
    - secretKey: jwtSecret
      remoteRef:
        key: xagent/jwt-secret
    - secretKey: opaPolicyToken
      remoteRef:
        key: xagent/opa-policy-token
```

### Method 4: Sealed Secrets

Install Sealed Secrets controller:

```bash
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
```

Seal your secrets:

```bash
# Create secret file
cat > secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: xagent-secrets
  namespace: xagent
stringData:
  openaiApiKey: "sk-..."
  jwtSecret: "..."
EOF

# Seal it
kubeseal --format=yaml < secret.yaml > sealed-secret.yaml

# Apply sealed secret
kubectl apply -f sealed-secret.yaml
```

## Monitoring & Observability

### Prometheus Integration

Enable Prometheus monitoring:

```yaml
monitoring:
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true
      interval: 30s
      scrapeTimeout: 10s
```

Verify ServiceMonitor:

```bash
kubectl get servicemonitor -n xagent
```

### Grafana Dashboards

Access Grafana:

```bash
kubectl port-forward -n xagent svc/xagent-grafana 3000:80
```

Default credentials:
- Username: `admin`
- Password: (from `values.yaml` or generated)

Import dashboards:
1. Navigate to http://localhost:3000
2. Go to Dashboards → Import
3. Upload JSON dashboards from `config/grafana/dashboards/`

### Jaeger Tracing

Access Jaeger UI:

```bash
kubectl port-forward -n xagent svc/xagent-jaeger-query 16686:16686
```

Open http://localhost:16686 in browser.

### Custom Alerts

Create PrometheusRule:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: xagent-alerts
  namespace: xagent
spec:
  groups:
    - name: xagent
      interval: 30s
      rules:
        - alert: XAgentHighErrorRate
          expr: rate(xagent_errors_total[5m]) > 0.05
          for: 5m
          labels:
            severity: warning
          annotations:
            summary: "High error rate detected"
        - alert: XAgentAPIDown
          expr: up{job="xagent-api"} == 0
          for: 1m
          labels:
            severity: critical
          annotations:
            summary: "X-Agent API is down"
```

## Troubleshooting

### Common Issues

#### 1. Pods Stuck in Pending

```bash
# Check events
kubectl describe pod <pod-name> -n xagent

# Check if PVC is bound
kubectl get pvc -n xagent
```

**Solutions:**
- Ensure storage class exists and is provisioning
- Check node resources (CPU/memory)
- Verify pod anti-affinity rules aren't too restrictive

#### 2. Image Pull Errors

```bash
kubectl get pods -n xagent
# Shows ImagePullBackOff or ErrImagePull
```

**Solutions:**
- Verify image repository and tag
- Check imagePullSecrets configuration
- Ensure Docker registry is accessible

#### 3. CrashLoopBackOff

```bash
# Check logs
kubectl logs <pod-name> -n xagent --previous

# Check events
kubectl describe pod <pod-name> -n xagent
```

**Solutions:**
- Check application logs for errors
- Verify environment variables and secrets
- Ensure database connections are working

#### 4. Database Connection Issues

```bash
# Test Redis connection
kubectl run -it --rm redis-test --image=redis:alpine --restart=Never -n xagent -- \
  redis-cli -h xagent-redis-master ping

# Test PostgreSQL connection
kubectl run -it --rm postgres-test --image=postgres:15 --restart=Never -n xagent -- \
  psql -h xagent-postgresql -U xagent -d xagent -c "SELECT 1"
```

**Solutions:**
- Verify database pods are running
- Check passwords in secrets
- Verify network policies aren't blocking connections

### Debug Commands

```bash
# Check all resources
kubectl get all -n xagent

# Check ConfigMaps and Secrets
kubectl get configmap,secret -n xagent

# View recent events
kubectl get events -n xagent --sort-by='.lastTimestamp' | tail -20

# Check pod resource usage
kubectl top pods -n xagent

# Get pod shell access
kubectl exec -it <pod-name> -n xagent -- /bin/bash

# Port-forward to service
kubectl port-forward -n xagent svc/xagent-api 8000:8000
```

## Best Practices

### Security

1. **Enable Network Policies**: Restrict pod-to-pod communication
2. **Use RBAC**: Limit service account permissions
3. **Enable Pod Security Standards**: Use restricted pod security context
4. **Rotate Secrets**: Implement secret rotation strategy
5. **Use External Secrets**: Never commit secrets to Git

### Performance

1. **Set Resource Limits**: Prevent resource exhaustion
2. **Enable Autoscaling**: Handle variable load
3. **Use Fast Storage**: SSD for databases
4. **Configure Caching**: Optimize Redis configuration
5. **Monitor Metrics**: Track performance indicators

### Reliability

1. **Enable Pod Disruption Budgets**: Maintain availability during updates
2. **Configure Health Checks**: Proper liveness and readiness probes
3. **Use Anti-Affinity**: Spread pods across nodes/zones
4. **Backup Databases**: Regular automated backups
5. **Test Disaster Recovery**: Practice restore procedures

### Operations

1. **Use GitOps**: Track all changes in Git
2. **Implement CI/CD**: Automate deployments
3. **Monitor Everything**: Logs, metrics, traces
4. **Document Changes**: Maintain deployment documentation
5. **Regular Updates**: Keep charts and dependencies updated

## Maintenance

### Backup Procedures

```bash
# Backup PostgreSQL
kubectl exec -n xagent xagent-postgresql-0 -- \
  pg_dump -U xagent xagent | gzip > xagent-$(date +%Y%m%d).sql.gz

# Backup Redis
kubectl exec -n xagent xagent-redis-master-0 -- redis-cli SAVE
kubectl cp xagent/xagent-redis-master-0:/data/dump.rdb ./redis-$(date +%Y%m%d).rdb
```

### Upgrade Procedures

```bash
# Check current release
helm list -n xagent

# Check what will change
helm diff upgrade xagent . -n xagent -f values-production.yaml

# Upgrade with backup
helm upgrade xagent . -n xagent -f values-production.yaml --atomic --cleanup-on-fail

# Verify upgrade
helm status xagent -n xagent
kubectl rollout status deployment/xagent-api -n xagent
```

### Rollback Procedures

```bash
# List revisions
helm history xagent -n xagent

# Rollback to previous
helm rollback xagent -n xagent

# Rollback to specific revision
helm rollback xagent 3 -n xagent
```

## Additional Resources

- [Main Repository](https://github.com/UnknownEngineOfficial/XAgent)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Helm Documentation](https://helm.sh/docs/)
- [Internal Rate Limiting](INTERNAL_RATE_LIMITING.md)
- [Testing Guide](TESTING.md)

## Support

For issues and questions:
- GitHub Issues: https://github.com/UnknownEngineOfficial/XAgent/issues
- Documentation: https://github.com/UnknownEngineOfficial/XAgent/tree/main/docs
