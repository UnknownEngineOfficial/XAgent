"""Tests for OPA client integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from xagent.security.opa_client import OPAClient, get_opa_client
from xagent.config import Settings


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        opa_url="http://localhost:8181",
        opa_enabled=True,
        opa_timeout=5,
    )


@pytest.fixture
def disabled_settings():
    """Create test settings with OPA disabled."""
    return Settings(
        opa_url="http://localhost:8181",
        opa_enabled=False,
        opa_timeout=5,
    )


@pytest.fixture
def opa_client(settings):
    """Create OPA client."""
    return OPAClient(settings)


@pytest.mark.asyncio
async def test_opa_client_initialization(settings):
    """Test OPA client initialization."""
    client = OPAClient(settings)
    assert client.opa_url == "http://localhost:8181"
    assert client.enabled is True
    assert client.timeout == 5
    await client.close()


@pytest.mark.asyncio
async def test_opa_client_disabled(disabled_settings):
    """Test OPA client with disabled OPA."""
    client = OPAClient(disabled_settings)
    
    result = await client.check_policy("xagent/base/allow", {})
    
    assert result["result"] is True
    assert result["allowed"] is True
    await client.close()


@pytest.mark.asyncio
async def test_check_policy_success():
    """Test successful policy check."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client = OPAClient(settings)
    
    # Mock the HTTP client
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": True}
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await client.check_policy(
            "xagent/base/allow",
            {"user": {"authenticated": True}}
        )
        
        assert result["result"] is True
        mock_post.assert_called_once()
    
    await client.close()


@pytest.mark.asyncio
async def test_check_policy_failure():
    """Test policy check with HTTP error."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client = OPAClient(settings)
    
    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Connection failed")
        
        result = await client.check_policy(
            "xagent/base/allow",
            {"user": {"authenticated": True}}
        )
        
        assert result["result"] is False
        assert result["allowed"] is False
        assert "error" in result
    
    await client.close()


@pytest.mark.asyncio
async def test_check_base_policy():
    """Test base policy check."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client = OPAClient(settings)
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"result": True}
    mock_response.raise_for_status = MagicMock()
    
    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        result = await client.check_base_policy({
            "user": {
                "authenticated": True,
                "token_valid": True
            }
        })
        
        assert result is True
    
    await client.close()


@pytest.mark.asyncio
async def test_check_api_access_allowed():
    """Test API access check - allowed."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client = OPAClient(settings)
    
    allow_response = MagicMock()
    allow_response.json.return_value = {"result": True}
    allow_response.raise_for_status = MagicMock()
    
    deny_response = MagicMock()
    deny_response.json.return_value = {"result": []}
    deny_response.raise_for_status = MagicMock()
    
    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [allow_response, deny_response]
        
        result = await client.check_api_access({
            "user": {"authenticated": True, "scopes": ["agent_control"]},
            "request": {"method": "GET", "path": "/api/v1/goals"}
        })
        
        assert result["allowed"] is True
        assert result["deny_reasons"] == []
    
    await client.close()


@pytest.mark.asyncio
async def test_check_api_access_denied():
    """Test API access check - denied."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client = OPAClient(settings)
    
    allow_response = MagicMock()
    allow_response.json.return_value = {"result": False}
    allow_response.raise_for_status = MagicMock()
    
    deny_response = MagicMock()
    deny_response.json.return_value = {"result": ["Authentication required"]}
    deny_response.raise_for_status = MagicMock()
    
    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [allow_response, deny_response]
        
        result = await client.check_api_access({
            "user": {"authenticated": False},
            "request": {"method": "POST", "path": "/api/v1/goals"}
        })
        
        assert result["allowed"] is False
        assert "Authentication required" in result["deny_reasons"]
    
    await client.close()


@pytest.mark.asyncio
async def test_check_tool_execution_allowed():
    """Test tool execution check - allowed."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client = OPAClient(settings)
    
    allow_response = MagicMock()
    allow_response.json.return_value = {"result": True}
    allow_response.raise_for_status = MagicMock()
    
    deny_response = MagicMock()
    deny_response.json.return_value = {"result": []}
    deny_response.raise_for_status = MagicMock()
    
    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [allow_response, deny_response]
        
        result = await client.check_tool_execution({
            "user": {"authenticated": True, "scopes": ["code_exec"]},
            "tool": {
                "name": "execute_code",
                "sandboxed": True,
                "args": {"code": "print('hello')"}
            }
        })
        
        assert result["allowed"] is True
        assert result["deny_reasons"] == []
    
    await client.close()


@pytest.mark.asyncio
async def test_check_tool_execution_denied():
    """Test tool execution check - denied."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client = OPAClient(settings)
    
    allow_response = MagicMock()
    allow_response.json.return_value = {"result": False}
    allow_response.raise_for_status = MagicMock()
    
    deny_response = MagicMock()
    deny_response.json.return_value = {"result": ["Dangerous code pattern detected"]}
    deny_response.raise_for_status = MagicMock()
    
    with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [allow_response, deny_response]
        
        result = await client.check_tool_execution({
            "user": {"authenticated": True, "scopes": ["code_exec"]},
            "tool": {
                "name": "execute_code",
                "sandboxed": True,
                "args": {"code": "eval('malicious code')"}
            }
        })
        
        assert result["allowed"] is False
        assert "Dangerous code pattern detected" in result["deny_reasons"]
    
    await client.close()


@pytest.mark.asyncio
async def test_context_manager():
    """Test OPA client as context manager."""
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    
    async with OPAClient(settings) as client:
        assert client is not None
        assert client._client is not None


def test_get_opa_client_singleton():
    """Test OPA client singleton."""
    # Reset global singleton
    import xagent.security.opa_client
    xagent.security.opa_client._opa_client = None
    
    settings = Settings(opa_url="http://localhost:8181", opa_enabled=True)
    client1 = get_opa_client(settings)
    client2 = get_opa_client()
    
    assert client1 is client2
