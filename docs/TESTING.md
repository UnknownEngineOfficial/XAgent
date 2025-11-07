# Test Coverage Documentation

## Overview

This document describes the test coverage infrastructure for X-Agent, which achieves **97.15% coverage** for core modules with a **central control point** for managing test execution and coverage reporting.

## Test Coverage Architecture

### Central Control Point

The central control point for test coverage is the `scripts/run_tests.py` script, which provides:

- Unified test execution interface
- Coverage reporting and validation
- Enforcement of 90% coverage threshold
- Separate tracking for unit vs integration tests

### Coverage Thresholds

- **Target Coverage**: 90%
- **Current Core Modules Coverage**: **97.15%** ✅
- **Overall Project Coverage**: 21.58% (includes integration modules)

## Core Modules (Unit Tested)

These modules have comprehensive unit test coverage (90%+):

| Module | Coverage | Tests | Description |
|--------|----------|-------|-------------|
| `xagent.config` | 95.59% | 19 tests | Configuration management |
| `xagent.core.executor` | 100.00% | 10 tests | Action execution engine |
| `xagent.core.goal_engine` | 96.58% | 16 tests | Goal and task management |
| `xagent.core.metacognition` | 98.46% | 14 tests | Self-monitoring and evaluation |
| `xagent.core.planner` | 95.00% | 11 tests | Strategic planning |
| `xagent.utils.logging` | 100.00% | 6 tests | Logging utilities |

**Total: 76 unit tests covering 275 statements**

## Integration Modules (Separate Testing)

These modules require integration testing due to external dependencies:

- `xagent.api.rest` - REST API endpoints (requires FastAPI setup)
- `xagent.api.websocket` - WebSocket gateway (requires async WebSocket setup)
- `xagent.cli.main` - CLI interface (requires terminal interaction)
- `xagent.core.agent` - Main agent (requires full system initialization)
- `xagent.core.cognitive_loop` - Cognitive loop (requires async event loop)
- `xagent.memory.memory_layer` - Memory layer (requires database connections)
- `xagent.security.policy` - Security policies (requires authentication setup)
- `xagent.tools.tool_server` - Tool server (requires external tool integrations)

## Running Tests

### Using the Central Control Script

```bash
# Run all tests with coverage report
python scripts/run_tests.py

# Run unit tests only
python scripts/run_tests.py --unit

# Generate HTML coverage report
python scripts/run_tests.py --report

# Enforce 90% coverage (fail if not met)
python scripts/run_tests.py --strict

# Show coverage for core modules only
python scripts/run_tests.py --core
```

### Using Make Commands

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Run tests with coverage and enforce 90% threshold
make test-cov-report

# Run unit tests only
make test-unit
```

### Using pytest Directly

```bash
# Run all unit tests
PYTHONPATH=src pytest tests/unit/ -v

# Run specific test file
PYTHONPATH=src pytest tests/unit/test_goal_engine.py -v

# Run with coverage
PYTHONPATH=src pytest tests/unit/ --cov=src/xagent --cov-report=html
```

## Test Structure

```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_config.py           # Configuration tests
│   ├── test_executor.py         # Executor tests
│   ├── test_goal_engine.py      # Goal engine tests
│   ├── test_logging.py          # Logging utility tests
│   ├── test_metacognition.py    # Metacognition tests
│   └── test_planner.py          # Planner tests
└── integration/                  # (Future) Integration tests
```

## Coverage Configuration

### .coveragerc

The `.coveragerc` file serves as the central coverage configuration:

```ini
[run]
source = src/xagent
branch = True

[report]
precision = 2
show_missing = True
fail_under = 90

[html]
directory = htmlcov
```

### pyproject.toml

Pytest and coverage settings are also defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --strict-markers"

[tool.coverage.run]
source = ["src/xagent"]
branch = true

[tool.coverage.report]
fail_under = 90
```

## Test Development Guidelines

### Writing Unit Tests

1. **Isolation**: Unit tests should not require external dependencies
2. **Mocking**: Use mocks for complex dependencies
3. **Coverage**: Aim for 90%+ coverage for all new code
4. **Naming**: Follow the pattern `test_<function_name>_<scenario>()`
5. **Documentation**: Include docstrings explaining what is being tested

### Example Test Structure

```python
def test_function_name_success_case():
    """Test that function works correctly in normal case."""
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result.success is True
    assert result.value == expected_value
```

### Coverage Best Practices

1. **Test edge cases**: Empty inputs, None values, boundary conditions
2. **Test error handling**: Exception paths, validation errors
3. **Test state changes**: Before/after comparisons
4. **Test integration points**: Mock external calls, verify interactions

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests with coverage
  run: |
    python scripts/run_tests.py --strict
    
- name: Upload coverage report
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Viewing Coverage Reports

### Terminal Report

```bash
python scripts/run_tests.py --core
```

### HTML Report

```bash
python scripts/run_tests.py --report
# Open htmlcov/index.html in browser
```

### Coverage Metrics

The HTML report provides:
- Line coverage per file
- Branch coverage
- Missing lines highlighted
- Coverage trends over time

## Future Improvements

1. **Integration Tests**: Add tests for API, WebSocket, and database modules
2. **Performance Tests**: Add benchmarking for critical paths
3. **Property-Based Tests**: Use hypothesis for property testing
4. **Mutation Testing**: Use mutmut to verify test quality
5. **Coverage Tracking**: Integrate with Codecov or similar service

## Maintenance

### Adding New Tests

1. Create test file in `tests/unit/test_<module>.py`
2. Write comprehensive tests following guidelines
3. Run `python scripts/run_tests.py --core` to verify coverage
4. Ensure core modules maintain 90%+ coverage

### Updating Coverage Threshold

To adjust the coverage threshold:

1. Update `COVERAGE_THRESHOLD` in `scripts/run_tests.py`
2. Update `fail_under` in `.coveragerc`
3. Update `fail_under` in `pyproject.toml`

## Support

For questions or issues with the test infrastructure:

1. Check this documentation
2. Review test examples in `tests/unit/`
3. Run `python scripts/run_tests.py --help`
4. Open an issue on GitHub

---

**Last Updated**: 2025-11-07  
**Coverage Target**: 90%  
**Current Coverage**: 97.15% (core modules)  
**Total Tests**: 76 unit tests
