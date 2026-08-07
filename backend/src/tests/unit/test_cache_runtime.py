from __future__ import annotations

import pytest

from cache.contracts import CacheUnavailable
from cache.memory import MemoryCacheStore
from cache.runtime import CacheRuntimeError, create_cache_store


def test_development_defaults_to_in_process_memory_cache():
    cache = create_cache_store(runtime_environment="development")

    assert isinstance(cache, MemoryCacheStore)


def test_explicit_redis_backend_requires_a_redis_url():
    with pytest.raises(CacheRuntimeError, match="REDIS_URL"):
        create_cache_store(
            runtime_environment="development",
            cache_backend="redis",
            redis_url="",
        )


def test_production_rejects_memory_cache():
    with pytest.raises(CacheRuntimeError, match="production.*redis"):
        create_cache_store(
            runtime_environment="production",
            cache_backend="memory",
        )


def test_memory_cache_expires_values():
    cache = MemoryCacheStore(clock=lambda: 10.0)
    cache.set("snapshot", b"payload", ttl_seconds=1)

    assert cache.get("snapshot") == b"payload"

    cache._clock = lambda: 11.0

    assert cache.get("snapshot") is None


def test_versioned_publication_writes_value_before_switching_pointer():
    cache = MemoryCacheStore()
    pointer_key = "public:latest:pointer"
    first_key = "public:latest:v1"
    second_key = "public:latest:v2"

    cache.publish_versioned(pointer_key, first_key, b"first", ttl_seconds=60)
    cache.publish_versioned(pointer_key, second_key, b"second", ttl_seconds=60)

    assert cache.get(first_key) == b"first"
    assert cache.get(pointer_key) == second_key.encode("utf-8")
    assert cache.get_versioned(pointer_key) == b"second"


def test_cache_backend_errors_are_exposed_as_cache_unavailable():
    class BrokenCache(MemoryCacheStore):
        def _write(self, key: str, value: bytes, ttl_seconds: int) -> None:
            raise OSError("connection reset")

    with pytest.raises(CacheUnavailable, match="connection reset"):
        BrokenCache().set("snapshot", b"payload", ttl_seconds=1)
