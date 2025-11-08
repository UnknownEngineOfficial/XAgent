# X-Agent Kubernetes Deployment

This directory contains Kubernetes manifests for deploying X-Agent in a production environment.

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Storage provisioner (for StatefulSets)
- Ingress controller (nginx recommended)
- cert-manager (optional, for TLS)

## Quick Start

### 1. Create Namespace
```bash
kubectl apply -f namespace.yaml
```

### 2. Configure Secrets
**Important:** Edit `secrets.yaml` and replace all placeholder values with actual credentials:
- OpenAI API key
- Anthropic API key
- Database passwords
- Secret key for JWT

```bash
kubectl apply -f secrets.yaml
```

### 3. Apply Configuration
```bash
kubectl apply -f configmap.yaml
```

### 4. Deploy Infrastructure Services
```bash
kubectl apply -f deployment-redis.yaml
kubectl apply -f deployment-postgres.yaml
```

Wait for infrastructure to be ready:
```bash
kubectl wait --for=condition=ready pod -l component=redis -n xagent --timeout=120s
kubectl wait --for=condition=ready pod -l component=postgres -n xagent --timeout=120s
```

### 5. Run Database Migrations
```bash
# Create a job to run migrations
kubectl run alembic-migrate --image=xagent:latest --restart=Never -n xagent \
  --env="PYTHONPATH=/app/src" \
  --command -- alembic upgrade head
```

### 6. Deploy Application Services
```bash
kubectl apply -f deployment-api.yaml
kubectl apply -f deployment-websocket.yaml
```

### 7. Configure Ingress (Optional)
Edit `ingress.yaml` and replace `xagent.example.com` with your domain, then:
```bash
kubectl apply -f ingress.yaml
```

## Verification

### Check Pod Status
```bash
kubectl get pods -n xagent
```

### Check Services
```bash
kubectl get services -n xagent
```

### View Logs
```bash
# API logs
kubectl logs -l component=api -n xagent --tail=50 -f

# WebSocket logs
kubectl logs -l component=websocket -n xagent --tail=50 -f
```

### Test Health Endpoints
```bash
# Port forward to API
kubectl port-forward -n xagent svc/xagent-api-service 8000:8000

# In another terminal, test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/healthz
curl http://localhost:8000/ready
```

## Architecture

### Components

- **xagent-api**: REST API service (3 replicas)
  - Handles HTTP requests
  - Exposes metrics on port 9090
  - Health checks: `/health`, `/healthz`, `/ready`

- **xagent-websocket**: WebSocket service (2 replicas)
  - Handles real-time communication
  - Stateless design

- **redis**: In-memory cache and message broker (StatefulSet)
  - 1 replica with persistent storage
  - 256MB memory limit

- **postgres**: Persistent database (StatefulSet)
  - 1 replica with 5GB persistent storage
  - Stores goals, agent state, memories, actions

### Resource Allocation

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit |
|---------|-------------|-----------|----------------|--------------|
| API     | 250m        | 1000m     | 512Mi          | 1Gi          |
| WebSocket | 100m      | 500m      | 256Mi          | 512Mi        |
| Redis   | 100m        | 250m      | 128Mi          | 256Mi        |
| Postgres | 100m       | 500m      | 256Mi          | 512Mi        |

### Storage

- **Redis**: 1Gi persistent volume
- **Postgres**: 5Gi persistent volume

## Scaling

### Horizontal Pod Autoscaler (HPA)

To enable auto-scaling based on CPU usage:

```bash
# API service
kubectl autoscale deployment xagent-api -n xagent \
  --min=3 --max=10 --cpu-percent=70

# WebSocket service  
kubectl autoscale deployment xagent-websocket -n xagent \
  --min=2 --max=5 --cpu-percent=80
```

### Manual Scaling

```bash
# Scale API
kubectl scale deployment xagent-api -n xagent --replicas=5

# Scale WebSocket
kubectl scale deployment xagent-websocket -n xagent --replicas=3
```

## Monitoring

### Prometheus Integration

The API service is annotated for Prometheus scraping:
- Endpoint: `/metrics`
- Port: `9090`

Configure Prometheus to discover pods with:
```yaml
kubernetes_sd_configs:
  - role: pod
    namespaces:
      names:
        - xagent
```

### Grafana Dashboards

Import the dashboards from `../config/grafana/dashboards/`:
- Agent Performance Dashboard
- API Health Dashboard
- System Logs Dashboard

## Security

### Network Policies

Consider implementing network policies to restrict traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: xagent-network-policy
  namespace: xagent
spec:
  podSelector:
    matchLabels:
      app: xagent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  - to:
    - podSelector: {}
```

### Pod Security Standards

All deployments should use:
- Non-root user
- Read-only root filesystem where possible
- Drop all capabilities
- No privilege escalation

### Secret Management

For production, consider using:
- **External Secrets Operator** for cloud secret managers
- **HashiCorp Vault** for dynamic secrets
- **Sealed Secrets** for GitOps workflows

## Backup & Recovery

### Database Backup

Set up automated PostgreSQL backups:

```bash
kubectl create job --from=cronjob/postgres-backup postgres-backup-manual -n xagent
```

### Disaster Recovery

1. Back up all persistent volumes
2. Export secrets securely
3. Store manifests in version control
4. Document recovery procedures

## Troubleshooting

### Pod Not Starting

```bash
kubectl describe pod <pod-name> -n xagent
kubectl logs <pod-name> -n xagent --previous
```

### Database Connection Issues

```bash
# Check if postgres is accessible
kubectl run -it --rm debug --image=postgres:15-alpine --restart=Never -n xagent \
  -- psql -h postgres-service -U xagent -d xagent
```

### Redis Connection Issues

```bash
# Check if redis is accessible
kubectl run -it --rm debug --image=redis:7-alpine --restart=Never -n xagent \
  -- redis-cli -h redis-service -a <password> ping
```

### Migration Issues

```bash
# Check current migration version
kubectl run alembic-current --image=xagent:latest --restart=Never -n xagent \
  --env="PYTHONPATH=/app/src" \
  --command -- alembic current

# View migration history
kubectl run alembic-history --image=xagent:latest --restart=Never -n xagent \
  --env="PYTHONPATH=/app/src" \
  --command -- alembic history
```

## Cleanup

To remove all resources:

```bash
kubectl delete namespace xagent
```

## Production Checklist

- [ ] Update all secrets with strong, unique values
- [ ] Configure TLS/SSL certificates
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation (ELK, Loki, etc.)
- [ ] Implement backup strategy
- [ ] Set resource limits and requests appropriately
- [ ] Configure network policies
- [ ] Enable pod security standards
- [ ] Set up horizontal pod autoscaling
- [ ] Test disaster recovery procedures
- [ ] Document runbooks for common issues
- [ ] Configure ingress for your domain
- [ ] Set up rate limiting at ingress level
- [ ] Enable API authentication in production
