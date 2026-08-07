"""Redis implementation of the cache contract.

Client construction is intentionally lazy: redis-py opens a connection only on an
operation, so importing or creating this adapter cannot make the process start-up
depend on Redis availability.
"""

from __future__ import annotations

from typing import Any

from cache.contracts import CacheUnavailable


_PUBLISH_VERSIONED_SCRIPT = """
local existing = redis.call('GET', KEYS[1])
if existing and existing ~= ARGV[1] then
    return 0
end
if not existing then
    redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
else
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
redis.call('SET', KEYS[2], ARGV[3], 'EX', ARGV[4])
return 1
"""


class RedisCacheStore:
    """Bounded Redis operations and immutable version publication."""

    def __init__(self, redis_url: str, *, socket_timeout: float = 0.2) -> None:
        if not redis_url.strip():
            raise ValueError("REDIS_URL must not be empty")
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - requirements deployment guard
            raise RuntimeError("Install the redis package to use CACHE_BACKEND=redis.") from exc
        self._redis_errors = (redis.RedisError, OSError)
        self._client: Any = redis.Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=socket_timeout,
            socket_timeout=socket_timeout,
            retry_on_timeout=False,
        )

    def _unavailable(self, exc: Exception) -> CacheUnavailable:
        return CacheUnavailable(str(exc))

    def get(self, key: str) -> bytes | None:
        try:
            value = self._client.get(key)
            return None if value is None else bytes(value)
        except self._redis_errors as exc:
            raise self._unavailable(exc) from exc

    def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        try:
            self._client.set(key, bytes(value), ex=ttl_seconds)
        except self._redis_errors as exc:
            raise self._unavailable(exc) from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except self._redis_errors as exc:
            raise self._unavailable(exc) from exc

    def publish_versioned(
        self,
        pointer_key: str,
        version_key: str,
        value: bytes,
        *,
        ttl_seconds: int,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        try:
            # One script makes version/pointer publication retriable. The version
            # gets a one-second TTL margin, so it always outlives the pointer.
            published = self._client.eval(
                _PUBLISH_VERSIONED_SCRIPT,
                2,
                version_key,
                pointer_key,
                bytes(value),
                ttl_seconds + 1,
                version_key.encode("utf-8"),
                ttl_seconds,
            )
            if not published:
                raise CacheUnavailable("version key is immutable and already has a different value")
        except self._redis_errors as exc:
            raise self._unavailable(exc) from exc

    def get_versioned(self, pointer_key: str) -> bytes | None:
        pointer = self.get(pointer_key)
        if pointer is None:
            return None
        try:
            version_key = pointer.decode("utf-8")
        except UnicodeDecodeError:
            return None
        return self.get(version_key)
