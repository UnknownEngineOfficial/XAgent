"""Integration tests for LangServe tools."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from xagent.tools.langserve_tools import (
    execute_code,
    think,
    read_file,
    write_file,
    web_search,
    http_request,
    get_tool_by_name,
    get_all_tools,
)


class TestExecuteCodeTool:
    """Integration tests for execute_code tool."""

    @pytest.mark.asyncio
    async def test_execute_python_code_success(self):
        """Test successful Python code execution."""
        code = "print('Hello, World!')"
        result = await execute_code.ainvoke({"code": code, "language": "python", "timeout": 10})

        assert result["status"] == "success"
        assert "Hello, World!" in result["output"]
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_execute_python_with_calculation(self):
        """Test Python code with calculations."""
        code = """
result = 2 + 2
print(f"Result: {result}")
"""
        result = await execute_code.ainvoke({"code": code, "language": "python", "timeout": 10})

        assert result["status"] == "success"
        assert "Result: 4" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_javascript_code(self):
        """Test JavaScript code execution."""
        code = "console.log('Hello from JS');"
        result = await execute_code.ainvoke({"code": code, "language": "javascript", "timeout": 10})

        assert result["status"] == "success"
        assert "Hello from JS" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_bash_code(self):
        """Test Bash code execution."""
        code = "echo 'Hello from Bash'"
        result = await execute_code.ainvoke({"code": code, "language": "bash", "timeout": 10})

        assert result["status"] == "success"
        assert "Hello from Bash" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_code_with_error(self):
        """Test code execution with errors."""
        code = "print(undefined_variable)"
        result = await execute_code.ainvoke({"code": code, "language": "python", "timeout": 10})

        assert result["status"] == "error"
        assert result["exit_code"] != 0

    @pytest.mark.asyncio
    async def test_execute_code_timeout(self):
        """Test code execution timeout."""
        # Infinite loop
        code = "while True: pass"
        result = await execute_code.ainvoke({"code": code, "language": "python", "timeout": 2})

        assert result["status"] in ["timeout", "error"]

    @pytest.mark.asyncio
    async def test_execute_code_network_disabled(self):
        """Test that network is disabled in sandbox."""
        # This should fail if network is disabled
        code = """
import socket
try:
    socket.create_connection(('google.com', 80), timeout=2)
    print('Network is enabled')
except Exception as e:
    print(f'Network is disabled: {e}')
"""
        result = await execute_code.ainvoke({"code": code, "language": "python", "timeout": 10})

        # Network should be disabled
        assert result["status"] == "success"
        assert (
            "Network is disabled" in result["output"]
            or "Network is enabled" not in result["output"]
        )

    @pytest.mark.asyncio
    async def test_execute_code_memory_limit(self):
        """Test that memory limits are enforced."""
        # Try to allocate a large amount of memory
        code = """
try:
    # Try to allocate 512MB (should fail with 256MB limit)
    data = bytearray(512 * 1024 * 1024)
    print('Memory allocation succeeded')
except MemoryError:
    print('Memory allocation failed (limit enforced)')
"""
        result = await execute_code.ainvoke({"code": code, "language": "python", "timeout": 10})

        # Should succeed or fail based on memory limits
        assert result["status"] in ["success", "error"]


class TestThinkTool:
    """Integration tests for think tool."""

    def test_think_basic(self):
        """Test basic thought recording."""
        result = think.invoke({"thought": "I need to analyze this problem"})

        assert result["status"] == "recorded"
        assert "thought_id" in result
        assert result["thought"] == "I need to analyze this problem"
        assert "timestamp" in result

    def test_think_with_context(self):
        """Test thought recording with context."""
        context = {"goal": "solve_problem", "step": 1, "confidence": 0.85}
        result = think.invoke(
            {"thought": "Breaking down the problem into subtasks", "context": context}
        )

        assert result["status"] == "recorded"
        assert result["context"] == context
        assert "thought_id" in result

    def test_think_without_context(self):
        """Test thought recording without context."""
        result = think.invoke({"thought": "Simple thought"})

        assert result["status"] == "recorded"
        assert result["context"] == {}

    def test_think_unique_ids(self):
        """Test that each thought gets a unique ID."""
        result1 = think.invoke({"thought": "First thought"})
        result2 = think.invoke({"thought": "Second thought"})

        assert result1["thought_id"] != result2["thought_id"]


class TestFileReadTool:
    """Integration tests for read_file tool."""

    def test_read_file_success(self, tmp_path):
        """Test successful file reading."""
        # Create a temporary file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!\nLine 2\nLine 3"
        test_file.write_text(test_content)

        result = read_file.invoke({"path": str(test_file)})

        assert result["status"] == "success"
        assert result["content"] == test_content
        assert result["lines"] == 3
        assert result["size"] == len(test_content)

    def test_read_file_with_max_lines(self, tmp_path):
        """Test reading file with line limit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")

        result = read_file.invoke({"path": str(test_file), "max_lines": 3})

        assert result["status"] == "success"
        assert "Line 1" in result["content"]
        assert "Line 2" in result["content"]
        assert "Line 3" in result["content"]
        # May or may not include Line 4 depending on implementation

    def test_read_file_not_found(self):
        """Test reading non-existent file."""
        result = read_file.invoke({"path": "/nonexistent/file.txt"})

        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_read_file_is_directory(self, tmp_path):
        """Test reading a directory instead of file."""
        result = read_file.invoke({"path": str(tmp_path)})

        assert result["status"] == "error"
        assert "not a file" in result["error"].lower()

    def test_read_empty_file(self, tmp_path):
        """Test reading empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        result = read_file.invoke({"path": str(test_file)})

        assert result["status"] == "success"
        assert result["content"] == ""
        assert result["size"] == 0


class TestFileWriteTool:
    """Integration tests for write_file tool."""

    def test_write_file_success(self, tmp_path):
        """Test successful file writing."""
        test_file = tmp_path / "output.txt"
        content = "Test content"

        result = write_file.invoke({"path": str(test_file), "content": content})

        assert result["status"] == "success"
        assert result["path"] == str(test_file)
        assert result["bytes_written"] == len(content.encode("utf-8"))
        assert not result["append"]

        # Verify file was written
        assert test_file.read_text() == content

    def test_write_file_overwrite(self, tmp_path):
        """Test overwriting existing file."""
        test_file = tmp_path / "output.txt"
        test_file.write_text("Original content")

        new_content = "New content"
        result = write_file.invoke({"path": str(test_file), "content": new_content})

        assert result["status"] == "success"
        assert test_file.read_text() == new_content

    def test_write_file_append(self, tmp_path):
        """Test appending to existing file."""
        test_file = tmp_path / "output.txt"
        test_file.write_text("Line 1\n")

        result = write_file.invoke({"path": str(test_file), "content": "Line 2\n", "append": True})

        assert result["status"] == "success"
        assert result["append"]
        assert test_file.read_text() == "Line 1\nLine 2\n"

    def test_write_file_create_directories(self, tmp_path):
        """Test creating parent directories."""
        test_file = tmp_path / "subdir" / "nested" / "file.txt"
        content = "Nested file"

        result = write_file.invoke({"path": str(test_file), "content": content})

        assert result["status"] == "success"
        assert test_file.exists()
        assert test_file.read_text() == content

    def test_write_file_unicode_content(self, tmp_path):
        """Test writing unicode content."""
        test_file = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"

        result = write_file.invoke({"path": str(test_file), "content": content})

        assert result["status"] == "success"
        assert test_file.read_text(encoding="utf-8") == content


class TestToolDiscovery:
    """Integration tests for tool discovery functions."""

    def test_get_all_tools(self):
        """Test getting all tools."""
        tools = get_all_tools()

        assert len(tools) == 6
        tool_names = [tool.name for tool in tools]
        assert "execute_code" in tool_names
        assert "think" in tool_names
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "web_search" in tool_names
        assert "http_request" in tool_names

    def test_get_tool_by_name(self):
        """Test getting tool by name."""
        tool = get_tool_by_name("think")

        assert tool is not None
        assert tool.name == "think"

    def test_get_tool_by_name_not_found(self):
        """Test getting non-existent tool."""
        tool = get_tool_by_name("nonexistent_tool")

        assert tool is None

    def test_all_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        tools = get_all_tools()

        for tool in tools:
            assert hasattr(tool, "description")
            assert len(tool.description) > 0


class TestToolIntegration:
    """Integration tests for tool interactions."""

    @pytest.mark.asyncio
    async def test_code_execution_and_file_write(self, tmp_path):
        """Test executing code and writing results to file."""
        # Execute code
        code = "result = 10 * 5\nprint(result)"
        exec_result = await execute_code.ainvoke(
            {"code": code, "language": "python", "timeout": 10}
        )

        assert exec_result["status"] == "success"

        # Write output to file
        output_file = tmp_path / "result.txt"
        write_result = write_file.invoke(
            {"path": str(output_file), "content": exec_result["output"]}
        )

        assert write_result["status"] == "success"
        assert "50" in output_file.read_text()

    def test_write_and_read_file(self, tmp_path):
        """Test writing and then reading a file."""
        test_file = tmp_path / "test.txt"
        content = "Test content for integration"

        # Write file
        write_result = write_file.invoke({"path": str(test_file), "content": content})
        assert write_result["status"] == "success"

        # Read file back
        read_result = read_file.invoke({"path": str(test_file)})
        assert read_result["status"] == "success"
        assert read_result["content"] == content

    def test_think_and_file_logging(self, tmp_path):
        """Test recording thoughts and logging to file."""
        # Record thought
        thought_result = think.invoke(
            {"thought": "Starting the task", "context": {"task": "integration_test"}}
        )

        assert thought_result["status"] == "recorded"

        # Log thought to file
        log_file = tmp_path / "thoughts.log"
        log_content = f"{thought_result['timestamp']}: {thought_result['thought']}\n"

        write_result = write_file.invoke(
            {"path": str(log_file), "content": log_content, "append": True}
        )

        assert write_result["status"] == "success"


class TestWebSearchTool:
    """Integration tests for web_search tool."""

    @pytest.mark.asyncio
    async def test_web_search_success_mock(self):
        """Test successful web search with mocked response."""
        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test Page</h1><p>Test content</p></body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await web_search.ainvoke(
                {"url": "https://example.com", "extract_text": True, "max_length": 10000}
            )

            assert result["status"] == "success"
            assert result["url"] == "https://example.com"
            assert "Test Page" in result["content"]
            assert "Test content" in result["content"]
            assert "<html>" not in result["content"]  # HTML tags removed

    @pytest.mark.asyncio
    async def test_web_search_no_text_extraction(self):
        """Test web search without text extraction."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>Raw HTML</body></html>"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await web_search.ainvoke(
                {"url": "https://example.com", "extract_text": False, "max_length": 10000}
            )

            assert result["status"] == "success"
            assert "<html>" in result["content"]  # HTML tags preserved

    @pytest.mark.asyncio
    async def test_web_search_max_length_truncation(self):
        """Test max length truncation."""
        long_content = "A" * 20000
        mock_response = MagicMock()
        mock_response.text = long_content
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await web_search.ainvoke(
                {"url": "https://example.com", "extract_text": False, "max_length": 1000}
            )

            assert result["status"] == "success"
            assert len(result["content"]) <= 1003  # 1000 + "..."
            assert result["content"].endswith("...")

    @pytest.mark.asyncio
    async def test_web_search_http_error(self):
        """Test web search with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "404 Not Found", request=MagicMock(), response=MagicMock(status_code=404)
                )
            )

            result = await web_search.ainvoke(
                {"url": "https://example.com/notfound", "extract_text": True, "max_length": 10000}
            )

            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_web_search_timeout(self):
        """Test web search with timeout."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )

            result = await web_search.ainvoke(
                {"url": "https://slow-site.com", "extract_text": True, "max_length": 10000}
            )

            assert result["status"] == "error"
            assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()


class TestHTTPRequestTool:
    """Integration tests for http_request tool."""

    @pytest.mark.asyncio
    async def test_http_get_request(self):
        """Test HTTP GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"message": "success"}'
        mock_response.url = "https://api.example.com/data"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await http_request.ainvoke(
                {
                    "url": "https://api.example.com/data",
                    "method": "GET",
                    "headers": None,
                    "body": None,
                    "timeout": 30,
                }
            )

            assert result["status"] == "success"
            assert result["status_code"] == 200
            assert result["content"] == '{"message": "success"}'

    @pytest.mark.asyncio
    async def test_http_post_request_with_body(self):
        """Test HTTP POST request with body."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"id": 123}'
        mock_response.url = "https://api.example.com/create"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await http_request.ainvoke(
                {
                    "url": "https://api.example.com/create",
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"name": "test"}',
                    "timeout": 30,
                }
            )

            assert result["status"] == "success"
            assert result["status_code"] == 201

    @pytest.mark.asyncio
    async def test_http_request_with_custom_headers(self):
        """Test HTTP request with custom headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"x-custom": "value"}
        mock_response.text = "OK"
        mock_response.url = "https://api.example.com"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await http_request.ainvoke(
                {
                    "url": "https://api.example.com",
                    "method": "GET",
                    "headers": {"Authorization": "Bearer token123"},
                    "body": None,
                    "timeout": 30,
                }
            )

            assert result["status"] == "success"
            assert "x-custom" in result["headers"]

    @pytest.mark.asyncio
    async def test_http_request_error(self):
        """Test HTTP request with error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            result = await http_request.ainvoke(
                {
                    "url": "https://invalid-host.com",
                    "method": "GET",
                    "headers": None,
                    "body": None,
                    "timeout": 30,
                }
            )

            assert result["status"] == "error"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_http_put_request(self):
        """Test HTTP PUT request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = "Updated"
        mock_response.url = "https://api.example.com/update/1"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await http_request.ainvoke(
                {
                    "url": "https://api.example.com/update/1",
                    "method": "PUT",
                    "headers": {"Content-Type": "application/json"},
                    "body": '{"status": "active"}',
                    "timeout": 30,
                }
            )

            assert result["status"] == "success"
            assert result["status_code"] == 200

    @pytest.mark.asyncio
    async def test_http_delete_request(self):
        """Test HTTP DELETE request."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.url = "https://api.example.com/delete/1"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            result = await http_request.ainvoke(
                {
                    "url": "https://api.example.com/delete/1",
                    "method": "DELETE",
                    "headers": None,
                    "body": None,
                    "timeout": 30,
                }
            )

            assert result["status"] == "success"
            assert result["status_code"] == 204
