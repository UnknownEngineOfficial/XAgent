# X-Agent Developer Guide

**Version**: 0.1.0  
**Last Updated**: 2025-11-08

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Core Concepts](#core-concepts)
5. [Development Workflow](#development-workflow)
6. [Testing](#testing)
7. [Code Style & Standards](#code-style--standards)
8. [Adding Features](#adding-features)
9. [Debugging](#debugging)
10. [Common Tasks](#common-tasks)
11. [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- Git
- Code editor (VSCode recommended)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/UnknownEngineOfficial/X-Agent.git
cd X-Agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env

# Start services
docker-compose up -d redis postgres chromadb

# Run tests
make test
```

---

## Development Environment Setup

### VSCode Configuration

Install recommended extensions:
- Python
- Pylance
- Black Formatter
- autoDocstring
- GitLens

**`.vscode/settings.json`:**
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### Environment Variables

Create `.env` file for local development:

```bash
# Development Configuration
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# API
API_HOST=127.0.0.1
API_PORT=8000

# Database
DATABASE_URL=postgresql://xagent:xagent@localhost:5432/xagent
REDIS_URL=redis://localhost:6379/0

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Security (dev keys - change in production!)
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256

# OpenAI (optional - for LLM features)
OPENAI_API_KEY=sk-your-key-here

# Monitoring
PROMETHEUS_PORT=9090
OTLP_ENDPOINT=http://localhost:4318
```

---

## Project Structure

```
X-Agent/
├── src/xagent/              # Main source code
│   ├── api/                 # REST and WebSocket APIs
│   │   ├── rest.py          # REST API endpoints
│   │   └── websocket.py     # WebSocket gateway
│   ├── core/                # Core agent logic
│   │   ├── agent.py         # Main agent orchestration
│   │   ├── cognitive_loop.py # Thinking cycle
│   │   ├── goal_engine.py   # Goal management
│   │   ├── planner.py       # Planning logic
│   │   ├── executor.py      # Action execution
│   │   └── metacognition.py # Self-monitoring
│   ├── planning/            # Advanced planning
│   │   └── langgraph_planner.py  # LangGraph planner
│   ├── memory/              # Memory system
│   │   └── memory_layer.py  # Memory management
│   ├── tools/               # Agent tools
│   │   ├── langserve_tools.py  # LangChain tools
│   │   └── tool_server.py   # Tool execution
│   ├── sandbox/             # Code execution
│   │   └── docker_sandbox.py  # Docker isolation
│   ├── security/            # Security components
│   │   ├── auth.py          # Authentication
│   │   ├── opa_client.py    # Policy enforcement
│   │   └── policy.py        # Policy definitions
│   ├── monitoring/          # Observability
│   │   ├── metrics.py       # Prometheus metrics
│   │   └── tracing.py       # OpenTelemetry tracing
│   ├── tasks/               # Background tasks
│   │   ├── celery_app.py    # Celery configuration
│   │   └── worker.py        # Task workers
│   ├── cli/                 # Command-line interface
│   │   └── main.py          # Typer CLI
│   ├── utils/               # Utilities
│   │   └── logging.py       # Structured logging
│   ├── config.py            # Configuration
│   └── health.py            # Health checks
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
├── config/                  # Configuration files
│   ├── grafana/             # Grafana dashboards
│   ├── prometheus/          # Prometheus config
│   └── policies/            # OPA policies
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── pyproject.toml           # Python project config
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── Makefile                 # Build automation
└── docker-compose.yml       # Docker services
```

---

## Core Concepts

### 1. Agent Architecture

The agent follows a **cognitive loop** pattern:

```python
# Simplified cognitive loop
while agent.is_running:
    # 1. Perceive - Get current state
    state = agent.perceive()
    
    # 2. Think - Process information
    thoughts = agent.think(state)
    
    # 3. Plan - Decide what to do
    plan = agent.plan(thoughts)
    
    # 4. Execute - Take action
    result = agent.execute(plan)
    
    # 5. Reflect - Learn from outcome
    agent.reflect(result)
```

### 2. Goal System

Goals are hierarchical and can be:

- **goal_oriented**: Completes when criteria are met
- **continuous**: Runs indefinitely (monitoring, maintenance)

```python
from xagent.core.goal_engine import GoalEngine, GoalMode

# Create goal engine
engine = GoalEngine()

# Add a goal
goal_id = engine.add_goal(
    description="Build authentication system",
    mode=GoalMode.GOAL_ORIENTED,
    priority=8,
    completion_criteria=[
        "User registration works",
        "Login returns JWT token",
        "Tests pass"
    ]
)

# Check status
status = engine.get_goal_status(goal_id)
```

### 3. Tool System

Tools are LangChain-compatible functions:

```python
from langchain.tools import tool
from pydantic import BaseModel, Field

class CalculateInput(BaseModel):
    """Input for calculate tool."""
    expression: str = Field(..., description="Math expression to evaluate")

@tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### 4. Memory System

Three-tier memory architecture:

```python
from xagent.memory.memory_layer import MemoryLayer

memory = MemoryLayer()

# Short-term (recent context)
memory.add_to_short_term("User requested authentication feature")

# Long-term (persistent knowledge)
memory.store_knowledge("authentication", {
    "method": "JWT",
    "library": "authlib",
    "security": "HS256"
})

# Retrieve
context = memory.get_relevant_context("authentication")
```

---

## Development Workflow

### 1. Feature Branch Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes
# ... edit files ...

# Run tests
make test

# Format code
make format

# Lint
make lint

# Commit
git add .
git commit -m "feat: add my feature"

# Push
git push origin feature/my-feature

# Create PR on GitHub
```

### 2. Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add user authentication
fix: resolve memory leak in cognitive loop
docs: update API documentation
test: add integration tests for goals
refactor: simplify planner logic
perf: optimize database queries
chore: update dependencies
```

---

## Testing

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
pytest tests/integration/

# With coverage
make test-cov

# Specific test file
pytest tests/unit/test_goal_engine.py -v

# Specific test
pytest tests/unit/test_goal_engine.py::test_add_goal -v
```

### Writing Tests

**Unit Test Example:**

```python
# tests/unit/test_my_feature.py
import pytest
from xagent.core.my_feature import MyFeature

@pytest.fixture
def my_feature():
    """Create MyFeature instance for testing."""
    return MyFeature()

def test_my_feature_works(my_feature):
    """Test that my feature works correctly."""
    result = my_feature.do_something()
    assert result == expected_value

@pytest.mark.asyncio
async def test_async_feature(my_feature):
    """Test async functionality."""
    result = await my_feature.async_operation()
    assert result is not None
```

**Integration Test Example:**

```python
# tests/integration/test_api_my_feature.py
import pytest
from httpx import AsyncClient
from xagent.api.rest import app

@pytest.mark.asyncio
async def test_api_endpoint():
    """Test API endpoint integration."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/my-endpoint",
            json={"data": "test"}
        )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
```

### Test Coverage

Maintain 90%+ coverage for core modules:

```bash
# Generate coverage report
pytest --cov=xagent --cov-report=html

# View report
open htmlcov/index.html
```

---

## Code Style & Standards

### Code Formatting

Use **Black** for consistent formatting:

```bash
# Format all code
make format

# Or manually
black src/ tests/
```

### Linting

Use **Ruff** for fast linting:

```bash
# Lint all code
make lint

# Or manually
ruff check src/ tests/
```

### Type Checking

Use **mypy** for type safety:

```bash
# Check types
mypy src/ --ignore-missing-imports
```

### Docstrings

Use Google-style docstrings:

```python
def my_function(param1: str, param2: int) -> bool:
    """Short description of function.
    
    Longer description if needed. Explain what the function does,
    its purpose, and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param2 is negative
    
    Example:
        >>> result = my_function("test", 42)
        >>> print(result)
        True
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")
    return len(param1) > param2
```

---

## Adding Features

### 1. Adding a New API Endpoint

```python
# src/xagent/api/rest.py

from fastapi import Depends
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    """Request model."""
    data: str = Field(..., description="Input data")

class MyResponse(BaseModel):
    """Response model."""
    result: str = Field(..., description="Output result")

@app.post("/my-endpoint", response_model=MyResponse, tags=["MyFeature"])
async def my_endpoint(
    request: MyRequest,
    user: User = Depends(verify_token)
) -> MyResponse:
    """
    My new endpoint.
    
    Requires authentication with agent:write scope.
    """
    # Implement logic
    result = process_data(request.data)
    return MyResponse(result=result)
```

### 2. Adding a New Tool

```python
# src/xagent/tools/langserve_tools.py

from langchain.tools import tool
from pydantic import BaseModel, Field

class MyToolInput(BaseModel):
    """Input schema for my tool."""
    param: str = Field(..., description="Parameter description")

@tool(args_schema=MyToolInput)
def my_tool(param: str) -> str:
    """Tool description for LLM."""
    # Implement tool logic
    result = do_something(param)
    return f"Result: {result}"
```

### 3. Adding a New Goal Type

```python
# src/xagent/core/goal_engine.py

# Add new mode to GoalMode enum
class GoalMode(Enum):
    GOAL_ORIENTED = "goal_oriented"
    CONTINUOUS = "continuous"
    MY_NEW_MODE = "my_new_mode"  # Add this

# Update goal processing logic
def process_goal(self, goal_id: str) -> None:
    goal = self.get_goal(goal_id)
    
    if goal.mode == GoalMode.MY_NEW_MODE:
        # Handle new mode
        self._process_new_mode(goal)
```

### 4. Adding Metrics

```python
# src/xagent/monitoring/metrics.py

from prometheus_client import Counter, Histogram

# Define metrics
my_feature_counter = Counter(
    'x_agent_my_feature_total',
    'Total my feature operations',
    ['status']
)

my_feature_duration = Histogram(
    'x_agent_my_feature_duration_seconds',
    'Duration of my feature operations'
)

# Use metrics
def my_feature_function():
    with my_feature_duration.time():
        try:
            # Do work
            result = do_work()
            my_feature_counter.labels(status='success').inc()
            return result
        except Exception as e:
            my_feature_counter.labels(status='error').inc()
            raise
```

---

## Debugging

### Local Debugging

**Using VSCode Debugger:**

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "xagent.api.rest:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

### Logging

Use structured logging:

```python
from xagent.utils.logging import get_logger

logger = get_logger(__name__)

# Different log levels
logger.debug("Detailed debugging info", extra={"user_id": user_id})
logger.info("Normal operation", extra={"goal_id": goal_id})
logger.warning("Something unexpected", extra={"error": str(e)})
logger.error("Error occurred", exc_info=True)
```

### Distributed Tracing

Add tracing to functions:

```python
from xagent.monitoring.tracing import trace_operation

@trace_operation("my_operation")
async def my_function():
    """Function with tracing."""
    # Work is automatically traced
    result = await do_work()
    return result
```

View traces in Jaeger: http://localhost:16686

---

## Common Tasks

### Starting the API Server

```bash
# Development mode with auto-reload
uvicorn xagent.api.rest:app --reload --port 8000

# Or using make
make run-api
```

### Running the Agent

```bash
# Command line
python -m xagent.cli start

# Or using make
make run-agent
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding Dependencies

```bash
# Add to requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# Install
pip install -r requirements.txt

# Check for security vulnerabilities
pip-audit
```

### Updating Documentation

```bash
# Edit markdown files in docs/

# Generate API docs from code
python scripts/generate_api_docs.py

# Preview docs (if using MkDocs)
mkdocs serve
```

---

## Contributing

### Pull Request Process

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** and add tests
4. **Run tests**: `make test`
5. **Format code**: `make format`
6. **Lint code**: `make lint`
7. **Commit**: `git commit -m "feat: add amazing feature"`
8. **Push**: `git push origin feature/amazing-feature`
9. **Open Pull Request** on GitHub
10. **Address review comments**
11. **Merge** when approved

### Code Review Guidelines

**For Authors:**
- Keep PRs small and focused
- Write clear descriptions
- Add tests for new features
- Update documentation
- Respond to feedback promptly

**For Reviewers:**
- Be respectful and constructive
- Focus on code quality and maintainability
- Check test coverage
- Verify documentation updates
- Test the changes locally

### Release Process

```bash
# Update version
bumpversion minor  # or major, patch

# Update CHANGELOG.md

# Create release commit
git commit -am "chore: release v0.2.0"

# Tag release
git tag v0.2.0

# Push
git push && git push --tags

# GitHub Actions will build and publish
```

---

## Additional Resources

- [API Documentation](API.md)
- [Architecture Overview](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Testing Documentation](TESTING.md)
- [Observability Guide](OBSERVABILITY.md)

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [pytest Documentation](https://docs.pytest.org/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

---

## Getting Help

- **Documentation**: Check docs/ directory
- **Issues**: [GitHub Issues](https://github.com/UnknownEngineOfficial/X-Agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/UnknownEngineOfficial/X-Agent/discussions)
- **Stack Overflow**: Tag with `x-agent`

---

**Happy Coding!** 🚀

**Last Updated**: 2025-11-08  
**Maintained by**: X-Agent Contributors
