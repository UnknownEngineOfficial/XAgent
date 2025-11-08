# X-Agent Deployment Guide

**Version**: 0.1.0  
**Last Updated**: 2025-11-08

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (Docker)](#quick-start-docker)
4. [Production Deployment](#production-deployment)
5. [Configuration](#configuration)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security Hardening](#security-hardening)
8. [Scaling](#scaling)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Overview

X-Agent can be deployed in various environments:

- **Development**: Local Docker Compose setup
- **Staging**: Docker Compose with production-like configuration
- **Production**: Kubernetes or Docker Swarm with full observability stack

This guide covers all deployment scenarios with best practices for each.

---

## Prerequisites

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 20 GB
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

### Software Requirements

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.10+ (for local development)
- **Git**: For cloning the repository

### Optional (for production)

- **Kubernetes**: 1.25+ (if deploying to K8s)
- **Terraform**: For infrastructure as code
- **Ansible**: For configuration management

---

## Quick Start (Docker)

### 1. Clone the Repository

```bash
git clone https://github.com/UnknownEngineOfficial/X-Agent.git
cd X-Agent
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration (see Configuration section)
nano .env
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/health
```

### 4. Access Services

- **REST API**: http://localhost:8000
- **WebSocket**: ws://localhost:8001
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686

### 5. Test the API

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "secret"}'

# Create a goal
curl -X POST http://localhost:8000/goals \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Test goal",
    "priority": 5
  }'
```

---

## Production Deployment

### Architecture Overview

```
┌─────────────────┐
│  Load Balancer  │ (nginx, traefik, or cloud LB)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   X-Agent API   │ (FastAPI, multiple instances)
└────────┬────────┘
         │
         ├─────► Redis (caching, pubsub)
         ├─────► PostgreSQL (persistent storage)
         ├─────► ChromaDB (vector embeddings)
         └─────► Celery Workers (background tasks)
                        │
                        ├─────► Prometheus (metrics)
                        ├─────► Jaeger (tracing)
                        └─────► Loki (logs)
```

### Step-by-Step Production Setup

#### 1. Infrastructure Setup

**Option A: Docker Compose (Small Production)**

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

**Option B: Kubernetes (Large Production)**

```bash
# Apply Kubernetes manifests (coming soon)
kubectl apply -f k8s/
```

#### 2. Database Setup

```bash
# Initialize PostgreSQL database
docker-compose exec postgres psql -U xagent -d xagent

# Run migrations (if using Alembic)
docker-compose exec api alembic upgrade head
```

#### 3. Security Configuration

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env with production values
JWT_SECRET_KEY=<generated-secret>
JWT_ALGORITHM=HS256
ENVIRONMENT=production
DEBUG=false
```

#### 4. SSL/TLS Setup

**Using Let's Encrypt with Certbot:**

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

**Using Traefik (recommended for Docker):**

```yaml
# docker-compose.prod.yml
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./letsencrypt:/letsencrypt
```

#### 5. Configure Reverse Proxy

**Nginx Configuration Example:**

```nginx
# /etc/nginx/sites-available/xagent
upstream xagent_api {
    server 127.0.0.1:8000;
    # Add more instances for load balancing
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

upstream xagent_ws {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # API endpoints
    location / {
        proxy_pass http://xagent_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket endpoint
    location /ws {
        proxy_pass http://xagent_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/xagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Configuration

### Environment Variables

Core configuration is managed via environment variables in `.env`:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
JWT_SECRET_KEY=your-secret-key-here-minimum-32-chars
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Database
DATABASE_URL=postgresql://xagent:password@postgres:5432/xagent
REDIS_URL=redis://redis:6379/0

# ChromaDB
CHROMA_HOST=chromadb
CHROMA_PORT=8000

# OpenAI (if using LLM features)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# Tracing
OTLP_ENDPOINT=http://jaeger:4318
TRACING_CONSOLE=false
TRACING_INSECURE=true

# Logging
LOKI_URL=http://loki:3100
```

### Production Configuration Checklist

- [ ] Change default passwords
- [ ] Set secure `JWT_SECRET_KEY` (32+ characters)
- [ ] Disable `DEBUG=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure production database with backups
- [ ] Set up SSL/TLS certificates
- [ ] Configure monitoring and alerting
- [ ] Set up log aggregation
- [ ] Configure backups
- [ ] Set resource limits
- [ ] Enable CORS only for trusted domains
- [ ] Configure rate limiting
- [ ] Set up firewalls

---

## Monitoring & Observability

### Metrics (Prometheus)

**Access**: http://localhost:9090

**Key Metrics to Monitor:**

```promql
# Request rate
rate(x_agent_api_requests_total[5m])

# Request duration (95th percentile)
histogram_quantile(0.95, rate(x_agent_api_request_duration_seconds_bucket[5m]))

# Error rate
rate(x_agent_api_errors_total[5m])

# Active goals
x_agent_goals_total{status="in_progress"}

# Cognitive loop performance
rate(x_agent_cognitive_loop_iterations_total[5m])
```

### Dashboards (Grafana)

**Access**: http://localhost:3000 (default: admin/admin)

**Pre-configured Dashboards:**

1. **Agent Performance**: Cognitive loop, goals, completion time
2. **API Health**: Response time, request rate, errors
3. **System Resources**: CPU, memory, disk usage

**Import Dashboards:**
```bash
# Dashboards are auto-provisioned from config/grafana/dashboards/
```

### Distributed Tracing (Jaeger)

**Access**: http://localhost:16686

**Use Cases:**
- Trace request flow through system
- Identify performance bottlenecks
- Debug complex multi-service issues

### Log Aggregation (Loki)

**Access**: Via Grafana (Explore > Loki)

**Query Examples:**

```logql
# All errors
{job="xagent"} |= "ERROR"

# Specific service logs
{job="xagent", service="api"} |= "request"

# Trace correlation
{job="xagent"} | json | trace_id="abc123"
```

### Alerting

**Setup AlertManager:**

```yaml
# config/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@yourdomain.com'
  smtp_auth_username: 'alerts@yourdomain.com'
  smtp_auth_password: 'your-password'

route:
  receiver: 'email'
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h

receivers:
  - name: 'email'
    email_configs:
      - to: 'ops@yourdomain.com'
```

**Alert Rules:**

```yaml
# config/prometheus/alerts.yml
groups:
  - name: xagent
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(x_agent_api_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"
      
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(x_agent_api_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API response time"
          description: "95th percentile response time is {{ $value }}s"
      
      - alert: ServiceDown
        expr: up{job="xagent"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "X-Agent service is down"
          description: "Service {{ $labels.instance }} is not responding"
```

---

## Security Hardening

### 1. Network Security

```bash
# Configure firewall (UFW on Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 2. Container Security

```yaml
# docker-compose.prod.yml
services:
  api:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
```

### 3. Secrets Management

**Using Docker Secrets:**

```bash
# Create secrets
echo "your-jwt-secret" | docker secret create jwt_secret -
echo "your-db-password" | docker secret create db_password -

# Use in docker-compose
services:
  api:
    secrets:
      - jwt_secret
      - db_password
    environment:
      JWT_SECRET_KEY_FILE: /run/secrets/jwt_secret
```

**Using HashiCorp Vault:**

```python
# src/xagent/config.py
import hvac

def get_secret(path: str, key: str) -> str:
    client = hvac.Client(url='http://vault:8200')
    secret = client.secrets.kv.v2.read_secret_version(path=path)
    return secret['data']['data'][key]

# Usage
JWT_SECRET_KEY = get_secret('xagent', 'jwt_secret')
```

### 4. Database Security

```sql
-- Create limited-privilege user
CREATE USER xagent_app WITH PASSWORD 'secure-password';
GRANT CONNECT ON DATABASE xagent TO xagent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO xagent_app;

-- Enable SSL
ALTER SYSTEM SET ssl = on;
```

### 5. API Security Checklist

- [ ] Enable JWT authentication on all endpoints
- [ ] Implement rate limiting (100 req/min default)
- [ ] Use HTTPS only (disable HTTP)
- [ ] Set secure CORS policies
- [ ] Implement request validation
- [ ] Enable API key rotation
- [ ] Set up IP whitelisting for admin endpoints
- [ ] Enable audit logging
- [ ] Implement request signing
- [ ] Use OPA for policy enforcement

---

## Scaling

### Horizontal Scaling

**Docker Compose (Swarm Mode):**

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml xagent

# Scale API instances
docker service scale xagent_api=3
```

**Kubernetes:**

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: xagent-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: xagent-api
  template:
    metadata:
      labels:
        app: xagent-api
    spec:
      containers:
      - name: api
        image: xagent:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: xagent-api
spec:
  type: LoadBalancer
  selector:
    app: xagent-api
  ports:
  - port: 80
    targetPort: 8000
```

### Vertical Scaling

**Resource Limits:**

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### Database Scaling

**Read Replicas:**

```yaml
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_USER: xagent
      POSTGRES_PASSWORD: password
      POSTGRES_DB: xagent
    volumes:
      - postgres-data:/var/lib/postgresql/data
  
  postgres-replica:
    image: postgres:15
    environment:
      POSTGRES_USER: xagent
      POSTGRES_PASSWORD: password
      POSTGRES_PRIMARY_HOST: postgres-primary
```

---

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check logs
docker-compose logs api

# Check health
curl http://localhost:8000/health

# Check dependencies
docker-compose ps
```

**Solution:**
- Verify all required services are running
- Check environment variables
- Ensure ports are not already in use

#### 2. Database Connection Failed

```bash
# Test connection
docker-compose exec api python -c "
from xagent.config import settings
from sqlalchemy import create_engine
engine = create_engine(settings.database_url)
engine.connect()
"
```

**Solution:**
- Verify `DATABASE_URL` is correct
- Ensure PostgreSQL is running
- Check network connectivity

#### 3. High Memory Usage

```bash
# Check memory
docker stats

# Identify memory hogs
docker-compose top
```

**Solution:**
- Reduce worker count
- Optimize cache size
- Enable memory cleanup routines

#### 4. Slow API Response

```bash
# Check metrics
curl http://localhost:8000/metrics | grep duration

# View traces
# Open Jaeger UI: http://localhost:16686
```

**Solution:**
- Scale horizontally (add more instances)
- Enable caching
- Optimize database queries
- Check network latency

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart service
docker-compose restart api

# View detailed logs
docker-compose logs -f api
```

---

## Maintenance

### Backup Strategy

#### 1. Database Backup

```bash
# Manual backup
docker-compose exec postgres pg_dump -U xagent xagent > backup.sql

# Restore
docker-compose exec -T postgres psql -U xagent xagent < backup.sql

# Automated backup (cron)
0 2 * * * docker-compose exec postgres pg_dump -U xagent xagent > /backups/xagent-$(date +\%Y\%m\%d).sql
```

#### 2. Configuration Backup

```bash
# Backup env and compose files
tar -czf config-backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml config/
```

### Updates

```bash
# Pull latest images
docker-compose pull

# Recreate containers
docker-compose up -d --force-recreate

# Run migrations
docker-compose exec api alembic upgrade head
```

### Log Rotation

```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Monitoring Checklist

Daily:
- [ ] Check service health status
- [ ] Review error logs
- [ ] Monitor disk space

Weekly:
- [ ] Review performance metrics
- [ ] Check backup integrity
- [ ] Update dependencies

Monthly:
- [ ] Security audit
- [ ] Review and rotate logs
- [ ] Capacity planning

---

## Additional Resources

- [API Documentation](API.md)
- [Observability Guide](OBSERVABILITY.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Developer Guide](DEVELOPER_GUIDE.md)
- [GitHub Issues](https://github.com/UnknownEngineOfficial/X-Agent/issues)

---

## Support

For deployment issues:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with deployment logs
4. Join community discussions

---

**Last Updated**: 2025-11-08  
**Contributors**: X-Agent Team
