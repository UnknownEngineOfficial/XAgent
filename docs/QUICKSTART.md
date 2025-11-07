# X-Agent Quick Start Guide

## Installation

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/UnknownEngineOfficial/X-Agent.git
cd X-Agent
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Edit `.env` and add your API keys:
```bash
OPENAI_API_KEY=your_key_here
```

4. Start services:
```bash
docker-compose up -d
```

5. Access the services:
- REST API: http://localhost:8000
- WebSocket: ws://localhost:8001
- Prometheus: http://localhost:9090

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up databases:
- Redis: `docker run -d -p 6379:6379 redis:7-alpine`
- PostgreSQL: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:15-alpine`

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run agent:
```bash
python -m xagent.core.agent
```

## Usage Examples

### CLI Usage

```bash
python -m xagent.cli.main
```

Commands:
```
start Create a web application
goal Build a REST API
status
command Add authentication
feedback The API looks good
stop
```

### REST API Usage

Start agent:
```bash
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"description": "Create a project", "mode": "goal_oriented"}'
```

Get status:
```bash
curl http://localhost:8000/status
```

Send command:
```bash
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -d '{"command": "Add unit tests"}'
```

### WebSocket Usage

```javascript
const ws = new WebSocket('ws://localhost:8001/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'start',
        goal: 'Build a web scraper'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Agent:', data);
};

ws.send(JSON.stringify({
    type: 'command',
    content: 'Add error handling'
}));
```

### Python API Usage

```python
import asyncio
from xagent.core.agent import XAgent

async def main():
    # Create agent
    agent = XAgent()
    await agent.initialize()
    
    # Start with goal
    await agent.start("Analyze system architecture")
    
    # Send commands
    await agent.send_command("Create documentation")
    
    # Get status
    status = await agent.get_status()
    print(status)
    
    # Stop agent
    await agent.stop()

asyncio.run(main())
```

## Configuration

Key environment variables:

```bash
# API Keys
OPENAI_API_KEY=your_key

# Agent Settings
AGENT_MODE=interactive
MAX_ITERATIONS=100

# Enable Tools
ENABLE_CODE_TOOLS=true
ENABLE_SEARCH_TOOLS=true
SANDBOX_ENABLED=true
```

## Next Steps

- Read [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed design
- See examples in `/examples` directory
- Check API documentation at http://localhost:8000/docs
- Join our Discord for support

## Troubleshooting

**Services not starting**: Check Docker logs with `docker-compose logs -f`

**Connection errors**: Verify Redis and PostgreSQL are running

**API errors**: Check logs in `/logs` directory

For more help, see the full documentation or open an issue on GitHub.
