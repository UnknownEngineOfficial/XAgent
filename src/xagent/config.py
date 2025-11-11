"""Configuration management for X-Agent."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_settings import BaseSettings as BaseSettingsType
else:
    BaseSettingsType = Any  # type: ignore[misc,assignment]

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseSettings  # type: ignore[assignment,no-redef]
    from pydantic import Field

    PYDANTIC_V2 = False


class Settings(BaseSettings):
    """Application settings."""

    if not PYDANTIC_V2:

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False
            extra = "ignore"

    else:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )

    # API Keys
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="", description="Redis password")
    redis_db: int = Field(default=0, description="Redis database")

    # PostgreSQL Configuration
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="xagent", description="PostgreSQL database")
    postgres_user: str = Field(default="xagent", description="PostgreSQL user")
    postgres_password: str = Field(default="", description="PostgreSQL password")

    # ChromaDB Configuration
    chroma_host: str = Field(default="localhost", description="ChromaDB host")
    chroma_port: int = Field(default=8000, description="ChromaDB port")
    chroma_persist_directory: str = Field(
        default="./data/chroma", description="ChromaDB persist directory"
    )

    # Server Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    ws_host: str = Field(default="0.0.0.0", description="WebSocket host")
    ws_port: int = Field(default=8001, description="WebSocket port")

    # Security
    secret_key: str = Field(default="change-me-in-production", description="Secret key for JWT")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT expiration in minutes")

    # Rate Limiting
    rate_limiting_enabled: bool = Field(default=True, description="Enable API rate limiting")
    rate_limit_default: int = Field(default=100, description="Default rate limit per minute")
    rate_limit_burst: int = Field(default=120, description="Default burst size")

    # OPA (Open Policy Agent) Configuration
    opa_url: str = Field(default="http://localhost:8181", description="OPA server URL")
    opa_enabled: bool = Field(default=False, description="Enable OPA policy enforcement")
    opa_timeout: int = Field(default=5, description="OPA request timeout in seconds")

    # Agent Configuration
    agent_name: str = Field(default="X-Agent", description="Agent name")
    agent_mode: str = Field(
        default="interactive", description="Agent mode: interactive, focus, idle, emergency"
    )
    max_iterations: int = Field(default=100, description="Maximum iterations per task")
    loop_delay_seconds: float = Field(default=1.0, description="Delay between loop iterations")
    max_sub_agents: int = Field(
        default=5, 
        description="Maximum number of concurrent sub-agents for subtask execution (recommended: 5-7)"
    )

    # Planning Configuration
    use_langgraph_planner: bool = Field(
        default=False, description="Use LangGraph-based planner instead of legacy planner"
    )

    # Tool Configuration
    enable_code_tools: bool = Field(default=True, description="Enable code tools")
    enable_search_tools: bool = Field(default=True, description="Enable search tools")
    enable_file_tools: bool = Field(default=True, description="Enable file tools")
    enable_network_tools: bool = Field(default=True, description="Enable network tools")
    sandbox_enabled: bool = Field(default=True, description="Enable sandbox for tool execution")

    # Content Moderation Configuration
    moderation_mode: str = Field(
        default="moderated",
        description="Content moderation mode: 'moderated' (strict) or 'unmoderated' (freedom)",
    )
    moderation_enabled: bool = Field(
        default=True, description="Enable content moderation system"
    )

    # Monitoring
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    log_level: str = Field(default="INFO", description="Log level")

    # Observability - OpenTelemetry
    otlp_endpoint: str = Field(default="", description="OTLP collector endpoint")
    tracing_console: bool = Field(default=False, description="Enable console span exporter")
    tracing_insecure: bool = Field(
        default=True, description="Use insecure OTLP connection (set False for production)"
    )

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend"
    )

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        from urllib.parse import urlunparse

        return urlunparse(
            (
                "postgresql",
                f"{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}",
                f"/{self.postgres_db}",
                "",
                "",
                "",
            )
        )

    @property
    def SECRET_KEY(self) -> str:  # noqa: N802
        """Alias for secret_key (backward compatibility)."""
        return self.secret_key

    @property
    def CELERY_BROKER_URL(self) -> str:  # noqa: N802
        """Alias for celery_broker_url (Celery expects uppercase)."""
        return self.celery_broker_url

    @property
    def CELERY_RESULT_BACKEND(self) -> str:  # noqa: N802
        """Alias for celery_result_backend (Celery expects uppercase)."""
        return self.celery_result_backend


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)."""
    return settings
