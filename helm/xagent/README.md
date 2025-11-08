# X-Agent Helm Chart

This Helm chart deploys X-Agent, an autonomous AI agent platform, on Kubernetes.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (for persistent storage)
- cert-manager (optional, for TLS certificates)

## Installation

### Add Dependencies

First, add the required Helm repositories:

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

### Install the Chart

To install the chart with the release name `xagent`:

```bash
helm install xagent ./helm/xagent \
  --set secrets.openaiApiKey="your-openai-api-key" \
  --set ingress.hosts[0].host="xagent.yourdomain.com" \
  --set redis.auth.password="your-redis-password" \
  --set postgresql.auth.password="your-postgres-password"
```

### Install with Custom Values

Create a `values-production.yaml` file:

```yaml
api:
  replicaCount: 5
  resources:
    limits:
      cpu: 2000m
      memory: 2Gi
    requests:
      cpu: 1000m
      memory: 1Gi

secrets:
  openaiApiKey: "sk-..."
  jwtSecret: "your-secure-jwt-secret"

ingress:
  enabled: true
  hosts:
    - host: xagent.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
          service: api

redis:
  auth:
    password: "secure-redis-password"

postgresql:
  auth:
    password: "secure-postgres-password"
```

Then install:

```bash
helm install xagent ./helm/xagent -f values-production.yaml
```

## Configuration

The following table lists the configurable parameters of the X-Agent chart and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `""` |
| `global.imagePullSecrets` | Global Docker registry secret names | `[]` |

### API Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `api.replicaCount` | Number of API replicas | `3` |
| `api.image.repository` | API image repository | `xagent/api` |
| `api.image.tag` | API image tag | `Chart.AppVersion` |
| `api.service.type` | Kubernetes service type | `ClusterIP` |
| `api.service.port` | Service port | `8000` |
| `api.resources.limits.cpu` | CPU limit | `1000m` |
| `api.resources.limits.memory` | Memory limit | `1Gi` |
| `api.autoscaling.enabled` | Enable HPA | `true` |
| `api.autoscaling.minReplicas` | Minimum replicas | `2` |
| `api.autoscaling.maxReplicas` | Maximum replicas | `10` |

### WebSocket Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `websocket.enabled` | Enable WebSocket gateway | `true` |
| `websocket.replicaCount` | Number of WebSocket replicas | `2` |
| `websocket.resources.limits.memory` | Memory limit | `512Mi` |

### Worker Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `worker.enabled` | Enable worker pods | `true` |
| `worker.replicaCount` | Number of worker replicas | `2` |
| `worker.resources.limits.cpu` | CPU limit | `2000m` |
| `worker.resources.limits.memory` | Memory limit | `2Gi` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.hosts[0].host` | Hostname | `xagent.example.com` |
| `ingress.tls[0].secretName` | TLS secret name | `xagent-tls` |

### Redis Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `redis.enabled` | Enable Redis deployment | `true` |
| `redis.auth.password` | Redis password | `changeme` |
| `redis.master.persistence.size` | Redis PVC size | `8Gi` |

### PostgreSQL Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL deployment | `true` |
| `postgresql.auth.username` | PostgreSQL username | `xagent` |
| `postgresql.auth.password` | PostgreSQL password | `changeme` |
| `postgresql.auth.database` | PostgreSQL database | `xagent` |
| `postgresql.primary.persistence.size` | PostgreSQL PVC size | `10Gi` |

### ChromaDB Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `chromadb.enabled` | Enable ChromaDB deployment | `true` |
| `chromadb.persistence.size` | ChromaDB PVC size | `10Gi` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `config.agent.mode` | Agent mode | `autonomous` |
| `config.agent.maxIterations` | Max iterations | `50` |
| `config.llm.provider` | LLM provider | `openai` |
| `config.llm.model` | LLM model | `gpt-4` |
| `config.log.level` | Log level | `INFO` |

### Secrets

| Parameter | Description | Default |
|-----------|-------------|---------|
| `secrets.openaiApiKey` | OpenAI API key (required) | `""` |
| `secrets.jwtSecret` | JWT secret | Auto-generated |
| `secrets.opaPolicyToken` | OPA policy token | Auto-generated |

### Monitoring

| Parameter | Description | Default |
|-----------|-------------|---------|
| `monitoring.prometheus.enabled` | Enable Prometheus monitoring | `true` |
| `monitoring.prometheus.serviceMonitor.enabled` | Create ServiceMonitor | `true` |
| `monitoring.grafana.enabled` | Enable Grafana | `true` |
| `monitoring.jaeger.enabled` | Enable Jaeger tracing | `true` |

## Upgrading

To upgrade an existing release:

```bash
helm upgrade xagent ./helm/xagent -f values-production.yaml
```

## Uninstallation

To uninstall/delete the `xagent` deployment:

```bash
helm uninstall xagent
```

This command removes all the Kubernetes components associated with the chart and deletes the release.

## Production Checklist

Before deploying to production:

- [ ] Set strong passwords for Redis and PostgreSQL
- [ ] Configure proper OpenAI API key
- [ ] Set up TLS certificates (via cert-manager or manual)
- [ ] Configure ingress hostname
- [ ] Review and adjust resource limits based on load
- [ ] Enable monitoring (Prometheus, Grafana, Jaeger)
- [ ] Set up backup strategy for PostgreSQL
- [ ] Configure network policies if required
- [ ] Review security context settings
- [ ] Set up log aggregation (ELK, Loki, etc.)
- [ ] Configure alerting (AlertManager)
- [ ] Test autoscaling behavior
- [ ] Set up pod disruption budgets

## Architecture

The chart deploys the following components:

- **API Pods**: FastAPI REST API with health checks
- **WebSocket Pods**: Real-time WebSocket gateway
- **Worker Pods**: Celery workers for background tasks
- **Redis**: In-memory cache and message broker
- **PostgreSQL**: Primary database for persistence
- **ChromaDB**: Vector database for embeddings

## Health Checks

The chart includes comprehensive health checks:

- **Liveness**: `/healthz` - Container restart if fails
- **Readiness**: `/ready` - Remove from load balancer if not ready
- **Startup**: `/health` - Wait for application startup

## Autoscaling

Horizontal Pod Autoscaling (HPA) is enabled by default for:

- API pods: Scale based on CPU (70%) and Memory (80%)
- Worker pods: Scale based on CPU (80%)

## Monitoring

The chart integrates with Prometheus for metrics collection:

- API metrics exposed on port 9090
- ServiceMonitor created automatically when enabled
- Grafana dashboards pre-configured
- Jaeger for distributed tracing

## Troubleshooting

### Check pod status

```bash
kubectl get pods -l app.kubernetes.io/name=xagent
```

### View logs

```bash
kubectl logs -l app.kubernetes.io/name=xagent,app.kubernetes.io/component=api
```

### Check health endpoints

```bash
kubectl port-forward svc/xagent-api 8000:8000
curl http://localhost:8000/health
```

### Debug configuration

```bash
kubectl get configmap xagent-config -o yaml
kubectl get secret xagent-secrets -o yaml
```

## Support

For issues and questions:

- GitHub: https://github.com/UnknownEngineOfficial/X-Agent
- Issues: https://github.com/UnknownEngineOfficial/X-Agent/issues

## License

This chart is licensed under the MIT License.
