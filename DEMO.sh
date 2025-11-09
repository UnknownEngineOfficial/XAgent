#!/bin/bash
# X-Agent Quick Demo Script
# Demonstrates X-Agent capabilities in your terminal

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    X-Agent Quick Demo                          ║"
echo "║                Autonomous AI Agent in Action                   ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if we're in the right directory
if [ ! -f "src/xagent/__init__.py" ]; then
    echo "❌ Error: Please run this script from the X-Agent root directory"
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="$(pwd)/src:$PYTHONPATH"

echo "🔍 Checking environment..."
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo "✓ Python: $PYTHON_VERSION"

# Check if dependencies are installed
if python3 -c "import rich" 2>/dev/null; then
    echo "✓ Dependencies: Installed"
else
    echo "❌ Dependencies not installed"
    echo ""
    echo "Installing dependencies..."
    pip install -q -r requirements.txt
    echo "✓ Dependencies installed"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Starting Standalone Demo (no external services required)..."
echo ""
echo "This demo will:"
echo "  • Create a hierarchical goal structure (1 main + 5 sub-goals)"
echo "  • Track goal progression in real-time"
echo "  • Display beautiful formatted output"
echo "  • Complete all goals with 100% success rate"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Run the standalone demo
python3 examples/standalone_results_demo.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ Demo complete! What's next?"
echo ""
echo "1. Try the full demo with Docker:"
echo "   $ docker-compose up -d"
echo "   $ python examples/automated_demo.py"
echo ""
echo "2. Read the quick start guide:"
echo "   $ cat QUICK_RESULTS.md"
echo ""
echo "3. Explore the API:"
echo "   $ python -m xagent.api.rest"
echo "   $ curl http://localhost:8000/health"
echo ""
echo "4. Run the test suite:"
echo "   $ make test"
echo ""
echo "5. Try the interactive CLI:"
echo "   $ python -m xagent.cli.main interactive"
echo ""
echo "📚 Documentation: docs/"
echo "🐛 Issues: https://github.com/UnknownEngineOfficial/X-Agent/issues"
echo "⭐ Star us: https://github.com/UnknownEngineOfficial/X-Agent"
echo ""
