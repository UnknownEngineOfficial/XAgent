"""Tests for configuration."""

import pytest
import os
from xagent.config import Settings


def test_settings_initialization():
    """Test settings initialization with defaults."""
    settings = Settings()
    
    # Check API keys
    assert settings.openai_api_key == ""
    assert settings.anthropic_api_key == ""
    
    # Check Redis defaults
    assert settings.redis_host == "localhost"
    assert settings.redis_port == 6379
    assert settings.redis_db == 0
    
    # Check PostgreSQL defaults
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432
    assert settings.postgres_db == "xagent"
    assert settings.postgres_user == "xagent"
    
    # Check server defaults
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.ws_port == 8001


def test_settings_custom_values():
    """Test settings with custom values."""
    settings = Settings(
        openai_api_key="test-key",
        redis_host="redis.example.com",
        redis_port=6380,
        api_port=9000,
    )
    
    assert settings.openai_api_key == "test-key"
    assert settings.redis_host == "redis.example.com"
    assert settings.redis_port == 6380
    assert settings.api_port == 9000


def test_redis_url_without_password():
    """Test Redis URL generation without password."""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password="",
    )
    
    url = settings.redis_url
    assert url == "redis://localhost:6379/0"


def test_redis_url_with_password():
    """Test Redis URL generation with password."""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_db=1,
        redis_password="secret123",
    )
    
    url = settings.redis_url
    assert url == "redis://:secret123@localhost:6379/1"
    assert "secret123" in url


def test_postgres_url():
    """Test PostgreSQL URL generation."""
    settings = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="testdb",
        postgres_user="testuser",
        postgres_password="testpass",
    )
    
    url = settings.postgres_url
    assert "postgresql://" in url
    assert "testuser" in url
    assert "testpass" in url
    assert "localhost" in url
    assert "5432" in url
    assert "testdb" in url


def test_agent_configuration():
    """Test agent configuration defaults."""
    settings = Settings()
    
    assert settings.agent_name == "X-Agent"
    assert settings.agent_mode == "interactive"
    assert settings.max_iterations == 100
    assert settings.loop_delay_seconds == 1.0


def test_tool_configuration():
    """Test tool configuration defaults."""
    settings = Settings()
    
    assert settings.enable_code_tools is True
    assert settings.enable_search_tools is True
    assert settings.enable_file_tools is True
    assert settings.enable_network_tools is True
    assert settings.sandbox_enabled is True


def test_security_configuration():
    """Test security configuration."""
    settings = Settings()
    
    assert settings.secret_key == "change-me-in-production"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expiration_minutes == 60


def test_security_custom_values():
    """Test security with custom values."""
    settings = Settings(
        secret_key="my-secret-key",
        jwt_algorithm="HS512",
        jwt_expiration_minutes=120,
    )
    
    assert settings.secret_key == "my-secret-key"
    assert settings.jwt_algorithm == "HS512"
    assert settings.jwt_expiration_minutes == 120


def test_monitoring_configuration():
    """Test monitoring configuration."""
    settings = Settings()
    
    assert settings.prometheus_port == 9090
    assert settings.log_level == "INFO"


def test_celery_configuration():
    """Test Celery configuration."""
    settings = Settings()
    
    assert "redis://" in settings.celery_broker_url
    assert "redis://" in settings.celery_result_backend


def test_chroma_configuration():
    """Test ChromaDB configuration."""
    settings = Settings()
    
    assert settings.chroma_host == "localhost"
    assert settings.chroma_port == 8000
    assert settings.chroma_persist_directory == "./data/chroma"


def test_custom_chroma_config():
    """Test custom ChromaDB configuration."""
    settings = Settings(
        chroma_host="chroma.example.com",
        chroma_port=9000,
        chroma_persist_directory="/custom/path",
    )
    
    assert settings.chroma_host == "chroma.example.com"
    assert settings.chroma_port == 9000
    assert settings.chroma_persist_directory == "/custom/path"


def test_server_ports():
    """Test server port configuration."""
    settings = Settings(
        api_port=8080,
        ws_port=8081,
        prometheus_port=9091,
    )
    
    assert settings.api_port == 8080
    assert settings.ws_port == 8081
    assert settings.prometheus_port == 9091


def test_settings_field_descriptions():
    """Test that field descriptions are set."""
    settings = Settings()
    
    # Access field info through model (compatible with both pydantic v1 and v2)
    try:
        # Pydantic v2
        fields = settings.model_fields
    except AttributeError:
        # Pydantic v1
        fields = settings.__fields__
    
    assert "openai_api_key" in fields
    # Field description access differs between v1 and v2
    if hasattr(fields["openai_api_key"], "description"):
        assert fields["openai_api_key"].description == "OpenAI API key"
    elif hasattr(fields["openai_api_key"], "field_info"):
        assert fields["openai_api_key"].field_info.description == "OpenAI API key"


def test_postgres_url_format():
    """Test PostgreSQL URL has correct format."""
    settings = Settings(
        postgres_user="user",
        postgres_password="pass",
        postgres_host="host",
        postgres_port=5432,
        postgres_db="db",
    )
    
    url = settings.postgres_url
    
    # Verify URL structure
    assert url.startswith("postgresql://")
    assert "@" in url  # user:pass@host separator
    assert ":" in url  # multiple colons for user:pass and host:port
    assert "/" in url  # separates host:port from database


def test_redis_url_different_db():
    """Test Redis URL with different database numbers."""
    for db_num in [0, 1, 5, 15]:
        settings = Settings(redis_db=db_num)
        url = settings.redis_url
        assert url.endswith(f"/{db_num}")


def test_agent_mode_values():
    """Test different agent mode values."""
    for mode in ["interactive", "focus", "idle", "emergency"]:
        settings = Settings(agent_mode=mode)
        assert settings.agent_mode == mode


def test_log_level_values():
    """Test different log level values."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        settings = Settings(log_level=level)
        assert settings.log_level == level
