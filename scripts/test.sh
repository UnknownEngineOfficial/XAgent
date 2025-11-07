#!/usr/bin/env bash
# Test script for X-Agent
# Runs unit tests with coverage reporting

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "X-Agent Test Suite"
echo "================================================"
echo ""

# Check if virtual environment is activated
if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected${NC}"
    echo "Consider running: source .venv/bin/activate"
    echo ""
fi

# Activate virtual environment if it exists and not already activated
if [ -d ".venv" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"

# Run tests with pytest
echo "Running unit tests..."
echo ""

# Run tests with minimal output first
if pytest tests/unit/ --maxfail=1 --disable-warnings -q; then
    echo ""
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Tests failed!${NC}"
    exit 1
fi

# Run coverage analysis
echo "================================================"
echo "Running coverage analysis..."
echo "================================================"
echo ""

# Run coverage without fail-under enforcement
pytest tests/unit/ \
    --cov=src/xagent \
    --cov-report=term \
    --cov-report=xml \
    --cov-report=html \
    --disable-warnings \
    -q \
    --cov-fail-under=0

# Check exit code
TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Coverage analysis complete${NC}"
    echo "Coverage reports generated:"
    echo "  - Terminal output above"
    echo "  - XML report: coverage.xml"
    echo "  - HTML report: htmlcov/index.html"
else
    echo -e "${RED}❌ Coverage analysis failed${NC}"
fi

echo ""
echo "================================================"
echo "Test run complete"
echo "================================================"

exit $TEST_EXIT_CODE
