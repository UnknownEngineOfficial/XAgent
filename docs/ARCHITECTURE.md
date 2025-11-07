# X-Agent Architecture Documentation

## Overview

X-Agent is an autonomous AI agent system implementing a modular, event-driven architecture with persistent cognitive loops and multi-tier memory management.

## System Architecture

```
┌─────────────────────────────────────┐
│ X-Agent Core                        │
│ ├─ Goal Engine (Purpose Core)       │
│ ├─ Cognitive Loop                   │
│ ├─ Memory Layer                     │
│ ├─ Planner & Executor               │
│ ├─ Meta-Cognition Monitor           │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ Tool Server (Action Layer)          │
│ ├─ Code Tools                       │
│ ├─ Search Tools                     │
│ ├─ FileOps / ShellOps               │
│ ├─ Network Tools                    │
│ └─ Secure Execution Sandbox         │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ I/O & Interface Layer               │
│ ├─ WebSocket Gateway (Realtime)     │
│ ├─ REST API                         │
│ ├─ CLI / Chat / WebUI               │
│ └─ Log & Audit Bus                  │
└─────────────────────────────────────┘
```

## Core Components

### 1. Goal Engine (Purpose Core)

**Location**: `src/xagent/core/goal_engine.py`

The Goal Engine manages the agent's objectives in two modes:

- **Goal-Oriented Mode**: Works toward specific completion criteria
- **Continuous Mode**: Operates indefinitely, reacting to events

**Key Features**:
- Hierarchical goal management (goals → sub-goals)
- Priority-based goal scheduling
- Completion criteria tracking
- Goal lifecycle management (pending → in_progress → completed)

### 2. Cognitive Loop

**Location**: `src/xagent/core/cognitive_loop.py`

Implements the continuous thinking process:

```
Perception → Interpretation → Planning → Execution → Reflection → Loop
```

### 3. Memory Layer

**Location**: `src/xagent/memory/memory_layer.py`

Three-tier memory system:

| Tier | Storage | Purpose | TTL |
|------|---------|---------|-----|
| **Short-term** | Redis | Active context, current tasks | 1 hour |
| **Medium-term** | PostgreSQL | Project history, sessions | Configurable |
| **Long-term** | ChromaDB | Semantic knowledge, patterns | Permanent |

### 4. Planner & Executor

Creates strategic action plans and executes them.

### 5. Meta-Cognition Monitor

Self-monitoring and evaluation:
- Performance tracking
- Error pattern detection
- Infinite loop detection

## Deployment

### Docker Compose

```bash
docker-compose up -d
```

### Standalone

```bash
pip install -r requirements.txt
python -m xagent.core.agent
```

See full documentation for details.
