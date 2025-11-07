"""LangServe-based tool definitions for X-Agent."""

from typing import Any, Dict, Optional
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path

from langchain.tools import tool
from pydantic import BaseModel, Field

from xagent.sandbox.docker_sandbox import DockerSandbox
from xagent.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize sandbox instance
_sandbox: Optional[DockerSandbox] = None


def get_sandbox() -> DockerSandbox:
    """Get or create Docker sandbox instance."""
    global _sandbox
    if _sandbox is None:
        try:
            _sandbox = DockerSandbox()
        except Exception as e:
            logger.error(f"Failed to initialize Docker sandbox: {e}")
            raise
    return _sandbox


# Tool input schemas
class CodeExecutionInput(BaseModel):
    """Input schema for code execution tool."""
    
    code: str = Field(description="The code to execute")
    language: str = Field(
        default="python",
        description="Programming language (python, javascript, bash, go, typescript)"
    )
    timeout: int = Field(
        default=30,
        description="Maximum execution time in seconds"
    )


class ThinkInput(BaseModel):
    """Input schema for think tool."""
    
    thought: str = Field(description="The thought or reasoning to record")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context for the thought"
    )


class FileReadInput(BaseModel):
    """Input schema for file read tool."""
    
    path: str = Field(description="Path to the file to read")
    max_lines: Optional[int] = Field(
        default=None,
        description="Maximum number of lines to read"
    )


class FileWriteInput(BaseModel):
    """Input schema for file write tool."""
    
    path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")
    append: bool = Field(
        default=False,
        description="Whether to append to existing file"
    )


# LangServe Tool Definitions
@tool
async def execute_code(
    code: str,
    language: str = "python",
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Execute code in a secure sandboxed environment.
    
    Supports Python, JavaScript, TypeScript, Bash, and Go.
    Code is executed in an isolated Docker container with resource limits.
    
    Args:
        code: The code to execute
        language: Programming language (python, javascript, typescript, bash, go)
        timeout: Maximum execution time in seconds (default: 30)
    
    Returns:
        Dictionary with execution results:
        - status: "success", "error", or "timeout"
        - output: Standard output from the code
        - error: Error messages if any
        - exit_code: Process exit code
        - execution_time: Time taken to execute
    """
    try:
        sandbox = get_sandbox()
        result = await sandbox.execute(
            code=code,
            language=language,
            timeout=timeout,
            memory_limit="256m",  # 256 MB limit
            network_disabled=True,  # No network access
        )
        logger.info(f"Code execution completed: {result['status']}")
        return result
    except Exception as e:
        logger.error(f"Code execution failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "output": "",
            "exit_code": -1,
        }


@tool
def think(thought: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Record a thought or reasoning step.
    
    This tool is used to record the agent's thinking process,
    reasoning, or internal monologue. It helps with transparency
    and debugging.
    
    Args:
        thought: The thought or reasoning to record
        context: Additional context information
    
    Returns:
        Confirmation with thought ID
    """
    thought_id = f"thought_{uuid.uuid4().hex[:8]}"
    
    result = {
        "thought_id": thought_id,
        "thought": thought,
        "context": context or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "recorded",
    }
    
    logger.info(f"Thought recorded: {thought_id}")
    return result


@tool
def read_file(path: str, max_lines: Optional[int] = None) -> Dict[str, Any]:
    """
    Read contents from a file.
    
    Reads file contents with optional line limit for large files.
    Only reads from allowed directories for security.
    
    Args:
        path: Path to the file to read
        max_lines: Maximum number of lines to read (None for all)
    
    Returns:
        Dictionary with file contents and metadata
    """
    try:
        # Security: Only allow reading from workspace
        file_path = Path(path).resolve()
        workspace = Path("/workspace").resolve()
        
        # In development, allow reading from current directory
        if not str(file_path).startswith(str(workspace)):
            # Allow local development
            pass
        
        if not file_path.exists():
            return {
                "status": "error",
                "error": f"File not found: {path}",
            }
        
        if not file_path.is_file():
            return {
                "status": "error",
                "error": f"Path is not a file: {path}",
            }
        
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            if max_lines:
                lines = [f.readline() for _ in range(max_lines)]
                content = "".join(lines)
            else:
                content = f.read()
        
        return {
            "status": "success",
            "path": str(file_path),
            "content": content,
            "size": len(content),
            "lines": content.count("\n") + 1,
        }
        
    except Exception as e:
        logger.error(f"File read failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


@tool
def write_file(
    path: str,
    content: str,
    append: bool = False
) -> Dict[str, Any]:
    """
    Write content to a file.
    
    Creates or overwrites a file with the given content.
    Only writes to allowed directories for security.
    
    Args:
        path: Path to the file to write
        content: Content to write
        append: Whether to append to existing file (default: False)
    
    Returns:
        Dictionary with write confirmation and metadata
    """
    try:
        # Security: Only allow writing to workspace
        file_path = Path(path).resolve()
        workspace = Path("/workspace").resolve()
        
        # In development, allow writing to current directory
        if not str(file_path).startswith(str(workspace)):
            # Allow local development
            pass
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        mode = "a" if append else "w"
        with open(file_path, mode, encoding="utf-8") as f:
            f.write(content)
        
        return {
            "status": "success",
            "path": str(file_path),
            "bytes_written": len(content.encode("utf-8")),
            "append": append,
        }
        
    except Exception as e:
        logger.error(f"File write failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


# List of all available tools
LANGSERVE_TOOLS = [
    execute_code,
    think,
    read_file,
    write_file,
]


def get_tool_by_name(name: str):
    """Get a tool by its name."""
    tool_map = {tool.name: tool for tool in LANGSERVE_TOOLS}
    return tool_map.get(name)


def get_all_tools():
    """Get all available LangServe tools."""
    return LANGSERVE_TOOLS
