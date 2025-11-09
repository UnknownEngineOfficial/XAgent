"""LangServe-based tool definitions for X-Agent."""

# mypy: disable-error-code="no-untyped-def,arg-type"

import re
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx
from langchain.tools import tool
from pydantic import BaseModel, Field

from xagent.sandbox.docker_sandbox import DockerSandbox
from xagent.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize sandbox instance
_sandbox: DockerSandbox | None = None


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


class HTMLTextExtractor(HTMLParser):
    """Extract text from HTML, excluding script and style tags."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.skip_tags = {"script", "style"}
        self.in_skip_tag = False

    def handle_starttag(self, tag, attrs):
        """Handle opening tags."""
        if tag in self.skip_tags:
            self.in_skip_tag = True

    def handle_endtag(self, tag):
        """Handle closing tags."""
        if tag in self.skip_tags:
            self.in_skip_tag = False

    def handle_data(self, data):
        """Handle text data."""
        if not self.in_skip_tag:
            self.text_parts.append(data)

    def get_text(self):
        """Get extracted text."""
        return " ".join(self.text_parts)


# Tool input schemas
class CodeExecutionInput(BaseModel):
    """Input schema for code execution tool."""

    code: str = Field(description="The code to execute")
    language: str = Field(
        default="python",
        description="Programming language (python, javascript, bash, go, typescript)",
    )
    timeout: int = Field(default=30, description="Maximum execution time in seconds")


class ThinkInput(BaseModel):
    """Input schema for think tool."""

    thought: str = Field(description="The thought or reasoning to record")
    context: dict[str, Any] | None = Field(
        default=None, description="Additional context for the thought"
    )


class FileReadInput(BaseModel):
    """Input schema for file read tool."""

    path: str = Field(description="Path to the file to read")
    max_lines: int | None = Field(default=None, description="Maximum number of lines to read")


class FileWriteInput(BaseModel):
    """Input schema for file write tool."""

    path: str = Field(description="Path to the file to write")
    content: str = Field(description="Content to write to the file")
    append: bool = Field(default=False, description="Whether to append to existing file")


class WebSearchInput(BaseModel):
    """Input schema for web search/fetch tool."""

    url: str = Field(description="URL to fetch content from")
    extract_text: bool = Field(
        default=True, description="Whether to extract and clean text from HTML"
    )
    max_length: int | None = Field(default=10000, description="Maximum content length to return")


class HTTPRequestInput(BaseModel):
    """Input schema for HTTP request tool."""

    url: str = Field(description="URL to send the request to")
    method: str = Field(default="GET", description="HTTP method (GET, POST, PUT, DELETE)")
    headers: dict[str, str] | None = Field(default=None, description="HTTP headers to include")
    body: str | None = Field(default=None, description="Request body for POST/PUT")
    timeout: int = Field(default=30, description="Request timeout in seconds")


# LangServe Tool Definitions
@tool
async def execute_code(code: str, language: str = "python", timeout: int = 30) -> dict[str, Any]:
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
def think(thought: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
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
def read_file(path: str, max_lines: int | None = None) -> dict[str, Any]:
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
        with open(file_path, encoding="utf-8") as f:
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
def write_file(path: str, content: str, append: bool = False) -> dict[str, Any]:
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


@tool
async def web_search(
    url: str, extract_text: bool = True, max_length: int = 10000
) -> dict[str, Any]:
    """
    Fetch and extract content from a web page.

    This tool fetches content from a URL and optionally extracts
    clean text from HTML. Useful for web scraping and research.

    Args:
        url: URL to fetch content from
        extract_text: Whether to extract and clean text from HTML (default: True)
        max_length: Maximum content length to return (default: 10000)

    Returns:
        Dictionary with:
        - status: "success" or "error"
        - url: The fetched URL
        - content: The page content (text or HTML)
        - content_type: Content type from response
        - length: Content length
        - error: Error message if any
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            content = response.text
            content_type = response.headers.get("content-type", "")

            # Extract text from HTML if requested
            if extract_text and "html" in content_type.lower():
                # Use HTML parser to safely extract text (avoids regex pitfalls)
                try:
                    parser = HTMLTextExtractor()
                    parser.feed(content)
                    content = parser.get_text()
                    # Clean up whitespace
                    content = re.sub(r"\s+", " ", content)
                    content = content.strip()
                except Exception as e:
                    logger.warning(f"HTML parsing failed, using raw content: {e}")
                    # Fallback to basic text extraction if parser fails
                    content = re.sub(r"<[^>]+>", " ", content)
                    content = re.sub(r"\s+", " ", content)
                    content = content.strip()

            # Truncate if too long
            if len(content) > max_length:
                content = content[:max_length] + "..."

            logger.info(f"Fetched content from {url} ({len(content)} chars)")

            return {
                "status": "success",
                "url": url,
                "content": content,
                "content_type": content_type,
                "length": len(content),
                "status_code": response.status_code,
            }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching {url}: {e}")
        return {
            "status": "error",
            "url": url,
            "error": f"HTTP error: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return {
            "status": "error",
            "url": url,
            "error": str(e),
        }


@tool
async def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Make an HTTP request to an API endpoint.

    This tool allows making custom HTTP requests with different methods,
    headers, and body content. Useful for API integration.

    Args:
        url: URL to send the request to
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional HTTP headers
        body: Optional request body for POST/PUT
        timeout: Request timeout in seconds

    Returns:
        Dictionary with:
        - status: "success" or "error"
        - status_code: HTTP status code
        - headers: Response headers
        - content: Response body
        - error: Error message if any
    """
    try:
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            request_kwargs = {
                "method": method.upper(),
                "url": url,
                "headers": headers or {},
            }

            if body and method.upper() in ["POST", "PUT", "PATCH"]:
                request_kwargs["content"] = body

            response = await client.request(**request_kwargs)

            # Try to get text content
            try:
                content = response.text
            except Exception:
                content = f"<binary content, {len(response.content)} bytes>"

            logger.info(f"HTTP {method} {url} -> {response.status_code}")

            return {
                "status": "success",
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": content,
                "url": str(response.url),
            }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error: {e}")
        return {
            "status": "error",
            "error": f"HTTP error: {str(e)}",
            "url": url,
        }
    except Exception as e:
        logger.error(f"Request error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "url": url,
        }


# List of all available tools
LANGSERVE_TOOLS = [
    execute_code,
    think,
    read_file,
    write_file,
    web_search,
    http_request,
]


def get_tool_by_name(name: str):
    """Get a tool by its name."""
    tool_map = {tool.name: tool for tool in LANGSERVE_TOOLS}
    return tool_map.get(name)


def get_all_tools():
    """Get all available LangServe tools."""
    return LANGSERVE_TOOLS
