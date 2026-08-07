"""Redis implementation of the cache contract.

Client construction is intentionally lazy: redis-py opens a connection only on an
operation, so importing or creating this adapter cannot make the process start-up
depend on Redis availability.
"""

from __future__ import annotations

from typing import Any

from cache.contracts import CacheUnavailable


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
            # SET NX establishes a version exactly once.  A failed claim is only
            # idempotent when the existing bytes are identical; otherwise the
            # pointer must remain untouched.
            with self._client.pipeline(transaction=True) as pipeline:
                pipeline.set(version_key, bytes(value), ex=ttl_seconds, nx=True)
                created = pipeline.execute()[0]
            if not created:
                existing = self.get(version_key)
                if existing != bytes(value):
                    raise CacheUnavailable(
                        "version key is immutable and already has a different value"
                    )

            # A Redis SET is atomic. It is deliberately a separate transaction:
            # a version-key collision can never update the public pointer.
            with self._client.pipeline(transaction=True) as pipeline:
                pipeline.set(pointer_key, version_key.encode("utf-8"), ex=ttl_seconds)
                pipeline.execute()
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
