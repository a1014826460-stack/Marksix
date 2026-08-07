from __future__ import annotations

import pytest

from cache.contracts import CacheUnavailable
from cache.memory import MemoryCacheStore
from cache.redis_store import RedisCacheStore
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


def test_memory_version_key_cannot_be_reused_with_different_value():
    cache = MemoryCacheStore()
    cache.publish_versioned("public:pointer", "public:v1", b"first", ttl_seconds=60)

    with pytest.raises(CacheUnavailable, match="immutable"):
        cache.publish_versioned("public:pointer", "public:v1", b"different", ttl_seconds=60)

    assert cache.get("public:v1") == b"first"
    assert cache.get("public:pointer") == b"public:v1"


class _FakePipeline:
    def __init__(self, client: "_FakeRedisClient") -> None:
        self._client = client
        self._commands: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def __enter__(self) -> "_FakePipeline":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def set(self, *args: object, **kwargs: object) -> "_FakePipeline":
        self._commands.append(("set", args, kwargs))
        return self

    def execute(self) -> list[bool]:
        if self._client.execute_error is not None:
            raise self._client.execute_error
        results: list[bool] = []
        for _name, args, kwargs in self._commands:
            key, value = str(args[0]), bytes(args[1])
            if kwargs.get("nx") and key in self._client.values:
                results.append(False)
                continue
            self._client.values[key] = value
            results.append(True)
        return results


class _FakeRedisClient:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.execute_error: OSError | None = None
        self.pipelines: list[_FakePipeline] = []

    def pipeline(self, *, transaction: bool) -> _FakePipeline:
        assert transaction is True
        pipeline = _FakePipeline(self)
        self.pipelines.append(pipeline)
        return pipeline

    def get(self, key: str) -> bytes | None:
        return self.values.get(key)


def _redis_store_with(client: _FakeRedisClient) -> RedisCacheStore:
    store = object.__new__(RedisCacheStore)
    store._client = client
    store._redis_errors = (OSError,)
    return store


def test_redis_version_key_collision_does_not_switch_pointer():
    client = _FakeRedisClient()
    client.values["public:v1"] = b"first"
    client.values["public:pointer"] = b"old-version"
    cache = _redis_store_with(client)

    with pytest.raises(CacheUnavailable, match="immutable"):
        cache.publish_versioned("public:pointer", "public:v1", b"different", ttl_seconds=60)

    assert client.values["public:v1"] == b"first"
    assert client.values["public:pointer"] == b"old-version"


def test_redis_fake_pipeline_publishes_same_immutable_version_idempotently():
    client = _FakeRedisClient()
    client.values["public:v1"] = b"payload"
    cache = _redis_store_with(client)

    cache.publish_versioned("public:pointer", "public:v1", b"payload", ttl_seconds=60)

    assert client.values["public:pointer"] == b"public:v1"
    assert len(client.pipelines) == 2


def test_redis_pipeline_errors_are_mapped_to_cache_unavailable():
    client = _FakeRedisClient()
    client.execute_error = OSError("redis unavailable")

    with pytest.raises(CacheUnavailable, match="redis unavailable"):
        _redis_store_with(client).publish_versioned(
            "public:pointer", "public:v1", b"payload", ttl_seconds=60
        )


def test_redis_store_creation_does_not_ping(monkeypatch):
    import redis

    calls: list[tuple[str, dict[str, object]]] = []

    class FakeRedis:
        @staticmethod
        def from_url(url: str, **kwargs: object) -> object:
            calls.append((url, kwargs))
            return object()

    monkeypatch.setattr(redis, "Redis", FakeRedis)

    RedisCacheStore("redis://cache.example:6379/0")

    assert len(calls) == 1


def test_cache_backend_errors_are_exposed_as_cache_unavailable():
    class BrokenCache(MemoryCacheStore):
        def _write(self, key: str, value: bytes, ttl_seconds: int) -> None:
            raise OSError("connection reset")

    with pytest.raises(CacheUnavailable, match="connection reset"):
        BrokenCache().set("snapshot", b"payload", ttl_seconds=1)
