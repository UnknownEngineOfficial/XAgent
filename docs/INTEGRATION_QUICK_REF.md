# Open-Source Integration Quick Reference

**Quick Links**: 
- [Full Strategy (FEATURES.md Section 10)](FEATURES.md#10-open-source-component-integration-strategy-)
- [Detailed Roadmap](INTEGRATION_ROADMAP.md)

---

## Component Replacement Summary

### ✅ USE These Open-Source Solutions

| Current/Planned Component | Replace With | Why |
|--------------------------|--------------|-----|
| Custom task scheduler | **Arq** or **Celery** | Proven distributed task queue |
| Goal/Planning engine | **LangGraph** + **CrewAI** | Advanced Chain-of-Thought workflows |
| Tool server | **LangServe** | Standardized, secure tool interface |
| Auth/Security | **OPA** + **Authlib** | Industry-standard policy & auth |
| Monitoring | **Prometheus** + **Grafana** | Complete observability stack |
| Tracing | **OpenTelemetry** | Distributed tracing standard |
| Logging | **Loki** + **Promtail** | Centralized log aggregation |
| CLI framework | **Typer** | Modern, rich CLI builder |

### 🔧 BUILD In-House

| Component | Reason |
|-----------|--------|
| Core agent logic | Unique value proposition |
| Reflection & reward system | Custom learning approach |
| Integration layer | Glue between components |
| Frontend/UI | Project-specific requirements |
| Audit system | X-Agent-specific metrics |

---

## Implementation Timeline (14 Weeks)

```
Weeks 1-4:   Security & Observability (OPA, Authlib, OpenTelemetry, Grafana)
Weeks 5-8:   Tool Management (LangServe, Docker sandbox, Arq/Celery)
Weeks 9-12:  Planning (LangGraph, CrewAI evaluation)
Weeks 13-14: CLI & Polish (Typer, documentation)
```

---

## Quick Start Guide

### Adding Dependencies

**ALWAYS run security check first:**
```bash
# Check new dependencies for vulnerabilities
pip-audit requirements.txt
safety check
```

**Then add to `requirements.txt`:**
```txt
# Phase 2: Security & Observability
opa-python-client>=1.4.1
authlib>=1.3.0
opentelemetry-api>=1.21.0
opentelemetry-sdk>=1.21.0
opentelemetry-instrumentation-fastapi>=0.42b0

# Phase 3: Tools
langserve>=0.0.40
docker>=6.1.0
arq>=0.25.0  # OR celery (already included)

# Phase 4: Planning
crewai>=0.1.0  # langgraph already included

# Phase 5: CLI
typer>=0.9.0
rich>=13.7.0
```

### Docker Compose Updates

**Example: Adding OPA**
```yaml
# docker-compose.yml
services:
  opa:
    image: openpolicyagent/opa:latest
    command: run --server --log-level=info /policies
    volumes:
      - ./config/policies:/policies
    ports:
      - "8181:8181"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8181/health"]
      interval: 10s
      timeout: 5s
      retries: 3
```

---

## Code Examples

### 1. OPA Policy Check

```python
# src/xagent/security/opa_client.py
from opa_client.opa import OpaClient

class PolicyEnforcer:
    def __init__(self):
        self.client = OpaClient(host="opa", port=8181)
    
    async def check_tool_permission(self, user, tool_name, args):
        """Check if user can execute tool with given args"""
        result = self.client.check_permission(
            input_data={
                "user": user.dict(),
                "tool": {"name": tool_name, "args": args}
            },
            policy_name="xagent.tools",
            rule_name="allow"
        )
        return result.get("result", False)
```

### 2. JWT Authentication

```python
# src/xagent/security/auth.py
from authlib.jose import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Security(security)):
    """Verify JWT and return user"""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY
        )
        return payload
    except Exception:
        raise HTTPException(401, "Invalid token")

# Usage in endpoint
@app.post("/tools/execute")
async def execute_tool(
    tool: str,
    user = Depends(verify_token)
):
    if "code_exec" not in user.get("scopes", []):
        raise HTTPException(403, "Insufficient permissions")
    # ... execute tool
```

### 3. OpenTelemetry Tracing

```python
# src/xagent/monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Custom spans
tracer = trace.get_tracer(__name__)

async def execute_plan(self, plan):
    with tracer.start_as_current_span("execute_plan") as span:
        span.set_attribute("plan.steps", len(plan.steps))
        for step in plan.steps:
            with tracer.start_as_current_span(f"step.{step.name}"):
                await self.execute_step(step)
```

### 4. LangServe Tool

```python
# src/xagent/tools/langserve_tools.py
from langchain.tools import tool
from langserve import add_routes

@tool
def execute_code(code: str, language: str = "python") -> str:
    """Execute code in sandbox"""
    # Docker sandbox execution
    return sandbox.run(code, language)

# Register tool
add_routes(
    app,
    execute_code,
    path="/tools/code_exec",
    enabled_endpoints=["invoke", "stream"]
)
```

### 5. Prometheus Metrics

```python
# src/xagent/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
tool_executions = Counter(
    "tool_executions_total",
    "Total tool executions",
    ["tool_name", "status"]
)

tool_duration = Histogram(
    "tool_execution_duration_seconds",
    "Tool execution duration",
    ["tool_name"]
)

# Use in code
with tool_duration.labels(tool_name="code_exec").time():
    result = await execute_code(code)
    tool_executions.labels(
        tool_name="code_exec",
        status="success"
    ).inc()
```

### 6. Typer CLI

```python
# src/xagent/cli/main.py
import typer
from rich import print
from rich.progress import track

app = typer.Typer()

@app.command()
def start(
    goal: str = typer.Argument(..., help="Goal to achieve"),
    mode: str = typer.Option("focus", help="Agent mode")
):
    """Start the X-Agent with a goal"""
    print(f"[bold green]Starting agent with goal:[/bold green] {goal}")
    
    # Show progress
    for step in track(range(100), description="Initializing..."):
        # ... initialization
        pass
    
    print("[bold green]✓[/bold green] Agent started successfully!")

if __name__ == "__main__":
    app()
```

---

## Testing Strategy

### Security Testing
```python
# tests/security/test_opa_integration.py
async def test_tool_permission_denied():
    """Test OPA denies unauthorized tool execution"""
    user = User(scopes=["read"])
    enforcer = PolicyEnforcer()
    
    allowed = await enforcer.check_tool_permission(
        user, "execute_code", {"code": "print('hi')"}
    )
    
    assert not allowed, "Should deny code execution without code_exec scope"
```

### Integration Testing
```python
# tests/integration/test_langserve_tools.py
async def test_code_execution_tool():
    """Test LangServe code execution tool"""
    response = await client.post(
        "/tools/code_exec/invoke",
        json={"code": "print('hello')", "language": "python"}
    )
    
    assert response.status_code == 200
    assert "hello" in response.json()["output"]
```

---

## Migration Checklist

When integrating each component:

- [ ] **Research**: Study docs, examples, best practices
- [ ] **Prototype**: Create minimal proof-of-concept
- [ ] **Security**: Run vulnerability scans on dependencies
- [ ] **Implement**: Write production code with tests
- [ ] **Document**: Update architecture and API docs
- [ ] **Monitor**: Add metrics, logs, and health checks
- [ ] **Deploy**: Gradual rollout with rollback plan
- [ ] **Review**: Post-integration retrospective

---

## Common Pitfalls to Avoid

### ❌ Don't
- Add dependencies without security scanning
- Skip writing integration tests
- Forget to update health checks
- Ignore performance benchmarking
- Couple tightly to framework internals

### ✅ Do
- Use abstraction layers for external components
- Maintain backward compatibility during migration
- Add comprehensive monitoring
- Document configuration options
- Plan for rollback scenarios

---

## Resources

### Documentation
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangServe Docs](https://python.langchain.com/docs/langserve)
- [OPA Docs](https://www.openpolicyagent.org/docs/latest/)
- [Authlib Docs](https://docs.authlib.org/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Typer Docs](https://typer.tiangolo.com/)

### Internal Docs
- [FEATURES.md](FEATURES.md) - Complete feature list
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [INTEGRATION_ROADMAP.md](INTEGRATION_ROADMAP.md) - Detailed implementation plan
- [TESTING.md](TESTING.md) - Testing guidelines

---

## Getting Help

- **Questions**: GitHub Discussions
- **Issues**: GitHub Issues
- **Security**: security@xagent.dev
- **General**: team@xagent.dev

---

**Last Updated**: 2025-11-07  
**Version**: 1.0
