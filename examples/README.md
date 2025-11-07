# Examples

This directory contains example scripts demonstrating various features of X-Agent.

## Available Examples

### 1. Basic Usage (`basic_usage.py`)

Demonstrates fundamental X-Agent operations:
- Creating and initializing an agent
- Setting up goals
- Sending commands
- Monitoring status
- Clean shutdown

**Run**:
```bash
cd examples
python basic_usage.py
```

### 2. Goal Management (`goal_management.py`)

Shows advanced goal management:
- Creating different goal types (goal-oriented vs continuous)
- Goal hierarchies (parent/child relationships)
- Priority-based scheduling
- Status tracking
- Completion checking

**Run**:
```bash
cd examples
python goal_management.py
```

### 3. Tool Server Usage (`tool_server_usage.py`)

Demonstrates tool system capabilities:
- Creating custom tools
- Registering tools with the server
- Executing tool calls
- Error handling
- Tool discovery

**Run**:
```bash
cd examples
python tool_server_usage.py
```

## Requirements

Make sure you have installed X-Agent dependencies:

```bash
pip install -r ../requirements.txt
```

## Learn More

- [Architecture Documentation](../docs/ARCHITECTURE.md)
- [Quick Start Guide](../docs/QUICKSTART.md)
- [API Reference](http://localhost:8000/docs) (when API is running)
