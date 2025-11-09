"""Tests for Redis cache implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from xagent.memory.cache import RedisCache, CacheConfig, cached, cache_key_from_args


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("xagent.memory.cache.redis") as mock:
        redis_client = AsyncMock()
        redis_client.ping = AsyncMock()
        redis_client.get = AsyncMock()
        redis_client.setex = AsyncMock()
        redis_client.delete = AsyncMock(return_value=1)
        redis_client.exists = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock(return_value=True)
        redis_client.mget = AsyncMock()
        redis_client.incrby = AsyncMock(return_value=1)
        redis_client.info = AsyncMock()
        redis_client.scan = AsyncMock(return_value=(0, []))
        redis_client.pipeline = MagicMock()
        redis_client.close = AsyncMock()

        mock.from_url = AsyncMock(return_value=redis_client)
        yield redis_client


@pytest.mark.asyncio
async def test_cache_connect(mock_redis):
    """Test Redis connection."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    assert cache._connected is True
    mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_cache_disconnect(mock_redis):
    """Test Redis disconnection."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()
    await cache.disconnect()

    assert cache._connected is False
    mock_redis.close.assert_called_once()


@pytest.mark.asyncio
async def test_cache_get_hit(mock_redis):
    """Test cache get with hit."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    mock_redis.get.return_value = '{"key": "value"}'

    result = await cache.get("test", "key1")

    assert result == {"key": "value"}
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_cache_get_miss(mock_redis):
    """Test cache get with miss."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    mock_redis.get.return_value = None

    result = await cache.get("test", "key1")

    assert result is None
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_cache_set(mock_redis):
    """Test cache set."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    result = await cache.set("test", "key1", {"data": "value"}, ttl=300)

    assert result is True
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "xagent:test:key1"
    assert args[1] == 300


@pytest.mark.asyncio
async def test_cache_delete(mock_redis):
    """Test cache delete."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    result = await cache.delete("test", "key1")

    assert result is True
    mock_redis.delete.assert_called_once_with("xagent:test:key1")


@pytest.mark.asyncio
async def test_cache_exists(mock_redis):
    """Test cache exists."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    result = await cache.exists("test", "key1")

    assert result is True
    mock_redis.exists.assert_called_once()


@pytest.mark.asyncio
async def test_cache_expire(mock_redis):
    """Test cache expire."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    result = await cache.expire("test", "key1", 600)

    assert result is True
    mock_redis.expire.assert_called_once_with("xagent:test:key1", 600)


@pytest.mark.asyncio
async def test_cache_get_many(mock_redis):
    """Test cache get_many."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    mock_redis.mget.return_value = ['{"a": 1}', '{"b": 2}', None]

    result = await cache.get_many("test", ["key1", "key2", "key3"])

    assert len(result) == 2
    assert result["key1"] == {"a": 1}
    assert result["key2"] == {"b": 2}
    mock_redis.mget.assert_called_once()


@pytest.mark.asyncio
async def test_cache_set_many(mock_redis):
    """Test cache set_many."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    pipeline_mock = AsyncMock()
    pipeline_mock.execute = AsyncMock()
    mock_redis.pipeline.return_value = pipeline_mock

    items = {"key1": {"a": 1}, "key2": {"b": 2}}
    result = await cache.set_many("test", items, ttl=300)

    assert result is True
    mock_redis.pipeline.assert_called_once()
    pipeline_mock.execute.assert_called_once()


@pytest.mark.asyncio
async def test_cache_increment(mock_redis):
    """Test cache increment."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    mock_redis.incrby.return_value = 5

    result = await cache.increment("test", "counter", 2)

    assert result == 5
    mock_redis.incrby.assert_called_once_with("xagent:test:counter", 2)


@pytest.mark.asyncio
async def test_cache_delete_pattern(mock_redis):
    """Test cache delete_pattern."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    mock_redis.scan.return_value = (0, ["xagent:test:key1", "xagent:test:key2"])
    mock_redis.delete.return_value = 2

    result = await cache.delete_pattern("test", "key*")

    assert result == 2
    mock_redis.scan.assert_called_once()


@pytest.mark.asyncio
async def test_cache_get_stats(mock_redis):
    """Test cache get_stats."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    mock_redis.info.return_value = {
        "total_commands_processed": 1000,
        "keyspace_hits": 750,
        "keyspace_misses": 250,
        "used_memory_human": "1.5M",
        "connected_clients": 5,
    }

    stats = await cache.get_stats()

    assert stats["connected"] is True
    assert stats["total_commands"] == 1000
    assert stats["keyspace_hits"] == 750
    assert stats["keyspace_misses"] == 250
    assert stats["hit_rate"] == 75.0
    assert stats["used_memory"] == "1.5M"


@pytest.mark.asyncio
async def test_cache_not_connected():
    """Test cache operations when not connected."""
    cache = RedisCache("redis://localhost:6379/0")

    # Should return None/False without errors
    assert await cache.get("test", "key") is None
    assert await cache.set("test", "key", "value") is False
    assert await cache.delete("test", "key") is False
    assert await cache.exists("test", "key") is False


@pytest.mark.asyncio
async def test_cache_connection_error():
    """Test cache connection error handling."""
    with patch("xagent.memory.cache.redis") as mock:
        mock.from_url = AsyncMock(side_effect=Exception("Connection failed"))

        cache = RedisCache("redis://localhost:6379/0")

        with pytest.raises(Exception):
            await cache.connect()

        assert cache._connected is False


@pytest.mark.asyncio
async def test_cache_serialization_error(mock_redis):
    """Test cache serialization error handling."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    # Create object with circular reference (not JSON serializable)
    obj = {}
    obj["self"] = obj

    # Should handle error gracefully and return False
    result = await cache.set("test", "key", obj)
    assert result is False


def test_cache_key_from_args():
    """Test cache key generation from arguments."""
    key1 = cache_key_from_args("arg1", "arg2", kwarg1="value1")
    key2 = cache_key_from_args("arg1", "arg2", kwarg1="value1")
    key3 = cache_key_from_args("arg1", "arg3", kwarg1="value1")

    assert key1 == key2  # Same args should produce same key
    assert key1 != key3  # Different args should produce different key


@pytest.mark.asyncio
async def test_cached_decorator_hit(mock_redis):
    """Test @cached decorator with cache hit."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    class TestService:
        def __init__(self):
            self._cache = cache

        @cached(category="test", ttl=300)
        async def get_data(self, key: str):
            return {"data": key}

    mock_redis.get.return_value = '{"data": "cached_value"}'

    service = TestService()
    result = await service.get_data("test_key")

    assert result == {"data": "cached_value"}


@pytest.mark.asyncio
async def test_cached_decorator_miss(mock_redis):
    """Test @cached decorator with cache miss."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    class TestService:
        def __init__(self):
            self._cache = cache

        @cached(category="test", ttl=300)
        async def get_data(self, key: str):
            return {"data": key}

    mock_redis.get.return_value = None

    service = TestService()
    result = await service.get_data("test_key")

    assert result == {"data": "test_key"}
    # Should have called set after function execution
    mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cached_decorator_no_cache():
    """Test @cached decorator without cache available."""

    class TestService:
        @cached(category="test", ttl=300)
        async def get_data(self, key: str):
            return {"data": key}

    service = TestService()
    result = await service.get_data("test_key")

    # Should call function directly when no cache
    assert result == {"data": "test_key"}


def test_cache_config():
    """Test cache configuration constants."""
    assert CacheConfig.DEFAULT_TTL == 300
    assert CacheConfig.SHORT_TTL == 60
    assert CacheConfig.MEDIUM_TTL == 600
    assert CacheConfig.LONG_TTL == 3600

    assert CacheConfig.PREFIX_GOAL == "goal"
    assert CacheConfig.PREFIX_AGENT_STATE == "agent_state"
    assert CacheConfig.PREFIX_MEMORY == "memory"


@pytest.mark.asyncio
async def test_cache_make_key(mock_redis):
    """Test cache key generation."""
    cache = RedisCache("redis://localhost:6379/0", key_prefix="myapp")
    await cache.connect()

    key = cache._make_key("category", "key123")
    assert key == "myapp:category:key123"


@pytest.mark.asyncio
async def test_cache_pipeline_error(mock_redis):
    """Test error handling in set_many."""
    cache = RedisCache("redis://localhost:6379/0")
    await cache.connect()

    pipeline_mock = AsyncMock()
    pipeline_mock.execute = AsyncMock(side_effect=Exception("Pipeline error"))
    mock_redis.pipeline.return_value = pipeline_mock

    result = await cache.set_many("test", {"key": "value"})

    assert result is False
