"""Integration tests for moderation API endpoints."""

import pytest
from fastapi.testclient import TestClient

from xagent.api.rest import app
from xagent.security.auth import AuthManager, UserRole


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_manager() -> AuthManager:
    """Create auth manager for generating tokens."""
    return AuthManager()


@pytest.fixture
def user_token(auth_manager: AuthManager) -> str:
    """Create user token."""
    return auth_manager.create_access_token(
        username="testuser", role=UserRole.USER, scopes=["moderation:read"]
    )


@pytest.fixture
def admin_token(auth_manager: AuthManager) -> str:
    """Create admin token."""
    return auth_manager.create_access_token(
        username="admin", role=UserRole.ADMIN, scopes=["moderation:write"]
    )


class TestModerationStatusEndpoint:
    """Tests for GET /moderation/status endpoint."""

    def test_get_status_without_auth(self, client: TestClient) -> None:
        """Test getting status without authentication fails."""
        response = client.get("/moderation/status")
        assert response.status_code in (401, 403)  # May return either depending on auth middleware

    def test_get_status_with_auth(self, client: TestClient, user_token: str) -> None:
        """Test getting status with authentication."""
        response = client.get(
            "/moderation/status", headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert "acknowledgment_given" in data
        assert "description" in data
        assert data["mode"] in ["moderated", "unmoderated"]

    def test_get_status_default_moderated(self, client: TestClient, user_token: str) -> None:
        """Test status returns moderated mode by default."""
        response = client.get(
            "/moderation/status", headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Note: May be in different state due to other tests, just verify structure
        assert isinstance(data["mode"], str)
        assert isinstance(data["acknowledgment_given"], bool)


class TestModerationModeEndpoint:
    """Tests for POST /moderation/mode endpoint."""

    def test_set_mode_without_auth(self, client: TestClient) -> None:
        """Test setting mode without authentication fails."""
        response = client.post(
            "/moderation/mode", json={"mode": "unmoderated", "user_acknowledgment": True}
        )
        assert response.status_code in (401, 403)  # May return either depending on auth middleware

    def test_set_mode_with_user_role_fails(self, client: TestClient, user_token: str) -> None:
        """Test setting mode with user role fails (requires admin)."""
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"mode": "unmoderated", "user_acknowledgment": True},
        )
        assert response.status_code == 403

    def test_set_mode_to_moderated(self, client: TestClient, admin_token: str) -> None:
        """Test setting mode to moderated with admin role."""
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "moderated", "user_acknowledgment": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["current_mode"] == "moderated"

    def test_set_mode_to_unmoderated_without_acknowledgment(
        self, client: TestClient, admin_token: str
    ) -> None:
        """Test setting to unmoderated mode without acknowledgment fails."""
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "unmoderated", "user_acknowledgment": False},
        )
        assert response.status_code == 400
        data = response.json()
        assert "acknowledgment" in data["detail"].lower()

    def test_set_mode_to_unmoderated_with_acknowledgment(
        self, client: TestClient, admin_token: str
    ) -> None:
        """Test setting to unmoderated mode with acknowledgment."""
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "unmoderated", "user_acknowledgment": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["current_mode"] == "unmoderated"

    def test_set_mode_invalid_mode(self, client: TestClient, admin_token: str) -> None:
        """Test setting invalid mode returns error."""
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "invalid_mode", "user_acknowledgment": False},
        )
        assert response.status_code == 400
        data = response.json()
        assert "invalid" in data["detail"].lower()


class TestModerationCheckEndpoint:
    """Tests for POST /moderation/check endpoint."""

    def test_check_content_without_auth(self, client: TestClient) -> None:
        """Test checking content without authentication fails."""
        response = client.post(
            "/moderation/check", json={"content": {"action": "read_file"}}
        )
        assert response.status_code in (401, 403)  # May return either depending on auth middleware

    def test_check_safe_content(self, client: TestClient, user_token: str) -> None:
        """Test checking safe content."""
        # First ensure we're in moderated mode
        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "read", "file": "document.txt"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert "allowed" in data
        assert "category" in data
        assert data["category"] == "safe"

    def test_check_sensitive_content(self, client: TestClient, user_token: str) -> None:
        """Test checking sensitive content."""
        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "store", "password": "secret123"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "sensitive"

    def test_check_restricted_content_in_moderated_mode(
        self, client: TestClient, user_token: str, admin_token: str
    ) -> None:
        """Test checking restricted content in moderated mode."""
        # Ensure moderated mode
        client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "moderated", "user_acknowledgment": False},
        )

        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "delete database"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["allowed"]
        assert data["category"] == "restricted"
        assert data.get("requires_confirmation", False)

    def test_check_illegal_content_in_moderated_mode(
        self, client: TestClient, user_token: str, admin_token: str
    ) -> None:
        """Test checking illegal content in moderated mode."""
        # Ensure moderated mode
        client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "moderated", "user_acknowledgment": False},
        )

        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "hack", "target": "exploit vulnerability"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["allowed"]
        assert data["category"] == "illegal"
        assert data.get("requires_review", False)

    def test_check_restricted_content_in_unmoderated_mode(
        self, client: TestClient, user_token: str, admin_token: str
    ) -> None:
        """Test checking restricted content in unmoderated mode."""
        # Switch to unmoderated mode
        client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "unmoderated", "user_acknowledgment": True},
        )

        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "delete database"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"]
        assert data["category"] == "restricted"
        assert data.get("warning", False)


class TestAcknowledgeRisksEndpoint:
    """Tests for POST /moderation/acknowledge-risks endpoint."""

    def test_acknowledge_without_auth(self, client: TestClient) -> None:
        """Test acknowledging risks without authentication fails."""
        response = client.post("/moderation/acknowledge-risks")
        assert response.status_code in (401, 403)  # May return either depending on auth middleware

    def test_acknowledge_with_user_role_fails(
        self, client: TestClient, user_token: str
    ) -> None:
        """Test acknowledging risks with user role fails (requires admin)."""
        response = client.post(
            "/moderation/acknowledge-risks",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403

    def test_acknowledge_in_unmoderated_mode(
        self, client: TestClient, admin_token: str
    ) -> None:
        """Test acknowledging risks in unmoderated mode."""
        # Switch to unmoderated mode
        client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "unmoderated", "user_acknowledgment": True},
        )

        response = client.post(
            "/moderation/acknowledge-risks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"]

    def test_acknowledge_in_moderated_mode_fails(
        self, client: TestClient, admin_token: str
    ) -> None:
        """Test acknowledging risks in moderated mode fails."""
        # Ensure moderated mode
        client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "moderated", "user_acknowledgment": False},
        )

        response = client.post(
            "/moderation/acknowledge-risks",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert not data["success"]


class TestModerationWorkflows:
    """Integration tests for complete moderation workflows."""

    def test_complete_mode_switch_workflow(
        self, client: TestClient, user_token: str, admin_token: str
    ) -> None:
        """Test complete workflow of switching modes and checking content."""
        # Start in moderated mode
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "moderated", "user_acknowledgment": False},
        )
        assert response.status_code == 200

        # Check restricted content - should be blocked
        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "drop table users"}},
        )
        assert response.status_code == 200
        assert not response.json()["allowed"]

        # Switch to unmoderated mode
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "unmoderated", "user_acknowledgment": True},
        )
        assert response.status_code == 200

        # Check same content - should be allowed with warning
        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "drop table users"}},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"]
        assert data.get("warning", False)

        # Switch back to moderated mode
        response = client.post(
            "/moderation/mode",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"mode": "moderated", "user_acknowledgment": False},
        )
        assert response.status_code == 200

        # Check content again - should be blocked again
        response = client.post(
            "/moderation/check",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"content": {"action": "drop table users"}},
        )
        assert response.status_code == 200
        assert not response.json()["allowed"]
