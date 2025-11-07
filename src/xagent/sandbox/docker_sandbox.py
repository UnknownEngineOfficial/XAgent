"""Docker-based sandboxed code execution for X-Agent."""

from typing import Any, Dict, Optional
import asyncio
import docker
from docker.errors import ContainerError, ImageNotFound, APIError
from datetime import datetime, timezone

from xagent.utils.logging import get_logger

logger = get_logger(__name__)


class DockerSandbox:
    """
    Secure code execution in isolated Docker containers.
    
    Features:
    - Resource limits (CPU, memory)
    - Network isolation
    - Read-only filesystem
    - Timeout enforcement
    - Automatic cleanup
    """
    
    # Language-specific Docker images
    LANGUAGE_IMAGES = {
        "python": "python:3.11-slim",
        "javascript": "node:20-slim",
        "typescript": "node:20-slim",
        "bash": "bash:5.2",
        "go": "golang:1.21-alpine",
    }
    
    def __init__(self, docker_url: Optional[str] = None):
        """
        Initialize Docker sandbox.
        
        Args:
            docker_url: Docker daemon URL (default: unix://var/run/docker.sock)
        """
        try:
            if docker_url:
                self.client = docker.DockerClient(base_url=docker_url)
            else:
                self.client = docker.from_env()
            
            # Verify Docker is accessible
            self.client.ping()
            logger.info("Docker sandbox initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        memory_limit: str = "128m",
        cpu_quota: int = 50000,  # 50% of one CPU
        network_disabled: bool = True,
        working_dir: str = "/workspace",
    ) -> Dict[str, Any]:
        """
        Execute code in a sandboxed Docker container.
        
        Args:
            code: Code to execute
            language: Programming language
            timeout: Maximum execution time in seconds
            memory_limit: Memory limit (e.g., "128m", "1g")
            cpu_quota: CPU quota in microseconds per 100ms period
            network_disabled: Disable network access
            working_dir: Working directory inside container
            
        Returns:
            Dict with execution result:
            {
                "status": "success" | "error" | "timeout",
                "output": stdout output,
                "error": stderr output,
                "exit_code": container exit code,
                "execution_time": time in seconds,
                "timestamp": ISO timestamp
            }
        """
        # Validate language
        if language not in self.LANGUAGE_IMAGES:
            return {
                "status": "error",
                "error": f"Unsupported language: {language}. Supported: {list(self.LANGUAGE_IMAGES.keys())}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        
        image = self.LANGUAGE_IMAGES[language]
        start_time = datetime.now(timezone.utc)
        
        try:
            # Pull image if not available
            await self._ensure_image(image)
            
            # Prepare execution command based on language
            command = self._get_execution_command(language, code)
            
            # Run container in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._run_container,
                image,
                command,
                timeout,
                memory_limit,
                cpu_quota,
                network_disabled,
                working_dir,
            )
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            result["execution_time"] = execution_time
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    
    async def _ensure_image(self, image: str) -> None:
        """Ensure Docker image is available, pull if necessary."""
        try:
            self.client.images.get(image)
        except ImageNotFound:
            logger.info(f"Pulling Docker image: {image}")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.images.pull, image)
    
    def _get_execution_command(self, language: str, code: str) -> list:
        """Get the command to execute code based on language."""
        commands = {
            "python": ["python", "-c", code],
            "javascript": ["node", "-e", code],
            "typescript": ["node", "-e", code],  # TypeScript would need compilation
            "bash": ["bash", "-c", code],
            "go": ["go", "run", "-"],  # Would need code in a file
        }
        return commands.get(language, ["python", "-c", code])
    
    def _run_container(
        self,
        image: str,
        command: list,
        timeout: int,
        memory_limit: str,
        cpu_quota: int,
        network_disabled: bool,
        working_dir: str,
    ) -> Dict[str, Any]:
        """
        Run container synchronously (called in thread pool).
        
        This is a blocking operation that runs in a thread pool executor.
        """
        container = None
        try:
            # Create and start container
            container = self.client.containers.run(
                image=image,
                command=command,
                mem_limit=memory_limit,
                cpu_quota=cpu_quota,
                network_disabled=network_disabled,
                working_dir=working_dir,
                read_only=True,  # Read-only root filesystem
                tmpfs={"/tmp": "rw,noexec,nosuid,size=10m"},  # Small writable tmp
                detach=True,
                remove=False,  # Don't auto-remove so we can get logs
                security_opt=["no-new-privileges"],  # Security hardening
                cap_drop=["ALL"],  # Drop all capabilities
            )
            
            # Wait for container with timeout
            exit_code = container.wait(timeout=timeout)
            
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            
            # Remove container
            container.remove(force=True)
            
            return {
                "status": "success" if exit_code["StatusCode"] == 0 else "error",
                "output": stdout,
                "error": stderr,
                "exit_code": exit_code["StatusCode"],
            }
            
        except ContainerError as e:
            # Container exited with non-zero code
            return {
                "status": "error",
                "output": e.container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace"),
                "error": e.container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace"),
                "exit_code": e.exit_status,
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"Container execution timed out after {timeout}s")
            if container:
                container.stop(timeout=1)
                container.remove(force=True)
            return {
                "status": "timeout",
                "error": f"Execution timed out after {timeout} seconds",
                "exit_code": -1,
            }
            
        except Exception as e:
            logger.error(f"Container execution failed: {e}")
            if container:
                try:
                    container.remove(force=True)
                except:
                    pass
            return {
                "status": "error",
                "error": str(e),
                "exit_code": -1,
            }
    
    def cleanup(self) -> None:
        """Clean up Docker resources."""
        try:
            # Remove dangling containers
            containers = self.client.containers.list(
                filters={"status": "exited", "label": "xagent-sandbox"}
            )
            for container in containers:
                try:
                    container.remove(force=True)
                except:
                    pass
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            self.cleanup()
        except:
            pass
