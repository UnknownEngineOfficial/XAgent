"""Unit tests for Docker sandbox."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from xagent.sandbox.docker_sandbox import DockerSandbox


class TestDockerSandbox:
    """Test DockerSandbox implementation."""
    
    @pytest.fixture
    def mock_docker_client(self):
        """Create a mock Docker client."""
        with patch("xagent.sandbox.docker_sandbox.docker") as mock_docker:
            client = MagicMock()
            client.ping.return_value = True
            mock_docker.from_env.return_value = client
            yield client
    
    def test_init_success(self, mock_docker_client):
        """Test successful initialization."""
        sandbox = DockerSandbox()
        assert sandbox.client is not None
        mock_docker_client.ping.assert_called_once()
    
    def test_init_with_custom_url(self):
        """Test initialization with custom Docker URL."""
        with patch("xagent.sandbox.docker_sandbox.docker") as mock_docker:
            client = MagicMock()
            client.ping.return_value = True
            mock_docker.DockerClient.return_value = client
            
            sandbox = DockerSandbox(docker_url="tcp://localhost:2375")
            assert sandbox.client is not None
            mock_docker.DockerClient.assert_called_once_with(base_url="tcp://localhost:2375")
    
    def test_language_images(self):
        """Test language image mappings."""
        assert "python" in DockerSandbox.LANGUAGE_IMAGES
        assert "javascript" in DockerSandbox.LANGUAGE_IMAGES
        assert "bash" in DockerSandbox.LANGUAGE_IMAGES
    
    @pytest.mark.asyncio
    async def test_execute_unsupported_language(self, mock_docker_client):
        """Test execution with unsupported language."""
        sandbox = DockerSandbox()
        result = await sandbox.execute("print('test')", language="unsupported")
        
        assert result["status"] == "error"
        assert "Unsupported language" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_docker_client):
        """Test successful code execution."""
        # Mock container
        container = MagicMock()
        container.wait.return_value = {"StatusCode": 0}
        container.logs.side_effect = [
            b"Hello, World!\n",  # stdout
            b"",  # stderr
        ]
        
        mock_docker_client.containers.run.return_value = container
        mock_docker_client.images.get.return_value = MagicMock()  # Image exists
        
        sandbox = DockerSandbox()
        result = await sandbox.execute("print('Hello, World!')", language="python")
        
        assert result["status"] == "success"
        assert "Hello, World!" in result["output"]
        assert result["exit_code"] == 0
        assert "execution_time" in result
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_execute_error(self, mock_docker_client):
        """Test code execution with error."""
        container = MagicMock()
        container.wait.return_value = {"StatusCode": 1}
        container.logs.side_effect = [
            b"",  # stdout
            b"SyntaxError: invalid syntax\n",  # stderr
        ]
        
        mock_docker_client.containers.run.return_value = container
        mock_docker_client.images.get.return_value = MagicMock()
        
        sandbox = DockerSandbox()
        result = await sandbox.execute("invalid python", language="python")
        
        assert result["status"] == "error"
        assert result["exit_code"] == 1
        assert "SyntaxError" in result["error"]
    
    def test_get_execution_command_python(self, mock_docker_client):
        """Test Python execution command."""
        sandbox = DockerSandbox()
        cmd = sandbox._get_execution_command("python", "print('test')")
        assert cmd == ["python", "-c", "print('test')"]
    
    def test_get_execution_command_javascript(self, mock_docker_client):
        """Test JavaScript execution command."""
        sandbox = DockerSandbox()
        cmd = sandbox._get_execution_command("javascript", "console.log('test')")
        assert cmd == ["node", "-e", "console.log('test')"]
    
    def test_get_execution_command_bash(self, mock_docker_client):
        """Test Bash execution command."""
        sandbox = DockerSandbox()
        cmd = sandbox._get_execution_command("bash", "echo test")
        assert cmd == ["bash", "-c", "echo test"]
    
    def test_cleanup(self, mock_docker_client):
        """Test cleanup of dangling containers."""
        container1 = MagicMock()
        container2 = MagicMock()
        mock_docker_client.containers.list.return_value = [container1, container2]
        
        sandbox = DockerSandbox()
        sandbox.cleanup()
        
        mock_docker_client.containers.list.assert_called_once()
        container1.remove.assert_called_once_with(force=True)
        container2.remove.assert_called_once_with(force=True)
