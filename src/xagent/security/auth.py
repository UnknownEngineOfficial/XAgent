"""Authentication and authorization module for X-Agent.

Implements JWT-based authentication with scope-based authorization.
Uses Authlib for secure token management.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from authlib.jose import JoseError, jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from xagent.config import Settings, get_settings
from xagent.utils.logging import get_logger

logger = get_logger(__name__)

# Security scheme for FastAPI
security = HTTPBearer()


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    USER = "user"
    SERVICE = "service"
    READONLY = "readonly"


class TokenScope(str, Enum):
    """Available permission scopes."""

    # Goal management
    GOAL_READ = "goal:read"
    GOAL_WRITE = "goal:write"
    GOAL_DELETE = "goal:delete"

    # Agent control
    AGENT_READ = "agent:read"
    AGENT_CONTROL = "agent:control"

    # Tool execution
    TOOL_EXECUTE = "tool:execute"
    TOOL_CODE_EXEC = "tool:code_exec"
    TOOL_FILE_OPS = "tool:file_ops"
    TOOL_WEB_SEARCH = "tool:web_search"
    TOOL_NETWORK = "tool:network"

    # System administration
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_METRICS = "system:metrics"


# Role to scope mapping
ROLE_SCOPES: dict[UserRole, set[TokenScope]] = {
    UserRole.ADMIN: {
        TokenScope.GOAL_READ,
        TokenScope.GOAL_WRITE,
        TokenScope.GOAL_DELETE,
        TokenScope.AGENT_READ,
        TokenScope.AGENT_CONTROL,
        TokenScope.TOOL_EXECUTE,
        TokenScope.TOOL_CODE_EXEC,
        TokenScope.TOOL_FILE_OPS,
        TokenScope.TOOL_WEB_SEARCH,
        TokenScope.TOOL_NETWORK,
        TokenScope.SYSTEM_ADMIN,
        TokenScope.SYSTEM_METRICS,
    },
    UserRole.USER: {
        TokenScope.GOAL_READ,
        TokenScope.GOAL_WRITE,
        TokenScope.AGENT_READ,
        TokenScope.AGENT_CONTROL,
        TokenScope.TOOL_EXECUTE,
        TokenScope.TOOL_WEB_SEARCH,
    },
    UserRole.SERVICE: {
        TokenScope.GOAL_READ,
        TokenScope.AGENT_READ,
        TokenScope.SYSTEM_METRICS,
    },
    UserRole.READONLY: {
        TokenScope.GOAL_READ,
        TokenScope.AGENT_READ,
    },
}


class User(BaseModel):
    """User model for authentication."""

    username: str = Field(..., description="Username")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    scopes: list[str] = Field(default_factory=list, description="Permission scopes")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def has_scope(self, scope: str) -> bool:
        """Check if user has a specific scope."""
        return scope in self.scopes

    def has_any_scope(self, scopes: list[str]) -> bool:
        """Check if user has any of the given scopes."""
        return any(scope in self.scopes for scope in scopes)


class TokenData(BaseModel):
    """JWT token payload data."""

    sub: str = Field(..., description="Subject (username)")
    role: str = Field(default="user", description="User role")
    scopes: list[str] = Field(default_factory=list, description="Permission scopes")
    exp: int | None = Field(None, description="Expiration timestamp")
    iat: int | None = Field(None, description="Issued at timestamp")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AuthManager:
    """Manages JWT token creation and validation."""

    def __init__(self, settings: Settings | None = None):
        """Initialize auth manager."""
        self.settings = settings or get_settings()
        self._secret_key = self.settings.SECRET_KEY

        if not self._secret_key or self._secret_key == "change-me-in-production":
            logger.warning(
                "Using default SECRET_KEY. Set SECRET_KEY environment variable for production!"
            )

    def create_access_token(
        self,
        username: str,
        role: UserRole = UserRole.USER,
        scopes: list[str] | None = None,
        expires_delta: timedelta | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a JWT access token.

        Args:
            username: Username for the token
            role: User role
            scopes: Permission scopes (defaults to role scopes)
            expires_delta: Token expiration time
            metadata: Additional metadata

        Returns:
            Encoded JWT token
        """
        # Use role scopes if not explicitly provided
        if scopes is None:
            scopes = [s.value for s in ROLE_SCOPES.get(role, set())]

        # Set expiration
        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        # Create payload
        payload = {
            "sub": username,
            "role": role.value,
            "scopes": scopes,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }

        if metadata:
            payload["metadata"] = metadata

        # Encode JWT
        header = {"alg": "HS256"}
        token_bytes = jwt.encode(header, payload, self._secret_key)
        token = token_bytes.decode("utf-8") if isinstance(token_bytes, bytes) else token_bytes

        logger.info(f"Created access token for user: {username}, role: {role.value}")

        return token

    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token data

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Decode token
            payload = jwt.decode(token, self._secret_key)

            # Manual expiration validation
            # Note: authlib jwt.decode does not automatically validate exp claim
            # We must check it manually to ensure token hasn't expired
            exp = payload.get("exp")
            if exp:
                now_timestamp = datetime.now(timezone.utc).timestamp()
                if exp < now_timestamp:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

            # Validate required fields
            username = payload.get("sub")
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing subject",
                )

            # Create token data
            token_data = TokenData(
                sub=username,
                role=payload.get("role", "user"),
                scopes=payload.get("scopes", []),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                metadata=payload.get("metadata", {}),
            )

            logger.debug(f"Verified token for user: {username}")

            return token_data

        except JoseError as e:
            logger.warning(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def get_user_from_token(self, token: str) -> User:
        """
        Extract user information from token.

        Args:
            token: JWT token string

        Returns:
            User object
        """
        token_data = self.verify_token(token)

        return User(
            username=token_data.sub,
            role=UserRole(token_data.role),
            scopes=token_data.scopes,
            metadata=token_data.metadata,
        )


# Global auth manager instance
_auth_manager: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    """Get or create auth manager singleton."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


# FastAPI dependency functions


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> User:
    """
    FastAPI dependency to verify JWT token and extract user.

    Args:
        credentials: HTTP authorization credentials
        auth_manager: Auth manager instance

    Returns:
        Authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    user = auth_manager.get_user_from_token(token)

    logger.debug(f"Authenticated user: {user.username}, role: {user.role}")

    return user


def require_scope(required_scope: str):
    """
    Create a dependency that requires a specific scope.

    Args:
        required_scope: Required permission scope

    Returns:
        FastAPI dependency function

    Example:
        @app.get("/goals", dependencies=[Depends(require_scope(TokenScope.GOAL_READ))])
    """

    async def scope_checker(user: User = Depends(verify_token)) -> User:
        """Check if user has required scope."""
        if not user.has_scope(required_scope):
            logger.warning(f"User {user.username} lacks required scope: {required_scope}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}",
            )
        return user

    return scope_checker


def require_any_scope(required_scopes: list[str]):
    """
    Create a dependency that requires any of the given scopes.

    Args:
        required_scopes: List of acceptable scopes

    Returns:
        FastAPI dependency function
    """

    async def scope_checker(user: User = Depends(verify_token)) -> User:
        """Check if user has any of the required scopes."""
        if not user.has_any_scope(required_scopes):
            logger.warning(f"User {user.username} lacks any required scope: {required_scopes}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scopes: {required_scopes}",
            )
        return user

    return scope_checker


def require_role(required_role: UserRole):
    """
    Create a dependency that requires a specific role.

    Args:
        required_role: Required user role

    Returns:
        FastAPI dependency function
    """

    async def role_checker(user: User = Depends(verify_token)) -> User:
        """Check if user has required role."""
        if user.role != required_role:
            logger.warning(f"User {user.username} has role {user.role}, required: {required_role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role.value}",
            )
        return user

    return role_checker


# Optional authentication (allows unauthenticated access)


async def optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(HTTPBearer(auto_error=False)),
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> User | None:
    """
    Optional authentication dependency.

    Returns user if authenticated, None otherwise.
    Useful for endpoints that work differently based on authentication.
    """
    if credentials is None:
        return None

    try:
        token = credentials.credentials
        return auth_manager.get_user_from_token(token)
    except HTTPException:
        return None
