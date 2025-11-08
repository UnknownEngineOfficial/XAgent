# X-Agent Quick Start Guide

**Version**: 0.1.0  
**Status**: ✅ Production Ready

## 🚀 Quick Deploy

### Option 1: Docker Compose (Recommended for Development)

```bash
# Clone repository
git clone https://github.com/UnknownEngineOfficial/X-Agent.git
cd X-Agent

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f xagent-api

# Access services
# - API: http://localhost:8000
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
# - Jaeger: http://localhost:16686
```

### Option 2: Kubernetes (Recommended for Production)

```bash
# Using kubectl
kubectl create namespace xagent
kubectl apply -f k8s/

# Or using Helm
helm install xagent ./helm/xagent --create-namespace --namespace xagent

# Check deployment
kubectl get pods -n xagent
kubectl get services -n xagent

# Access API
kubectl port-forward -n xagent svc/xagent-api 8000:80
```

### Option 3: Local Development

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start Redis and PostgreSQL
docker-compose up -d redis postgres chromadb

# Run API
export PYTHONPATH=$PWD/src:$PYTHONPATH
python -m uvicorn xagent.api.rest:app --reload

# Run CLI
python -m xagent.cli.main interactive
```

---

## 🎯 First Steps

### 1. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-11-08T...",
  "checks": {
    "redis": "healthy",
    "postgres": "healthy",
    "chromadb": "healthy"
  }
}
```

### 2. Create Your First Goal

```bash
# Using curl
curl -X POST http://localhost:8000/goals \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build a REST API with authentication",
    "mode": "goal_oriented",
    "priority": 10,
    "completion_criteria": [
      "API endpoints implemented",
      "Authentication working",
      "Tests passing"
    ]
  }'

# Using Python
python examples/basic_usage.py
```

### 3. Start the Agent

```bash
# Using curl
curl -X POST http://localhost:8000/agent/start

# With a specific goal
curl -X POST http://localhost:8000/agent/start?goal_id=<goal-id>
```

### 4. Monitor Progress

```bash
# Check agent status
curl http://localhost:8000/agent/status

# List goals
curl http://localhost:8000/goals

# Get specific goal
curl http://localhost:8000/goals/<goal-id>
```

---

## 📊 View Dashboards

### Grafana Dashboards

1. Open http://localhost:3000
2. Login: `admin` / `admin`
3. Navigate to Dashboards:
   - **Agent Performance**: Cognitive loop, goals, completion time
   - **API Health**: Response time, request rate, errors
   - **System Metrics**: CPU, memory, disk usage

### Metrics (Prometheus)

1. Open http://localhost:9090
2. Try these queries:
   ```promql
   # API request rate
   rate(xagent_api_requests_total[5m])
   
   # Cognitive loop duration
   xagent_cognitive_loop_duration_seconds
   
   # Goal completion rate
   rate(xagent_goals_completed_total[1h])
   ```

### Traces (Jaeger)

1. Open http://localhost:16686
2. Select service: `x-agent-api`
3. Search for traces
4. Analyze request flows and performance

---

## 🔒 Authentication

### Generate Token

```bash
# Login as admin
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin"
  }'

# Response includes access_token
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "username": "admin",
    "role": "admin",
    "scopes": ["read", "write", "admin"]
  }
}
```

### Use Token

```bash
# All subsequent requests
curl http://localhost:8000/goals \
  -H "Authorization: Bearer <your-token>"
```

---

## 🧪 Run Tests

```bash
# All tests
PYTHONPATH=$PWD/src:$PYTHONPATH python -m pytest tests/ -v

# With coverage
PYTHONPATH=$PWD/src:$PYTHONPATH python -m pytest tests/ --cov=src/xagent --cov-report=html

# Unit tests only
PYTHONPATH=$PWD/src:$PYTHONPATH python -m pytest tests/unit/ -v

# Integration tests only
PYTHONPATH=$PWD/src:$PYTHONPATH python -m pytest tests/integration/ -v

# Specific test
PYTHONPATH=$PWD/src:$PYTHONPATH python -m pytest tests/unit/test_goal_engine.py -v
```

---

## 🎨 Run Demonstrations

### Standalone Demo (No External Dependencies)

```bash
PYTHONPATH=$PWD/src:$PYTHONPATH python examples/standalone_demo.py
```

Shows:
- Goal Engine capabilities
- Security Policy Engine
- Rich CLI output
- Success metrics

### Comprehensive Demo (Requires Full Stack)

```bash
# Start all services first
docker-compose up -d

# Run demo
PYTHONPATH=$PWD/src:$PYTHONPATH python examples/comprehensive_demo.py
```

Shows:
- Full agent initialization
- Goal management with sub-goals
- Tool execution
- Policy enforcement
- Metacognition tracking

### Planner Comparison

```bash
PYTHONPATH=$PWD/src:$PYTHONPATH python examples/planner_comparison.py
```

Shows:
- Legacy vs LangGraph planner
- Planning quality comparison
- Performance metrics

---

## 🛠️ Configuration

### Key Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql://xagent:xagent@localhost:5432/xagent

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8001

# Security
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Planner Selection
USE_LANGGRAPH_PLANNER=false  # false=Legacy, true=LangGraph

# Observability
OTLP_ENDPOINT=http://localhost:4317
TRACING_CONSOLE=false
PROMETHEUS_PORT=9090
```

### Customize Planner

Edit `.env`:
```bash
# Use LangGraph planner for advanced workflows
USE_LANGGRAPH_PLANNER=true

# Or use Legacy planner for simple tasks
USE_LANGGRAPH_PLANNER=false
```

---

## 📚 Key Documentation

- **FEATURES.md** (70KB): Complete feature status and progress
- **README.md** (19KB): Project overview and architecture
- **PRODUCTION_VERIFICATION.md** (14.5KB): Production readiness report
- **DEPLOYMENT.md** (18KB): Detailed deployment guide
- **API.md** (21KB): Complete API reference
- **DEVELOPER_GUIDE.md** (17KB): Development workflow
- **OBSERVABILITY.md** (13KB): Monitoring and metrics
- **CACHING.md** (13KB): Redis caching guide

---

## 🐛 Troubleshooting

### API Won't Start

```bash
# Check Redis connection
docker-compose ps redis
docker-compose logs redis

# Check PostgreSQL connection
docker-compose ps postgres
docker-compose logs postgres

# Check API logs
docker-compose logs xagent-api
```

### Tests Failing

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=$PWD/src:$PYTHONPATH

# Check dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run specific test for debugging
python -m pytest tests/unit/test_goal_engine.py -v -s
```

### Docker Issues

```bash
# Reset everything
docker-compose down -v
docker-compose up -d

# Check logs
docker-compose logs -f

# Check disk space
df -h
docker system df
```

### Import Errors

```bash
# Always set PYTHONPATH
export PYTHONPATH=$PWD/src:$PYTHONPATH

# Or add to your shell profile
echo 'export PYTHONPATH=$PWD/src:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc
```

---

## 🔥 Quick Commands Cheat Sheet

```bash
# Development
make test                    # Run all tests
make test-cov               # Run tests with coverage
make lint                   # Run linters
make format                 # Format code
make run-api                # Start API server
make run-cli                # Start CLI

# Docker
make docker-build           # Build images
make docker-up             # Start services
make docker-down           # Stop services
make docker-logs           # View logs

# Deployment
kubectl apply -f k8s/      # Deploy to Kubernetes
helm install xagent ./helm/xagent  # Deploy with Helm
docker-compose up -d       # Start with Docker Compose
```

---

## ✅ Success Criteria

Your X-Agent is ready when:

- [x] Health check returns `"status": "healthy"`
- [x] All services are running (Redis, PostgreSQL, ChromaDB)
- [x] You can create and retrieve goals via API
- [x] Grafana dashboards show data
- [x] Authentication works
- [x] Tests pass

---

## 🎉 Next Steps

Once running:

1. **Explore the API**: http://localhost:8000/docs
2. **Create goals**: Start with simple tasks
3. **Monitor performance**: Check Grafana dashboards
4. **Review logs**: Watch agent decisions in real-time
5. **Run examples**: Learn from working code
6. **Read documentation**: Deep dive into capabilities

---

## 📞 Support

- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/UnknownEngineOfficial/X-Agent/issues
- **Discussions**: https://github.com/UnknownEngineOfficial/X-Agent/discussions

---

**Happy X-Agenting! 🤖**
