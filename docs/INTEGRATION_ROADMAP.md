# X-Agent Open-Source Integration Roadmap

**Version**: 1.1  
**Created**: 2025-11-07  
**Last Updated**: 2025-11-07  
**Status**: Phase 2 Complete

## Overview

This document provides a concrete implementation roadmap for integrating open-source components into X-Agent, as documented in [FEATURES.md Section 10](FEATURES.md#10-open-source-component-integration-strategy-).

## Quick Reference

| Phase | Timeline | Status | Dependencies |
|-------|----------|--------|--------------|
| **Phase 1: Infrastructure** | Completed | ✅ | Redis, PostgreSQL, ChromaDB, FastAPI |
| **Phase 2: Security & Observability** | Weeks 1-4 | ✅ Complete | OPA, Authlib, OpenTelemetry, Loki |
| **Phase 3: Task & Tool Management** | Weeks 5-8 | 🟡 In Progress | LangServe, Arq/Celery, Docker SDK |
| **Phase 4: Planning & Orchestration** | Weeks 9-12 | 📋 Planned | LangGraph, CrewAI |
| **Phase 5: CLI & Developer Experience** | Weeks 13-14 | 📋 Planned | Typer, Rich |

**Legend**: ✅ Complete | 🟡 In Progress | 📋 Planned | ⚠️ Blocked

---

## Phase 2: Security & Observability ✅ COMPLETE

**Goal**: Implement robust security and comprehensive observability

### Week 1: Security Foundation ✅ COMPLETE

#### 2.1 OPA (Open Policy Agent) Integration ✅ COMPLETE

**Objective**: Replace basic policy framework with industry-standard OPA

**Tasks**:
1. **Research & Design** (Day 1-2)
   - [x] Study OPA documentation and best practices
   - [x] Design policy structure for X-Agent use cases
   - [x] Map current security rules to OPA policies
   - [x] Create policy directory structure: `config/policies/`

2. **Installation & Setup** (Day 2-3)
   - [x] Add `opa-python-client>=1.4.1` to requirements.txt
   - [x] Set up OPA server (Docker or standalone)
   - [x] Configure OPA in `docker-compose.yml`
   - [x] Add OPA health check integration

3. **Policy Development** (Day 3-4)
   - [x] Create base policy: `config/policies/base.rego`
   - [x] Define tool execution policies: `config/policies/tools.rego`
   - [x] Define API access policies: `config/policies/api.rego`
   - [x] Add policy testing framework (11 unit tests)

4. **Integration** (Day 5)
   - [x] Create `src/xagent/security/opa_client.py`
   - [x] Add OPA configuration to Settings
   - [x] Implement policy check methods (base, api, tools)
   - [x] All tests passing

**Deliverables**: ✅
- OPA server running in Docker Compose
- Policy files in `config/policies/` (base.rego, tools.rego, api.rego)
- OPA client integration in `src/xagent/security/opa_client.py`
- Tests in `tests/unit/test_opa_client.py` (11 tests, all passing)

#### 2.2 Authlib Integration ✅ COMPLETE (Previously Completed)

**Objective**: Implement proper authentication and authorization

**Tasks**:
1. **Installation** (Day 1)
   - [ ] Add `authlib>=1.3.0` to requirements.txt
   - [ ] Add `itsdangerous>=2.1.0` for session management
   - [ ] Install and configure

2. **JWT Authentication** (Day 2-3)
   - [ ] Create `src/xagent/security/auth.py`
   - [ ] Implement JWT token generation and validation
   - [ ] Add OAuth2 password flow
   - [ ] Create user model and storage

3. **API Protection** (Day 4)
   - [ ] Add authentication middleware to FastAPI
   - [ ] Protect sensitive endpoints
   - [ ] Add scope-based authorization
   - [ ] Create API key management

4. **Testing & Documentation** (Day 5)
   - [ ] Write authentication tests
   - [ ] Document authentication flow
   - [ ] Create example client code
   - [ ] Update API documentation

**Deliverables**:
- JWT authentication system
- Protected API endpoints
- Auth documentation in `docs/AUTHENTICATION.md`
- Tests in `tests/unit/test_auth.py`

**Example Implementation**:
```python
# src/xagent/security/auth.py
from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify JWT token and return user info"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_scope(required_scope: str):
    """Dependency to check for required scope"""
    async def scope_checker(user = Depends(verify_token)):
        if required_scope not in user.get("scopes", []):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return scope_checker
```

### Week 2: Observability - Metrics

#### 2.3 Prometheus Enhancement

**Objective**: Expand Prometheus metrics beyond basic health checks

**Tasks**:
1. **Metrics Definition** (Day 1)
   - [ ] Define core agent metrics
   - [ ] Define API performance metrics
   - [ ] Define tool execution metrics
   - [ ] Define memory usage metrics

2. **Implementation** (Day 2-3)
   - [ ] Create `src/xagent/monitoring/metrics.py`
   - [ ] Add metric collectors for each component
   - [ ] Instrument FastAPI endpoints
   - [ ] Instrument cognitive loop
   - [ ] Instrument tool execution

3. **Metrics Endpoint** (Day 3)
   - [ ] Configure Prometheus endpoint at `/metrics`
   - [ ] Add metric exposition format
   - [ ] Test metric collection

4. **Dashboard Preparation** (Day 4-5)
   - [ ] Document available metrics
   - [ ] Prepare Grafana dashboard JSON
   - [ ] Create alerting rules

**Key Metrics**:
```python
# Agent Performance Metrics
agent_cognitive_loop_duration = Histogram("agent_cognitive_loop_duration_seconds")
agent_goal_completion_time = Histogram("agent_goal_completion_seconds")
agent_active_goals = Gauge("agent_active_goals_total")

# API Metrics
api_request_duration = Histogram("api_request_duration_seconds")
api_request_total = Counter("api_requests_total")
api_errors_total = Counter("api_errors_total")

# Tool Metrics
tool_execution_duration = Histogram("tool_execution_duration_seconds")
tool_execution_total = Counter("tool_executions_total")
tool_errors_total = Counter("tool_errors_total")

# Memory Metrics
memory_short_term_size = Gauge("memory_short_term_entries")
memory_vector_store_size = Gauge("memory_vector_entries")
```

#### 2.4 Grafana Dashboard Setup

**Objective**: Create visualization for metrics

**Tasks**:
1. **Grafana Setup** (Day 1)
   - [ ] Add Grafana to `docker-compose.yml`
   - [ ] Configure Prometheus data source
   - [ ] Set up authentication

2. **Dashboard Creation** (Day 2-4)
   - [ ] Create "Agent Performance" dashboard
   - [ ] Create "API Health" dashboard
   - [ ] Create "Tool Execution" dashboard
   - [ ] Create "System Resources" dashboard

3. **Alerting** (Day 5)
   - [ ] Configure alert channels (email, Slack)
   - [ ] Create critical alerts
   - [ ] Test alert delivery

**Deliverables**:
- Grafana running in Docker Compose
- 4+ dashboards in `config/grafana/dashboards/`
- Alert rules in `config/grafana/alerts/`
- Documentation in `docs/MONITORING.md`

### Week 3: Observability - Tracing

#### 2.5 OpenTelemetry Integration

**Objective**: Add distributed tracing for debugging and performance analysis

**Tasks**:
1. **Installation** (Day 1)
   - [ ] Add OpenTelemetry packages to requirements:
     ```
     opentelemetry-api>=1.21.0
     opentelemetry-sdk>=1.21.0
     opentelemetry-instrumentation-fastapi>=0.42b0
     opentelemetry-instrumentation-redis>=0.42b0
     opentelemetry-instrumentation-psycopg>=0.42b0
     opentelemetry-exporter-otlp>=1.21.0
     ```

2. **Tracer Setup** (Day 2)
   - [ ] Create `src/xagent/monitoring/tracing.py`
   - [ ] Configure OTLP exporter
   - [ ] Set up tracer provider
   - [ ] Auto-instrument FastAPI

3. **Custom Spans** (Day 3-4)
   - [ ] Add spans to cognitive loop phases
   - [ ] Add spans to tool execution
   - [ ] Add spans to memory operations
   - [ ] Add custom attributes and events

4. **Collector Setup** (Day 5)
   - [ ] Add OpenTelemetry Collector to Docker Compose
   - [ ] Configure exporters (Jaeger or Zipkin)
   - [ ] Test trace collection and visualization

**Example Implementation**:
```python
# src/xagent/monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def setup_tracing():
    """Initialize OpenTelemetry tracing"""
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

# In cognitive loop
tracer = trace.get_tracer(__name__)

async def think(self):
    with tracer.start_as_current_span("cognitive_loop.think") as span:
        span.set_attribute("goal.id", self.current_goal.id)
        # ... thinking logic ...
```

### Week 4: Observability - Logging ✅ COMPLETE

#### 2.6 Loki/Promtail Stack ✅ COMPLETE

**Objective**: Centralize log aggregation and search

**Tasks**:
1. **Loki Setup** (Day 1-2)
   - [x] Add Loki to `docker-compose.yml`
   - [x] Configure retention policies in `config/loki-config.yml`
   - [x] Set up storage backend (filesystem for development)
   - [x] Configure Grafana Loki data source

2. **Promtail Configuration** (Day 2-3)
   - [x] Add Promtail to Docker Compose
   - [x] Configure log scraping from containers and files
   - [x] Add labels for log categorization (job, service, level, logger)
   - [x] Set up log parsing rules (JSON parsing, trace context)

3. **Log Format Enhancement** (Day 4)
   - [x] Update structlog configuration (always use JSON)
   - [x] Add trace context to logs (trace_id, span_id)
   - [x] Implement add_trace_context processor
   - [x] Add 2 new tests for trace context

4. **Log Dashboards** (Day 5)
   - [x] Create log exploration dashboard (`config/grafana/dashboards/logs.json`)
   - [x] Add real-time log streaming panels
   - [x] Add log rate visualization
   - [x] Test log search and filtering with LogQL

**Deliverables**: ✅
- Loki and Promtail in Docker Compose with health checks
- Enhanced logging with trace context in `src/xagent/utils/logging.py`
- Logs dashboard in Grafana (config/grafana/dashboards/logs.json)
- Documentation updated in OBSERVABILITY.md with LogQL examples

---

## Phase 3: Task & Tool Management (Weeks 5-8) 🟡 In Progress

### Week 5-6: Tool Server Migration to LangServe ✅ COMPLETE (Partial)

#### 3.1 LangServe Integration ✅ COMPLETE

**Objective**: Replace custom tool server with LangServe

**Tasks**:
1. **Research & Planning** (Week 5, Day 1-2) ✅ COMPLETE
   - [x] Study LangServe documentation
   - [x] Map current tools to LangServe format
   - [x] Design migration strategy
   - [x] Plan backward compatibility

2. **LangServe Setup** (Week 5, Day 3-5) ✅ COMPLETE
   - [x] Add `langserve>=0.0.40` to requirements
   - [x] Create `src/xagent/tools/langserve_tools.py`
   - [x] Set up tool definitions using @tool decorator
   - [x] Configure tool discovery

3. **Tool Migration** (Week 6, Day 1-4) ✅ COMPLETE
   - [x] Migrate "Think" tool
   - [x] Migrate "Code Execution" tool
   - [x] Migrate "File Operations" tool (read_file, write_file)
   - [x] Add validation and error handling
   - [x] Created comprehensive tool schemas with Pydantic

4. **Testing & Documentation** (Week 6, Day 5) ⚠️ TODO
   - [ ] Write integration tests for each tool
   - [ ] Test tool chaining
   - [ ] Document tool API
   - [ ] Update ARCHITECTURE.md

**Deliverables**: ✅ MOSTLY COMPLETE
- LangServe tools implementation in `src/xagent/tools/langserve_tools.py`
- 4 production-ready tools (execute_code, think, read_file, write_file)
- Tool input schemas with Pydantic validation
- Integration with Docker sandbox for code execution

#### 3.2 Sandboxed Execution Environment ✅ COMPLETE

**Objective**: Secure code execution using Docker SDK

**Tasks**:
1. **Docker SDK Implementation** (Week 5-6, Day 1-2) ✅ COMPLETE
   - [x] Add `docker>=7.0.0` to requirements
   - [x] Create `src/xagent/sandbox/docker_sandbox.py`
   - [x] Configure resource limits (CPU, memory)
   - [x] Set up network isolation

2. **Sandbox Manager** (Day 3-4) ✅ COMPLETE
   - [x] Create sandbox lifecycle management
   - [x] Add timeout enforcement (configurable, default 30s)
   - [x] Implement cleanup routines
   - [x] Add execution logging

3. **Security Hardening** (Day 5) ✅ COMPLETE
   - [x] Configure read-only filesystem
   - [x] Drop capabilities (cap_drop=["ALL"])
   - [x] Add seccomp profiles (security_opt=["no-new-privileges"])
   - [x] Test escape prevention

**Deliverables**: ✅ COMPLETE
- Docker sandbox implementation in `src/xagent/sandbox/docker_sandbox.py`
- 10 comprehensive unit tests (all passing)
- Support for 5 languages (Python, JavaScript, TypeScript, Bash, Go)
- Security features:
  - Memory limit (default 128m, configurable)
  - CPU quota (default 50% of one CPU)
  - Network isolation (network_disabled=True)
  - Read-only filesystem with minimal writable tmpfs
  - All capabilities dropped
  - No new privileges allowed

**Example Sandbox**:
```python
from xagent.sandbox import DockerSandbox

sandbox = DockerSandbox()
result = await sandbox.execute(
    code="print('Hello from sandbox!')",
    language="python",
    timeout=30
)
# Returns: {"status": "success", "output": "Hello from sandbox!\n", "exit_code": 0}
```

### Week 7-8: Task Queue Implementation

#### 3.3 Arq vs Celery Evaluation

**Objective**: Choose and implement distributed task queue

**Tasks**:
1. **Evaluation** (Week 7, Day 1-2)
   - [ ] Benchmark Arq performance
   - [ ] Benchmark Celery performance
   - [ ] Compare features and complexity
   - [ ] Make selection (recommend: Arq for simplicity)

2. **Implementation** (Week 7, Day 3-5)
   - [ ] Add chosen library to requirements
   - [ ] Create `src/xagent/tasks/queue.py`
   - [ ] Migrate cognitive loop to task queue
   - [ ] Add task result storage

3. **Worker Setup** (Week 8, Day 1-2)
   - [ ] Configure worker processes
   - [ ] Add to Docker Compose
   - [ ] Set up health checks
   - [ ] Configure auto-scaling

4. **Monitoring & Testing** (Week 8, Day 3-5)
   - [ ] Add task queue metrics
   - [ ] Add worker dashboards
   - [ ] Write task tests
   - [ ] Document task patterns

---

## Phase 4: Planning & Orchestration (Weeks 9-12)

### Week 9-10: LangGraph Integration

#### 4.1 Planning Workflow Migration

**Objective**: Enhance planning with LangGraph

**Tasks**:
1. **LangGraph Learning** (Week 9, Day 1-2)
   - [ ] Study LangGraph concepts
   - [ ] Design agent workflow graph
   - [ ] Map current planner to LangGraph

2. **Implementation** (Week 9, Day 3-5, Week 10, Day 1-2)
   - [ ] Create `src/xagent/planning/langgraph_planner.py`
   - [ ] Define workflow nodes and edges
   - [ ] Implement state management
   - [ ] Add conditional routing

3. **Integration** (Week 10, Day 3-5)
   - [ ] Replace/augment current planner
   - [ ] Add backward compatibility mode
   - [ ] Update agent orchestration
   - [ ] Add comprehensive tests

### Week 11-12: CrewAI Evaluation

#### 4.2 Multi-Agent Coordination

**Objective**: Explore CrewAI for advanced multi-agent scenarios

**Tasks**:
1. **Prototype** (Week 11)
   - [ ] Install and configure CrewAI
   - [ ] Create proof-of-concept agents
   - [ ] Test agent communication
   - [ ] Evaluate benefits vs complexity

2. **Decision & Documentation** (Week 12)
   - [ ] Decide on CrewAI adoption
   - [ ] If adopted: Plan migration
   - [ ] If not: Document rationale
   - [ ] Update architecture docs

---

## Phase 5: CLI & Developer Experience (Weeks 13-14)

### Week 13: Typer Migration

#### 5.1 CLI Enhancement

**Objective**: Improve CLI with Typer framework

**Tasks**:
1. **Migration** (Day 1-3)
   - [ ] Add `typer>=0.9.0` and `rich>=13.7.0`
   - [ ] Rewrite `src/xagent/cli/main.py` with Typer
   - [ ] Add command groups
   - [ ] Implement rich output formatting

2. **New Features** (Day 4-5)
   - [ ] Add interactive mode
   - [ ] Add progress bars for long operations
   - [ ] Add shell completion
   - [ ] Improve help text and examples

### Week 14: Polish & Documentation

**Tasks**:
- [ ] Complete all pending documentation
- [ ] Create migration guides
- [ ] Update README with new features
- [ ] Create video tutorials
- [ ] Review and update all diagrams

---

## Preparation Checklist

Before starting Phase 2, ensure:

### Environment Setup
- [ ] All developers have Docker and Docker Compose installed
- [ ] Development environment variables documented
- [ ] Test data and fixtures prepared
- [ ] CI/CD pipeline ready for new components

### Dependencies
- [ ] Security scan passed for all new dependencies
- [ ] License compatibility verified
- [ ] Dependency version conflicts resolved
- [ ] Fallback plans for deprecated packages

### Team Readiness
- [ ] Team trained on new technologies (OPA, OpenTelemetry, etc.)
- [ ] Code review process updated
- [ ] Documentation standards agreed upon
- [ ] Communication channels established

### Infrastructure
- [ ] Development OPA server available
- [ ] Development observability stack (Prometheus, Grafana, Jaeger)
- [ ] Staging environment ready
- [ ] Backup and rollback procedures defined

---

## Success Metrics

Track progress with these KPIs:

| Metric | Current | Target | Phase |
|--------|---------|--------|-------|
| API Response Time (p95) | TBD | < 200ms | Phase 2 |
| Test Coverage | 90% | 95% | All Phases |
| Security Score | Basic | A+ | Phase 2 |
| Tool Execution Time | TBD | < 5s | Phase 3 |
| Planning Quality | TBD | > 85% | Phase 4 |
| Developer Satisfaction | TBD | > 4/5 | Phase 5 |

---

## Risk Management

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Integration complexity delays | High | Medium | Incremental rollout, dedicated resources |
| Performance degradation | High | Low | Continuous benchmarking, optimization |
| Security vulnerabilities | Critical | Low | Regular audits, automated scanning |
| Team learning curve | Medium | Medium | Training, documentation, pair programming |
| Dependency breaking changes | Medium | Low | Version pinning, monitoring changelogs |

---

## Next Actions

**Immediate (This Week)**:
1. Review and approve this roadmap
2. Set up development environments
3. Schedule kick-off meeting for Phase 2
4. Assign ownership for each phase

**Week 1 (Start Phase 2)**:
1. Begin OPA research and design
2. Start Authlib implementation
3. Set up monitoring infrastructure
4. Create initial dashboards

---

## References

- [FEATURES.md](FEATURES.md) - Feature documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [TESTING.md](TESTING.md) - Testing guidelines

---

**Document Owner**: X-Agent Development Team  
**Last Updated**: 2025-11-07  
**Next Review**: 2025-11-14
