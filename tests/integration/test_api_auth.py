"""Integration tests for REST API authentication."""

import pytest
from fastapi.testclient import TestClient

from xagent.api.rest import app
from xagent.security.auth import get_auth_manager, UserRole, TokenScope


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_manager():
    """Get the auth manager used by the app."""
    return get_auth_manager()


@pytest.fixture
def admin_token(auth_manager):
    """Create admin token."""
    return auth_manager.create_access_token(
        username="admin",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def user_token(auth_manager):
    """Create user token."""
    return auth_manager.create_access_token(
        username="testuser",
        role=UserRole.USER,
    )


@pytest.fixture
def readonly_token(auth_manager):
    """Create readonly token."""
    return auth_manager.create_access_token(
        username="readonly",
        role=UserRole.READONLY,
    )


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""
    
    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "username": "testuser",
                "password": "password",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user"]["username"] == "testuser"
    
    def test_login_admin_gets_admin_role(self, client):
        """Test that admin username gets admin role."""
        response = client.post(
            "/auth/login",
            json={
                "username": "admin",
                "password": "password",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user"]["role"] == "admin"
    
    def test_get_current_user_with_valid_token(self, client, user_token):
        """Test getting current user with valid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == "testuser"
        assert data["role"] == "user"
        assert isinstance(data["scopes"], list)
    
    def test_get_current_user_without_token(self, client):
        """Test getting current user without token."""
        response = client.get("/auth/me")
        
        assert response.status_code == 403  # No credentials
    
    def test_get_current_user_with_invalid_token(self, client):
        """Test getting current user with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        
        assert response.status_code == 401
    
    def test_create_token_as_admin(self, client, admin_token):
        """Test creating token as admin."""
        response = client.post(
            "/auth/token",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": "newuser",
                "role": "user",
                "expires_hours": 48,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["user"]["username"] == "newuser"
        assert data["user"]["role"] == "user"
        assert data["expires_in"] == 48 * 3600
    
    def test_create_token_as_non_admin_fails(self, client, user_token):
        """Test that non-admin cannot create tokens."""
        response = client.post(
            "/auth/token",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "username": "newuser",
                "role": "user",
                "expires_hours": 24,
            },
        )
        
        assert response.status_code == 403


class TestProtectedEndpoints:
    """Test that endpoints are properly protected."""
    
    def test_status_without_auth_returns_limited_info(self, client):
        """Test that status endpoint returns limited info without auth."""
        response = client.get("/status")
        
        # Should work but return limited data
        # Note: This will fail if agent is not initialized, which is expected
        assert response.status_code in [200, 503]
    
    def test_start_agent_without_auth_fails(self, client):
        """Test that starting agent without auth fails."""
        response = client.post("/start")
        
        assert response.status_code == 403
    
    def test_start_agent_with_user_token_succeeds(self, client, user_token):
        """Test that user can start agent."""
        response = client.post(
            "/start",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        
        # Will be 503 if agent not initialized, but auth should pass
        assert response.status_code in [200, 503]
    
    def test_stop_agent_without_auth_fails(self, client):
        """Test that stopping agent without auth fails."""
        response = client.post("/stop")
        
        assert response.status_code == 403
    
    def test_command_without_auth_fails(self, client):
        """Test that sending command without auth fails."""
        response = client.post(
            "/command",
            json={"command": "test"},
        )
        
        assert response.status_code == 403
    
    def test_create_goal_without_auth_fails(self, client):
        """Test that creating goal without auth fails."""
        response = client.post(
            "/goals",
            json={
                "description": "Test goal",
                "mode": "goal_oriented",
            },
        )
        
        assert response.status_code == 403
    
    def test_create_goal_with_user_token_succeeds(self, client, user_token):
        """Test that user can create goals."""
        response = client.post(
            "/goals",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "description": "Test goal",
                "mode": "goal_oriented",
            },
        )
        
        # Will be 503 if agent not initialized
        assert response.status_code in [200, 503]
    
    def test_list_goals_without_auth_fails(self, client):
        """Test that listing goals without auth fails."""
        response = client.get("/goals")
        
        assert response.status_code == 403
    
    def test_list_goals_with_readonly_token_succeeds(self, client, readonly_token):
        """Test that readonly user can list goals."""
        response = client.get(
            "/goals",
            headers={"Authorization": f"Bearer {readonly_token}"},
        )
        
        # Will be 503 if agent not initialized
        assert response.status_code in [200, 503]
    
    def test_readonly_cannot_create_goals(self, client, readonly_token):
        """Test that readonly user cannot create goals."""
        response = client.post(
            "/goals",
            headers={"Authorization": f"Bearer {readonly_token}"},
            json={
                "description": "Test goal",
                "mode": "goal_oriented",
            },
        )
        
        assert response.status_code == 403


class TestHealthEndpointsPublic:
    """Test that health endpoints remain public."""
    
    def test_health_endpoint_public(self, client):
        """Test that /health is accessible without auth."""
        response = client.get("/health")
        
        # Should always return something (200 or 503)
        assert response.status_code in [200, 503]
        assert "status" in response.json()
    
    def test_healthz_endpoint_public(self, client):
        """Test that /healthz is accessible without auth."""
        response = client.get("/healthz")
        
        assert response.status_code in [200, 503]
    
    def test_ready_endpoint_public(self, client):
        """Test that /ready is accessible without auth."""
        response = client.get("/ready")
        
        assert response.status_code in [200, 503]


class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def test_admin_has_all_scopes(self, auth_manager, admin_token):
        """Test that admin has all scopes."""
        user = auth_manager.get_user_from_token(admin_token)
        
        # Admin should have all critical scopes
        assert user.has_scope(TokenScope.SYSTEM_ADMIN.value)
        assert user.has_scope(TokenScope.TOOL_CODE_EXEC.value)
        assert user.has_scope(TokenScope.AGENT_CONTROL.value)
        assert user.has_scope(TokenScope.GOAL_WRITE.value)
    
    def test_user_has_limited_scopes(self, auth_manager, user_token):
        """Test that regular user has limited scopes."""
        user = auth_manager.get_user_from_token(user_token)
        
        # User should have basic scopes
        assert user.has_scope(TokenScope.AGENT_CONTROL.value)
        assert user.has_scope(TokenScope.GOAL_WRITE.value)
        
        # But not admin scopes
        assert not user.has_scope(TokenScope.SYSTEM_ADMIN.value)
        assert not user.has_scope(TokenScope.TOOL_CODE_EXEC.value)
    
    def test_readonly_cannot_write(self, auth_manager, readonly_token):
        """Test that readonly user cannot write."""
        user = auth_manager.get_user_from_token(readonly_token)
        
        # Readonly should only have read scopes
        assert user.has_scope(TokenScope.GOAL_READ.value)
        assert user.has_scope(TokenScope.AGENT_READ.value)
        
        # No write or control scopes
        assert not user.has_scope(TokenScope.GOAL_WRITE.value)
        assert not user.has_scope(TokenScope.AGENT_CONTROL.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
