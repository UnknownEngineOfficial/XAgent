"""Tests for authentication module."""

import pytest
from datetime import timedelta
from unittest.mock import Mock, patch

from fastapi import HTTPException

from xagent.security.auth import (
    AuthManager,
    User,
    UserRole,
    TokenScope,
    TokenData,
    ROLE_SCOPES,
    verify_token,
    require_scope,
    require_role,
)
from xagent.config import Settings


@pytest.fixture
def auth_manager():
    """Create auth manager for testing."""
    settings = Settings(secret_key="test-secret-32-characters-long!!")
    return AuthManager(settings)


@pytest.fixture
def admin_token(auth_manager):
    """Create admin token for testing."""
    return auth_manager.create_access_token(
        username="admin",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def user_token(auth_manager):
    """Create user token for testing."""
    return auth_manager.create_access_token(
        username="testuser",
        role=UserRole.USER,
    )


@pytest.fixture
def readonly_token(auth_manager):
    """Create readonly token for testing."""
    return auth_manager.create_access_token(
        username="readonly",
        role=UserRole.READONLY,
    )


class TestAuthManager:
    """Test AuthManager class."""

    def test_create_access_token(self, auth_manager):
        """Test creating an access token."""
        token = auth_manager.create_access_token(
            username="testuser",
            role=UserRole.USER,
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_custom_scopes(self, auth_manager):
        """Test creating token with custom scopes."""
        custom_scopes = [TokenScope.GOAL_READ.value, TokenScope.AGENT_READ.value]

        token = auth_manager.create_access_token(
            username="testuser",
            role=UserRole.USER,
            scopes=custom_scopes,
        )

        token_data = auth_manager.verify_token(token)
        assert set(token_data.scopes) == set(custom_scopes)

    def test_create_token_with_expiration(self, auth_manager):
        """Test creating token with custom expiration."""
        token = auth_manager.create_access_token(
            username="testuser",
            role=UserRole.USER,
            expires_delta=timedelta(minutes=30),
        )

        token_data = auth_manager.verify_token(token)
        assert token_data.exp is not None

    def test_create_token_with_metadata(self, auth_manager):
        """Test creating token with metadata."""
        metadata = {"user_id": 123, "org": "test-org"}

        token = auth_manager.create_access_token(
            username="testuser",
            role=UserRole.USER,
            metadata=metadata,
        )

        token_data = auth_manager.verify_token(token)
        assert token_data.metadata == metadata

    def test_verify_valid_token(self, auth_manager, user_token):
        """Test verifying a valid token."""
        token_data = auth_manager.verify_token(user_token)

        assert token_data.sub == "testuser"
        assert token_data.role == UserRole.USER.value
        assert isinstance(token_data.scopes, list)
        assert len(token_data.scopes) > 0

    def test_verify_invalid_token(self, auth_manager):
        """Test verifying an invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token("invalid-token")

        assert exc_info.value.status_code == 401

    def test_verify_token_with_wrong_secret(self, auth_manager):
        """Test verifying token with different secret."""
        token = auth_manager.create_access_token(
            username="testuser",
            role=UserRole.USER,
        )

        # Create new manager with different secret
        other_settings = Settings(secret_key="different-secret")
        other_manager = AuthManager(other_settings)

        with pytest.raises(HTTPException) as exc_info:
            other_manager.verify_token(token)

        assert exc_info.value.status_code == 401

    def test_get_user_from_token(self, auth_manager, user_token):
        """Test extracting user from token."""
        user = auth_manager.get_user_from_token(user_token)

        assert isinstance(user, User)
        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert isinstance(user.scopes, list)


class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test creating a user."""
        user = User(
            username="testuser",
            role=UserRole.USER,
            scopes=[TokenScope.GOAL_READ.value, TokenScope.AGENT_READ.value],
        )

        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert len(user.scopes) == 2

    def test_has_scope(self):
        """Test checking if user has a scope."""
        user = User(
            username="testuser",
            role=UserRole.USER,
            scopes=[TokenScope.GOAL_READ.value, TokenScope.AGENT_READ.value],
        )

        assert user.has_scope(TokenScope.GOAL_READ.value)
        assert user.has_scope(TokenScope.AGENT_READ.value)
        assert not user.has_scope(TokenScope.SYSTEM_ADMIN.value)

    def test_has_any_scope(self):
        """Test checking if user has any of given scopes."""
        user = User(
            username="testuser",
            role=UserRole.USER,
            scopes=[TokenScope.GOAL_READ.value],
        )

        assert user.has_any_scope([TokenScope.GOAL_READ.value, TokenScope.GOAL_WRITE.value])
        assert not user.has_any_scope(
            [TokenScope.SYSTEM_ADMIN.value, TokenScope.TOOL_CODE_EXEC.value]
        )


class TestRoleScopes:
    """Test role to scope mappings."""

    def test_admin_has_all_scopes(self):
        """Test that admin role has all scopes."""
        admin_scopes = ROLE_SCOPES[UserRole.ADMIN]

        # Admin should have access to everything
        assert TokenScope.SYSTEM_ADMIN in admin_scopes
        assert TokenScope.TOOL_CODE_EXEC in admin_scopes
        assert TokenScope.GOAL_DELETE in admin_scopes

    def test_user_has_limited_scopes(self):
        """Test that user role has limited scopes."""
        user_scopes = ROLE_SCOPES[UserRole.USER]

        # User should have basic access
        assert TokenScope.GOAL_READ in user_scopes
        assert TokenScope.GOAL_WRITE in user_scopes
        assert TokenScope.AGENT_CONTROL in user_scopes

        # But not admin access
        assert TokenScope.SYSTEM_ADMIN not in user_scopes
        assert TokenScope.TOOL_CODE_EXEC not in user_scopes

    def test_readonly_has_minimal_scopes(self):
        """Test that readonly role has minimal scopes."""
        readonly_scopes = ROLE_SCOPES[UserRole.READONLY]

        # Readonly should only have read access
        assert TokenScope.GOAL_READ in readonly_scopes
        assert TokenScope.AGENT_READ in readonly_scopes

        # No write or control access
        assert TokenScope.GOAL_WRITE not in readonly_scopes
        assert TokenScope.AGENT_CONTROL not in readonly_scopes

    def test_service_has_metrics_access(self):
        """Test that service role has metrics access."""
        service_scopes = ROLE_SCOPES[UserRole.SERVICE]

        # Service should have monitoring access
        assert TokenScope.SYSTEM_METRICS in service_scopes
        assert TokenScope.GOAL_READ in service_scopes


class TestAuthenticationIntegration:
    """Integration tests for authentication flow."""

    def test_full_authentication_flow(self, auth_manager):
        """Test complete authentication flow."""
        # Create token
        token = auth_manager.create_access_token(
            username="testuser",
            role=UserRole.USER,
        )

        # Verify token
        token_data = auth_manager.verify_token(token)
        assert token_data.sub == "testuser"

        # Get user
        user = auth_manager.get_user_from_token(token)
        assert user.username == "testuser"
        assert user.role == UserRole.USER

    def test_scope_based_authorization(self, auth_manager):
        """Test scope-based authorization."""
        # Create admin user
        admin_token = auth_manager.create_access_token(
            username="admin",
            role=UserRole.ADMIN,
        )
        admin_user = auth_manager.get_user_from_token(admin_token)

        # Admin should have code execution scope
        assert admin_user.has_scope(TokenScope.TOOL_CODE_EXEC.value)

        # Create regular user
        user_token = auth_manager.create_access_token(
            username="user",
            role=UserRole.USER,
        )
        regular_user = auth_manager.get_user_from_token(user_token)

        # Regular user should NOT have code execution scope
        assert not regular_user.has_scope(TokenScope.TOOL_CODE_EXEC.value)

    def test_token_expiration(self, auth_manager):
        """Test that expired tokens are rejected."""
        # Create token that expires immediately
        token = auth_manager.create_access_token(
            username="testuser",
            role=UserRole.USER,
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        # Should raise exception for expired token
        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(token)

        assert exc_info.value.status_code == 401


class TestFastAPIDependencies:
    """Test FastAPI dependency functions."""

    @pytest.mark.asyncio
    async def test_verify_token_dependency(self, auth_manager, user_token):
        """Test verify_token dependency."""
        from fastapi.security import HTTPAuthorizationCredentials

        # Mock credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=user_token,
        )

        # Test dependency
        user = await verify_token(credentials, auth_manager)

        assert isinstance(user, User)
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_require_scope_dependency_success(self, auth_manager, admin_token):
        """Test require_scope dependency with valid scope."""
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=admin_token,
        )

        # Get user first
        user = await verify_token(credentials, auth_manager)

        # Test scope checker
        scope_checker = require_scope(TokenScope.SYSTEM_ADMIN.value)
        result = await scope_checker(user)

        assert result == user

    @pytest.mark.asyncio
    async def test_require_scope_dependency_failure(self, auth_manager, readonly_token):
        """Test require_scope dependency with invalid scope."""
        from fastapi.security import HTTPAuthorizationCredentials

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=readonly_token,
        )

        # Get user first
        user = await verify_token(credentials, auth_manager)

        # Test scope checker - should fail
        scope_checker = require_scope(TokenScope.SYSTEM_ADMIN.value)

        with pytest.raises(HTTPException) as exc_info:
            await scope_checker(user)

        assert exc_info.value.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
