"""
Example: Tool Server Usage

This example demonstrates:
1. Creating custom tools
2. Registering tools with the tool server
3. Executing tool calls
4. Error handling
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xagent.tools.tool_server import Tool, ToolServer


class CalculatorTool(Tool):
    """Custom calculator tool."""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform mathematical calculations"
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculation."""
        operation = parameters.get("operation", "add")
        a = parameters.get("a", 0)
        b = parameters.get("b", 0)
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero")
            result = a / b
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": result,
        }


class DataAnalysisTool(Tool):
    """Custom data analysis tool."""
    
    @property
    def name(self) -> str:
        return "data_analysis"
    
    @property
    def description(self) -> str:
        return "Analyze data and generate insights"
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data analysis."""
        data = parameters.get("data", [])
        
        if not data:
            return {
                "count": 0,
                "mean": 0,
                "min": 0,
                "max": 0,
            }
        
        return {
            "count": len(data),
            "mean": sum(data) / len(data),
            "min": min(data),
            "max": max(data),
            "sum": sum(data),
        }


async def main():
    """Demonstrate tool server usage."""
    print("=" * 60)
    print("X-Agent Tool Server Example")
    print("=" * 60)
    print()
    
    # Create tool server
    print("1. Creating tool server...")
    server = ToolServer()
    print("   ✓ Tool server created")
    print()
    
    # Register custom tools
    print("2. Registering custom tools...")
    server.register_tool(CalculatorTool())
    server.register_tool(DataAnalysisTool())
    print("   ✓ Tools registered")
    print()
    
    # List available tools
    print("3. Available tools:")
    tools = server.list_tools()
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description']}")
    print()
    
    # Execute calculator tool
    print("4. Executing calculator tool...")
    result = await server.call_tool(
        "calculator",
        {"operation": "add", "a": 10, "b": 5}
    )
    print(f"   10 + 5 = {result['result']['result']}")
    
    result = await server.call_tool(
        "calculator",
        {"operation": "multiply", "a": 7, "b": 6}
    )
    print(f"   7 × 6 = {result['result']['result']}")
    print()
    
    # Execute data analysis tool
    print("5. Executing data analysis tool...")
    data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    result = await server.call_tool(
        "data_analysis",
        {"data": data}
    )
    
    analysis = result['result']
    print(f"   Data: {data}")
    print(f"   Count: {analysis['count']}")
    print(f"   Mean: {analysis['mean']}")
    print(f"   Min: {analysis['min']}")
    print(f"   Max: {analysis['max']}")
    print(f"   Sum: {analysis['sum']}")
    print()
    
    # Error handling
    print("6. Error handling...")
    result = await server.call_tool(
        "calculator",
        {"operation": "divide", "a": 10, "b": 0}
    )
    
    if result['success']:
        print(f"   Result: {result['result']}")
    else:
        print(f"   ✗ Error: {result['error']}")
    print()
    
    # Unknown tool
    result = await server.call_tool("unknown_tool", {})
    if not result['success']:
        print(f"   ✗ {result['error']}")
    print()
    
    print("=" * 60)
    print("Tool server example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
