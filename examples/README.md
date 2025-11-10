# X-Agent Examples

This directory contains example scripts demonstrating various features of X-Agent.

## 🌟 NEW: Featured Demonstrations (November 2025)

### ⭐ 1. Complete System Showcase (`complete_results_showcase.py`) **[BEST FOR OVERVIEW]**

The ultimate comprehensive demonstration of ALL X-Agent capabilities:

**Features:**
- System architecture visualization
- Complete features matrix (66/66 features = 100%)
- Test results (450/450 passing)
- Performance metrics dashboard
- Deployment options overview
- Live workflow simulation

**Run:**
```bash
cd /home/runner/work/X-Agent/X-Agent
export PYTHONPATH=$(pwd)/src:$PYTHONPATH
python examples/complete_results_showcase.py
```

**Duration:** ~20 seconds  
**Best for:** Getting a complete overview of system capabilities

---

### ⭐ 2. Live Agent Demonstration (`real_agent_demo.py`) **[MOST IMPRESSIVE]**

Shows the complete agent system with REAL execution:

**Features:**
- Hierarchical goal management (1 main + 5 sub-goals)
- Intelligent planning (LLM-based and rule-based)
- Real-time execution and status tracking
- Performance metrics dashboard
- Beautiful terminal visualization

**Run:**
```bash
cd /home/runner/work/X-Agent/X-Agent
export PYTHONPATH=$(pwd)/src:$PYTHONPATH
python examples/real_agent_demo.py
```

**Duration:** ~10 seconds  
**Best for:** Seeing the agent execute real goals in action

---

### ⭐ 3. Tool Execution Demo (`tool_execution_demo.py`) **[TECHNICAL SHOWCASE]**

Demonstrates real tool execution with actual code running:

**Features:**
- Agent thinking and reasoning
- Python code execution (sandbox)
- JavaScript code execution (sandbox)
- File operations (read/write)
- Complex multi-step scenarios
- Multi-tool integration

**Run:**
```bash
cd /home/runner/work/X-Agent/X-Agent
export PYTHONPATH=$(pwd)/src:$PYTHONPATH
python examples/tool_execution_demo.py
```

**Duration:** ~15 seconds  
**Best for:** Understanding tool capabilities and sandboxed execution

---

## 📚 Other Available Examples

### 1. Rate Limiting (`rate_limiting_example.py`) 🆕

**NEW!** Comprehensive rate limiting examples for API protection:
- In-memory rate limiting (development)
- Distributed Redis-based rate limiting (production)
- Custom rate limiting logic per endpoint
- Testing rate limiting behavior
- Monitoring rate limit statistics

**Features 5 Complete Examples**:
1. In-memory rate limiting setup
2. Distributed rate limiting with Redis
3. Custom rate limiting per endpoint
4. Testing and validation
5. Monitoring and admin operations

**Run**:
```bash
cd examples
python rate_limiting_example.py inmemory    # Run in-memory version
python rate_limiting_example.py distributed # Run distributed version
python rate_limiting_example.py test        # Test rate limiting
python rate_limiting_example.py monitor     # Monitor stats
```

**See also**: [Rate Limiting Quick Start Guide](../docs/RATE_LIMITING_QUICKSTART.md)

### 2. Basic Usage (`basic_usage.py`)

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

### 3. Goal Management (`goal_management.py`)

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

### 4. Tool Server Usage (`tool_server_usage.py`)

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
