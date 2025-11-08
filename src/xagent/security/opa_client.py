"""
OPA (Open Policy Agent) Client for X-Agent

This module provides integration with Open Policy Agent for policy-based
access control and security enforcement.
"""

from typing import Any

import httpx
from structlog import get_logger

from xagent.config import Settings

logger = get_logger(__name__)


class OPAClient:
    """Client for interacting with Open Policy Agent server."""

    def __init__(self, settings: Settings):
        """
        Initialize OPA client.

        Args:
            settings: Application settings containing OPA configuration
        """
        self.opa_url = settings.opa_url
        self.enabled = settings.opa_enabled
        self.timeout = settings.opa_timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def check_policy(
        self,
        policy_path: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Check a policy against input data.

        Args:
            policy_path: Policy path (e.g., "xagent/base/allow")
            input_data: Input data for policy evaluation

        Returns:
            Policy evaluation result
        """
        if not self.enabled:
            logger.debug("OPA is disabled, allowing by default")
            return {"result": True, "allowed": True}

        try:
            url = f"{self.opa_url}/v1/data/{policy_path}"
            payload = {"input": input_data}

            logger.debug(
                "Checking OPA policy",
                policy_path=policy_path,
                url=url,
            )

            response = await self._client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()
            logger.debug(
                "OPA policy check completed",
                policy_path=policy_path,
                result=result.get("result"),
            )

            return result

        except httpx.HTTPError as e:
            logger.error(
                "OPA policy check failed",
                policy_path=policy_path,
                error=str(e),
            )
            # Fail closed - deny access on error
            return {
                "result": False,
                "allowed": False,
                "error": str(e),
            }

    async def check_base_policy(self, input_data: dict[str, Any]) -> bool:
        """
        Check base policy (authentication and rate limiting).

        Args:
            input_data: Request and user information

        Returns:
            True if allowed, False otherwise
        """
        result = await self.check_policy("xagent/base/allow", input_data)
        return result.get("result", False)

    async def check_api_access(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Check API access policy.

        Args:
            input_data: Request and user information

        Returns:
            Dictionary with 'allowed' boolean and optional 'deny_reasons' list
        """
        # Check if access is allowed
        allow_result = await self.check_policy("xagent/api/allow_api_access", input_data)
        allowed = allow_result.get("result", False)

        # Check for deny reasons
        deny_result = await self.check_policy("xagent/api/deny_api_access", input_data)
        deny_reasons = deny_result.get("result", [])

        return {
            "allowed": allowed and not deny_reasons,
            "deny_reasons": (
                deny_reasons
                if isinstance(deny_reasons, list)
                else [deny_reasons] if deny_reasons else []
            ),
        }

    async def check_tool_execution(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Check tool execution policy.

        Args:
            input_data: Tool execution request information

        Returns:
            Dictionary with 'allowed' boolean and optional 'deny_reasons' list
        """
        # Check if execution is allowed
        allow_result = await self.check_policy("xagent/tools/allow_tool_execution", input_data)
        allowed = allow_result.get("result", False)

        # Check for deny reasons
        deny_result = await self.check_policy("xagent/tools/deny_tool_execution", input_data)
        deny_reasons = deny_result.get("result", [])

        return {
            "allowed": allowed and not deny_reasons,
            "deny_reasons": (
                deny_reasons
                if isinstance(deny_reasons, list)
                else [deny_reasons] if deny_reasons else []
            ),
        }

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Singleton instance
_opa_client: OPAClient | None = None


def get_opa_client(settings: Settings | None = None) -> OPAClient:
    """
    Get or create OPA client singleton.

    Args:
        settings: Application settings (required on first call)

    Returns:
        OPA client instance
    """
    global _opa_client

    if _opa_client is None:
        if settings is None:
            from xagent.config import get_settings

            settings = get_settings()
        _opa_client = OPAClient(settings)

    return _opa_client
